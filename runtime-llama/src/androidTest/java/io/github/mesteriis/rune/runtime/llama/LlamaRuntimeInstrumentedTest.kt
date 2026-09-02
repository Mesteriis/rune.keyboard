package io.github.mesteriis.rune.runtime.llama

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LlamaRuntimeInstrumentedTest {
    @Test(timeout = 15_000)
    fun scoringBeforeLoadAndAfterCancelOrUnloadReturnsTypedFailure() {
        LlamaLocalModelRuntime().use { runtime ->
            repeat(10) {
                assertScoringFailure(RuntimeErrorCode.NOT_LOADED, runtime.scoreCandidates(validRequest()))
                runtime.cancelCurrentOperation()
                // Each score is a new operation: a previous cancel must not poison it.
                assertScoringFailure(RuntimeErrorCode.NOT_LOADED, runtime.scoreCandidates(validRequest()))
                runtime.unload()
                assertScoringFailure(RuntimeErrorCode.NOT_LOADED, runtime.scoreCandidates(validRequest()))
            }
        }
    }

    @Test(timeout = 15_000)
    fun publicScoringRejectsInvalidInputWithoutAModel() {
        LlamaLocalModelRuntime().use { runtime ->
            val invalid = listOf(
                CandidateScoringRequest("\uD800", validRequest().candidates) to RuntimeErrorCode.INVALID_UTF8,
                CandidateScoringRequest("😀".repeat(1025), validRequest().candidates) to RuntimeErrorCode.CONTEXT_TOO_LONG,
                CandidateScoringRequest("context", listOf(ScoringCandidate(0, "\uDC00"))) to RuntimeErrorCode.INVALID_UTF8,
                CandidateScoringRequest("context", listOf(ScoringCandidate(0, "é".repeat(257)))) to RuntimeErrorCode.CONTEXT_TOO_LONG,
                CandidateScoringRequest("context", listOf(ScoringCandidate(1, "a"), ScoringCandidate(1, "b"))) to RuntimeErrorCode.INVALID_REQUEST,
                CandidateScoringRequest("context", (0..8).map { ScoringCandidate(it, "a") }) to RuntimeErrorCode.TOO_MANY_CANDIDATES,
            )
            invalid.forEach { (request, code) -> assertScoringFailure(code, runtime.scoreCandidates(request)) }
            assertScoringFailure(RuntimeErrorCode.NOT_LOADED, runtime.scoreCandidates(validRequest()))
        }
    }

    @Test(timeout = 15_000)
    fun nativeScoringIndependentlyValidatesByteArraysAndReturnsNoPartialWire() {
        // Public encode rejects malformed requests before JNI. Reflection is confined
        // to this test-owned handle so these assertions exercise the registered JNI
        // boundary itself, without changing production visibility or lifecycle state.
        LlamaLocalModelRuntime().use { runtime ->
            RawScoringHandle(runtime).use { native ->
                val ids = intArrayOf(7, 9)
                val continuations = arrayOf(" a".toByteArray(), " b".toByteArray())
                fun check(code: RuntimeErrorCode, prefix: ByteArray? = "context".toByteArray(),
                    candidateIds: IntArray? = ids, values: Array<out ByteArray?>? = continuations) {
                    assertArrayEquals(longArrayOf(1, code.stableCode.toLong(), 0, 0), native.score(prefix, candidateIds, values))
                }
                check(RuntimeErrorCode.NOT_LOADED, "NUL\u0000 supplementary 😀".toByteArray())
                check(RuntimeErrorCode.NOT_LOADED, ByteArray(4096) { 'a'.code.toByte() },
                    values = arrayOf(ByteArray(512) { 'b'.code.toByte() }, byteArrayOf(99)))
                for (invalid in listOf(byteArrayOf(0x80.toByte()), byteArrayOf(0xC0.toByte(), 0x80.toByte()),
                    byteArrayOf(0xED.toByte(), 0xA0.toByte(), 0x80.toByte()),
                    byteArrayOf(0xF4.toByte(), 0x90.toByte(), 0x80.toByte(), 0x80.toByte()),
                    byteArrayOf(0xE2.toByte(), 0x82.toByte()))) {
                    check(RuntimeErrorCode.INVALID_UTF8, prefix = invalid)
                    check(RuntimeErrorCode.INVALID_UTF8, values = arrayOf(invalid, byteArrayOf(98)))
                }
                check(RuntimeErrorCode.CONTEXT_TOO_LONG, prefix = ByteArray(4097))
                check(RuntimeErrorCode.CONTEXT_TOO_LONG, values = arrayOf(ByteArray(513), byteArrayOf(98)))
                check(RuntimeErrorCode.INVALID_REQUEST, candidateIds = intArrayOf(7, 7))
                check(RuntimeErrorCode.INVALID_REQUEST, candidateIds = intArrayOf(-1, 9))
                check(RuntimeErrorCode.INVALID_REQUEST, candidateIds = intArrayOf())
                check(RuntimeErrorCode.INVALID_REQUEST, values = arrayOf(byteArrayOf(97)))
                check(RuntimeErrorCode.INVALID_REQUEST, values = arrayOf(byteArrayOf(), byteArrayOf(98)))
                check(RuntimeErrorCode.INVALID_REQUEST, values = arrayOf(null, byteArrayOf(98)))
                check(RuntimeErrorCode.INVALID_REQUEST, prefix = null)
                check(RuntimeErrorCode.INVALID_REQUEST, candidateIds = null)
                check(RuntimeErrorCode.INVALID_REQUEST, values = null)
                check(RuntimeErrorCode.TOO_MANY_CANDIDATES, candidateIds = IntArray(9) { it },
                    values = Array(9) { byteArrayOf(97) })
                check(RuntimeErrorCode.NOT_LOADED)
            }
        }
    }

    @Test(timeout = 30_000)
    fun scoringRacesWithCancelUnloadAndCloseWithoutHanging() {
        repeat(20) {
            val runtime = LlamaLocalModelRuntime()
            val start = CountDownLatch(1)
            val finished = CountDownLatch(3)
            val failure = AtomicReference<Throwable?>()
            val actions = listOf<() -> Unit>(
                {
                    repeat(12) {
                        val result = runtime.scoreCandidates(validRequest())
                        assertTrue(result is CandidateScoringResult.Failure)
                        assertTrue((result as CandidateScoringResult.Failure).error in setOf(
                            RuntimeErrorCode.NOT_LOADED, RuntimeErrorCode.CANCELLED, RuntimeErrorCode.INTERNAL_ERROR,
                        ))
                    }
                },
                { repeat(12) { runtime.cancelCurrentOperation(); runtime.unload() } },
                { runtime.close() },
            )
            actions.forEach { action ->
                Thread {
                    try {
                        start.await()
                        action()
                    } catch (error: Throwable) {
                        failure.compareAndSet(null, error)
                    } finally {
                        finished.countDown()
                    }
                }.apply { isDaemon = true }.start()
            }
            start.countDown()
            assertTrue("scoring lifecycle race did not finish", finished.await(5, TimeUnit.SECONDS))
            failure.get()?.let { throw AssertionError("scoring lifecycle race failed", it) }
            runtime.close()
            assertScoringFailure(RuntimeErrorCode.INTERNAL_ERROR, runtime.scoreCandidates(validRequest()))
            LlamaLocalModelRuntime().use { next ->
                assertScoringFailure(RuntimeErrorCode.NOT_LOADED, next.scoreCandidates(validRequest()))
            }
        }
    }

    @Test
    fun nativeLibraryLoadsAndBadFileReturnsTypedFailure() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val badModel = File(context.cacheDir, "bad-${System.nanoTime()}.gguf").apply {
            writeBytes("not a gguf".toByteArray())
        }

        LlamaLocalModelRuntime().use { runtime ->
            val result = runtime.load(badModel)
            assertTrue(result is ModelLoadResult.Failure)
            assertEquals(RuntimeErrorCode.MODEL_LOAD_FAILED, (result as ModelLoadResult.Failure).code)
        }
    }

    @Test
    fun concurrentCancelAndCloseNeverUseADestroyedHandle() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val badModel = File(context.cacheDir, "bad-race-${System.nanoTime()}.gguf").apply {
            writeBytes("not a gguf".toByteArray())
        }

        repeat(20) {
            val runtime = LlamaLocalModelRuntime()
            val caller = Thread { runtime.load(badModel) }
            caller.start()
            runtime.cancelCurrentOperation()
            runtime.close()
            caller.join(5_000)
            assertFalse("native caller did not finish", caller.isAlive)
        }
    }

    private fun validRequest() = CandidateScoringRequest(
        "Synthetic context\u0000 😀", listOf(ScoringCandidate(7, " one"), ScoringCandidate(9, " two")),
    )

    private fun assertScoringFailure(code: RuntimeErrorCode, result: CandidateScoringResult) {
        assertEquals(CandidateScoringResult.Failure(code), result)
    }

    private class RawScoringHandle(private val runtime: LlamaLocalModelRuntime) : AutoCloseable {
        private val type = LlamaLocalModelRuntime::class.java
        private val create = type.getDeclaredMethod("nativeCreate").apply { isAccessible = true }
        private val destroy = type.getDeclaredMethod("nativeDestroy", Long::class.javaPrimitiveType).apply { isAccessible = true }
        private val score = type.getDeclaredMethod("nativeScoreCandidates", Long::class.javaPrimitiveType,
            ByteArray::class.java, IntArray::class.java, Array<ByteArray>::class.java).apply { isAccessible = true }
        private val handle = (create.invoke(runtime) as Long).also { assertTrue("native handle creation failed", it != 0L) }

        fun score(prefix: ByteArray?, ids: IntArray?, continuations: Array<out ByteArray?>?): LongArray =
            score.invoke(runtime, handle, prefix, ids, continuations) as LongArray

        override fun close() {
            destroy.invoke(runtime, handle)
        }
    }
}
