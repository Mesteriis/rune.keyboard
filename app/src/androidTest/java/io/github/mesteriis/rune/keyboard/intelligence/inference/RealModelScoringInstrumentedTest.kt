package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.pm.ApplicationInfo
import android.os.Process
import android.os.SystemClock
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelResolver
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import io.github.mesteriis.rune.runtime.llama.CandidateScoringRequest
import io.github.mesteriis.rune.runtime.llama.CandidateScoringResult
import io.github.mesteriis.rune.runtime.llama.LlamaLocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.ModelLoadResult
import io.github.mesteriis.rune.runtime.llama.ScoringCandidate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/** Exact-device gate. It skips ordinary CI, whose app data intentionally contains no full model. */
@RunWith(AndroidJUnit4::class)
class RealModelScoringInstrumentedTest {
    @Test
    fun installedRuneTextLoadsAndScoresBoundedCandidates() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val explicitPath = InstrumentationRegistry.getArguments().getString("runeScoringModel")
        val model = if (explicitPath != null) {
            File(explicitPath).also {
                assertTrue(
                    "Explicit Rune Text model is unavailable or has the wrong identity",
                    it.isFile && it.length() == MODEL_BYTES && it.sha256() == MODEL_SHA256,
                )
            }
        } else {
            val root = File(context.noBackupFilesDir, "model-delivery")
            val active = runCatching {
                ModelOperationGate(root).withReadLock { ActiveModelResolver(root).resolve() }
            }.getOrNull()
            assumeTrue("Exact Rune Text model is not installed", active?.descriptor?.sha256 == MODEL_SHA256)
            active!!.file
        }

        val runtime = LlamaLocalModelRuntime()
        try {
            val wallStart = SystemClock.elapsedRealtime()
            val loadCpuStart = Process.getElapsedCpuTime()
            val load = runtime.load(model)
            val loadCpuMillis = Process.getElapsedCpuTime() - loadCpuStart
            val loadWallMillis = SystemClock.elapsedRealtime() - wallStart
            assertTrue("Model load failed: $load", load is ModelLoadResult.Success)

            val request = CandidateScoringRequest(
                prefix = "Пекарь готовит ",
                candidates = listOf(
                    ScoringCandidate(0, "ттесто"),
                    ScoringCandidate(1, "тесто"),
                    ScoringCandidate(2, "место"),
                    ScoringCandidate(3, "тесть"),
                ),
            )
            val scoreWallStart = SystemClock.elapsedRealtime()
            val scoreCpuStart = Process.getElapsedCpuTime()
            val result = runtime.scoreCandidates(request)
            val scoreCpuMillis = Process.getElapsedCpuTime() - scoreCpuStart
            val scoreWallMillis = SystemClock.elapsedRealtime() - scoreWallStart
            assertTrue("Candidate scoring failed: $result", result is CandidateScoringResult.Success)
            result as CandidateScoringResult.Success
            assertEquals(listOf(0, 1, 2, 3), result.scores.map { it.id })
            val warmWallStart = SystemClock.elapsedRealtime()
            val warmCpuStart = Process.getElapsedCpuTime()
            val warm = runtime.scoreCandidates(request)
            val warmCpuMillis = Process.getElapsedCpuTime() - warmCpuStart
            val warmWallMillis = SystemClock.elapsedRealtime() - warmWallStart
            assertTrue("Warm candidate scoring failed: $warm", warm is CandidateScoringResult.Success)
            warm as CandidateScoringResult.Success
            assertEquals(result.scores, warm.scores)
            val debuggable = if (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0) 1 else 0
            println(
                "RUNE_REAL_MODEL_METRICS appDebuggable=$debuggable " +
                    "loadNativeMillis=${(load as ModelLoadResult.Success).loadMillis} " +
                    "loadWallMillis=$loadWallMillis loadCpuMillis=$loadCpuMillis " +
                    "scoreMillis=${result.durationMillis} scoreWallMillis=$scoreWallMillis " +
                    "scoreCpuMillis=$scoreCpuMillis warmScoreMillis=${warm.durationMillis} " +
                    "warmScoreWallMillis=$warmWallMillis warmScoreCpuMillis=$warmCpuMillis",
            )
        } finally {
            runtime.close()
        }
    }

    private companion object {
        const val MODEL_SHA256 = "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4"
        const val MODEL_BYTES = 396704416L
    }

    private fun File.sha256(): String {
        val digest = MessageDigest.getInstance("SHA-256")
        inputStream().buffered().use { input ->
            val buffer = ByteArray(1024 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
