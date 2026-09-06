package io.github.mesteriis.rune.runtime.llama

import android.os.Bundle
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@VerifiedModelOnly
@RunWith(AndroidJUnit4::class)
class LlamaRealModelInstrumentedTest {
    @Test(timeout = 120_000)
    fun verifiedModelScoresAndRecoversThroughThePublicAndroidRuntime() {
        val started = SystemClock.elapsedRealtime()
        // Verify before even constructing the runtime. This test never downloads or searches for a model.
        val model = verifiedModel()
        val metrics = Bundle()
        var successfulRequests = 0
        var scoredCandidates = 0
        val requests = listOf(
            request("Please check the", " address", " adress", " address"),
            request("Нужно исправить", " сообщение", " сообшение", " сообщения"),
            request("Quiero enviar un", " mensaje", " mensage", " mensajes"),
        )
        LlamaLocalModelRuntime().use { runtime ->
            val cancelledLoad = AtomicBoolean(true)
            runtime.cancelCurrentOperation()
            assertEquals(ModelLoadResult.Failure(RuntimeErrorCode.CANCELLED),
                runtime.load(model, isCancelled = cancelledLoad::get))
            assertLoaded(runtime.load(model, isCancelled = { false }))
            for (request in requests) {
                val first = assertSuccess(request, runtime.scoreCandidates(request, isCancelled = { false }))
                val repeated = assertSuccess(request, runtime.scoreCandidates(request, isCancelled = { false }))
                first.scores.zip(repeated.scores).forEach { (before, after) ->
                    assertEquals(before.scoredTokenCount, after.scoredTokenCount)
                    assertEquals(before.sumLogProbability, after.sumLogProbability, 0.000001)
                }
                successfulRequests += 2
                scoredCandidates += first.scores.size + repeated.scores.size
            }
            assertFailure(RuntimeErrorCode.SCORING_FAILED,
                runtime.scoreCandidates(request("Same", " word", " word")))
            assertInvalidInputs(runtime, requests.first())

            val cancelledScore = AtomicBoolean(true)
            runtime.cancelCurrentOperation()
            assertFailure(RuntimeErrorCode.CANCELLED,
                runtime.scoreCandidates(requests.first(), isCancelled = cancelledScore::get))
            assertSuccess(requests.first(), runtime.scoreCandidates(requests.first()))
            successfulRequests++
            scoredCandidates += requests.first().candidates.size

            // The public admission predicate signals after native cancellation has been reset.
            // It does not reveal tokenizer/decode stage, so this race makes no stage claim.
            val cancellationResult = cancelAdmittedScoring(runtime)
            metrics.putInt("cancellationRaceCancelled", if (cancellationResult is CandidateScoringResult.Failure) 1 else 0)
            metrics.putInt("cancellationRaceSucceeded", if (cancellationResult is CandidateScoringResult.Success) 1 else 0)
            if (cancellationResult is CandidateScoringResult.Success) {
                successfulRequests++
                scoredCandidates += cancellationResult.scores.size
            }
            assertSuccess(requests.first(), runtime.scoreCandidates(requests.first()))
            successfulRequests++
            scoredCandidates += requests.first().candidates.size

            runtime.unload()
            assertFailure(RuntimeErrorCode.NOT_LOADED, runtime.scoreCandidates(requests.first()))
            assertLoaded(runtime.load(model, isCancelled = { false }))
            assertSuccess(requests.first(), runtime.scoreCandidates(requests.first()))
            successfulRequests++
            scoredCandidates += requests.first().candidates.size
        }
        metrics.putLong("qualificationDurationMillis", SystemClock.elapsedRealtime() - started)
        metrics.putInt("successfulRequests", successfulRequests)
        metrics.putInt("scoredCandidates", scoredCandidates)
        metrics.putInt("preCancelledRequests", 2)
        // Only numeric test metrics; no request text, model path, or generated content is emitted.
        InstrumentationRegistry.getInstrumentation().sendStatus(0, metrics)
    }

    private fun verifiedModel(): File {
        val directory = InstrumentationRegistry.getInstrumentation().context.filesDir.canonicalFile
        val model = File(directory, "qualification-model.gguf")
        assertTrue("qualification model must remain inside the test app", directory == model.canonicalFile.parentFile)
        assertTrue("exact qualification model is missing", model.isFile)
        assertEquals("qualification model size mismatch", 396704416L, model.length())
        val digest = MessageDigest.getInstance("SHA-256")
        model.inputStream().buffered().use { input ->
            val bytes = ByteArray(64 * 1024)
            while (true) {
                val count = input.read(bytes)
                if (count < 0) break
                digest.update(bytes, 0, count)
            }
        }
        val actual = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
        assertEquals("qualification model SHA-256 mismatch",
            "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4", actual)
        return model
    }

    private fun assertInvalidInputs(runtime: LocalModelRuntime, valid: CandidateScoringRequest) {
        val invalid = listOf(
            CandidateScoringRequest("\uD800", valid.candidates) to RuntimeErrorCode.INVALID_UTF8,
            CandidateScoringRequest("😀".repeat(1025), valid.candidates) to RuntimeErrorCode.CONTEXT_TOO_LONG,
            request("context", "\uDC00", " a") to RuntimeErrorCode.INVALID_UTF8,
            request("context", "é".repeat(257), " a") to RuntimeErrorCode.CONTEXT_TOO_LONG,
            CandidateScoringRequest("context", listOf(ScoringCandidate(1, " a"), ScoringCandidate(1, " b"))) to
                RuntimeErrorCode.INVALID_REQUEST,
            CandidateScoringRequest("context", (0..8).map { ScoringCandidate(it, " a") }) to
                RuntimeErrorCode.TOO_MANY_CANDIDATES,
            // Each repeated " x" is one token for this pinned model; these stay within byte caps.
            request("context" + " x".repeat(193), " a", " b") to RuntimeErrorCode.CONTEXT_TOO_LONG,
            request("context", " x".repeat(65), " b") to RuntimeErrorCode.CONTEXT_TOO_LONG,
        )
        invalid.forEach { (request, expected) -> assertFailure(expected, runtime.scoreCandidates(request)) }
    }

    private fun cancelAdmittedScoring(runtime: LocalModelRuntime): CandidateScoringResult {
        // 129 prefix tokens and at most 33 continuation tokens on the pinned model,
        // comfortably within the production 192/64/256 token and eight-candidate caps.
        val request = CandidateScoringRequest("context" + " x".repeat(128),
            (0 until 8).map { index -> ScoringCandidate(100 + index, " ${'a' + index}" + " x".repeat(32)) })
        val cancelled = AtomicBoolean(false)
        val admitted = CountDownLatch(1)
        val result = AtomicReference<CandidateScoringResult?>()
        val error = AtomicReference<Throwable?>()
        val worker = Thread {
            try {
                result.set(runtime.scoreCandidates(request, isCancelled = {
                    admitted.countDown()
                    cancelled.get()
                }))
            } catch (failure: Throwable) {
                error.set(failure)
            }
        }.apply { isDaemon = true }
        worker.start()
        try {
            assertTrue("scoring was not admitted", admitted.await(5, TimeUnit.SECONDS))
            Thread.sleep(10)
            cancelled.set(true)
            runtime.cancelCurrentOperation()
            worker.join(20_000)
            assertFalse("cancelled scoring did not finish", worker.isAlive)
            error.get()?.let { throw AssertionError("scoring worker failed", it) }
            return when (val actual = result.get()) {
                is CandidateScoringResult.Success -> assertSuccess(request, actual)
                is CandidateScoringResult.Failure -> actual.also { assertFailure(RuntimeErrorCode.CANCELLED, it) }
                null -> throw AssertionError("scoring worker returned no result")
            }
        } finally {
            cancelled.set(true)
            runtime.cancelCurrentOperation()
            worker.join(20_000)
        }
    }

    private fun assertLoaded(result: ModelLoadResult) {
        assertTrue("exact model load failed: $result", result is ModelLoadResult.Success)
        assertTrue((result as ModelLoadResult.Success).loadMillis >= 0)
    }

    private fun assertSuccess(request: CandidateScoringRequest, result: CandidateScoringResult): CandidateScoringResult.Success {
        assertTrue("scoring failed: $result", result is CandidateScoringResult.Success)
        val success = result as CandidateScoringResult.Success
        assertEquals(request.candidates.map { it.id }, success.scores.map { it.id })
        assertTrue(success.durationMillis >= 0)
        success.scores.forEach { score ->
            assertTrue(score.sumLogProbability.isFinite())
            assertTrue(score.sumLogProbability <= 0.0)
            assertTrue(score.scoredTokenCount in 1..255)
        }
        return success
    }

    private fun assertFailure(expected: RuntimeErrorCode, result: CandidateScoringResult) {
        assertEquals(CandidateScoringResult.Failure(expected), result)
    }

    private fun request(prefix: String, vararg continuations: String) = CandidateScoringRequest(
        prefix, continuations.mapIndexed { index, text -> ScoringCandidate(20 - index * 3, text) },
    )
}
