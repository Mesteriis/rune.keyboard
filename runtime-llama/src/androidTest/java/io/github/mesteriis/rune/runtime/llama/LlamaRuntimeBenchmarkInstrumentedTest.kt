package io.github.mesteriis.rune.runtime.llama

import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Debug
import android.os.Process
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import java.util.zip.ZipFile
import org.junit.Test
import org.junit.runner.RunWith

/** Manual synthetic baseline through the public runtime. No editor/service work or generation. */
@RuntimeBenchmarkOnly
@RunWith(AndroidJUnit4::class)
class LlamaRuntimeBenchmarkInstrumentedTest {
    private var sequence = 0L
    private var profileCode = -1L
    private class BenchmarkFailure(val code: Int) : RuntimeException()
    private data class Timed<T>(val value: T, val wallNs: Long, val cpuMs: Long, val endedNs: Long)

    @Test(timeout = 1_860_000)
    fun fixedSyntheticCandidateScoringBaseline() {
        val finished = AtomicBoolean(false)
        var runtime: LlamaLocalModelRuntime? = null
        try {
            val profile = try {
                RuntimeBenchmarkWorkload.Profile.parse(InstrumentationRegistry.getArguments().getString("runeBenchmarkProfile"))
            } catch (_: IllegalArgumentException) { throw BenchmarkFailure(1) }
            profileCode = profile.code.toLong()
            // A stuck native call or uninterruptible close must not leave this test process running.
            Thread {
                Thread.sleep(profile.deadlineSeconds * 1000)
                if (!finished.get()) terminateProcess()
            }.apply { isDaemon = true; name = "rune-benchmark-deadline"; start() }
            val buildCode = buildCode()
            requireBench(InstrumentationRegistry.getArguments().getString("runeBenchmarkBuild") == buildCode.toString(), 26)
            val model = verifiedModel()
            val started = SystemClock.elapsedRealtimeNanos()
            val cpuStarted = Process.getElapsedCpuTime()
            emit(0, aux0 = Build.VERSION.SDK_INT.toLong(), aux1 = buildCode)
            nativeHashes()

            val constructed = timed(30) { LlamaLocalModelRuntime() }
            runtime = constructed.value
            emitTimed(3, constructed, config = 0)
            val activeRuntime = runtime
            val loadFlag = AtomicBoolean(false)
            val loaded = timed(120, { loadFlag.set(true); activeRuntime.cancelCurrentOperation() }) {
                activeRuntime.load(model, loadFlag::get)
            }
            val load = loaded.value as? ModelLoadResult.Success ?: throw BenchmarkFailure(2)
            requireBench(load.loadMillis >= 0, 3)
            emitTimed(3, loaded, config = 1, nativeMs = load.loadMillis)

            for (visit in RuntimeBenchmarkWorkload.visits(1)) score(activeRuntime, 1, visit)
            for (visit in RuntimeBenchmarkWorkload.visits(profile.repeats)) score(activeRuntime, 2, visit)

            repeat(RuntimeBenchmarkWorkload.CANCEL_ATTEMPTS) { attempt -> cancellation(activeRuntime, attempt) }
            score(activeRuntime, 5, RuntimeBenchmarkWorkload.Visit(0, -1))
            emitTimed(3, timed(30) { activeRuntime.unload() }, config = 2)
            emitTimed(3, timed(30) { activeRuntime.close() }, config = 3)
            runtime = null
            emit(6, wallNs = SystemClock.elapsedRealtimeNanos() - started,
                cpuMs = Process.getElapsedCpuTime() - cpuStarted)
        } catch (failure: Throwable) {
            val code = (failure as? BenchmarkFailure)?.code ?: 99
            emit(7, outcome = code.toLong())
            // Never attach a throwable whose payload could contain model paths or request data.
            throw AssertionError("runtime_benchmark_error_$code")
        } finally {
            try {
                runtime?.let { active -> timed(30) { active.close() } }
            } finally { finished.set(true) }
        }
    }

    private fun score(runtime: LlamaLocalModelRuntime, kind: Long, visit: RuntimeBenchmarkWorkload.Visit) {
        val request = RuntimeBenchmarkWorkload.request(visit.config)
        val cancelled = AtomicBoolean(false)
        val result = timed(45, { cancelled.set(true); runtime.cancelCurrentOperation() }) {
            runtime.scoreCandidates(request, cancelled::get)
        }
        val success = RuntimeBenchmarkWorkload.validatedScore(request, result.value)
        emitTimed(kind, result, visit.config.toLong(), visit.iteration.toLong(),
            tokens = success.scores.sumOf { it.scoredTokenCount.toLong() },
            scores = success.scores.size.toLong(), nativeMs = success.durationMillis)
    }

    private fun cancellation(runtime: LlamaLocalModelRuntime, attempt: Int) {
        val request = RuntimeBenchmarkWorkload.cancellationRequest()
        val cancelled = AtomicBoolean(false)
        val admitted = CountDownLatch(1)
        var signalledNs = 0L
        var admittedNs = 0L
        val result = timed(30, { cancelled.set(true); runtime.cancelCurrentOperation() }, afterStart = {
            requireBench(admitted.await(5, TimeUnit.SECONDS), 10)
            admittedNs = SystemClock.elapsedRealtimeNanos()
            Thread.sleep(10)
            signalledNs = SystemClock.elapsedRealtimeNanos()
            cancelled.set(true) // Independent request token FIRST, then shared native cancellation.
            runtime.cancelCurrentOperation()
        }) {
            runtime.scoreCandidates(request, isCancelled = { admitted.countDown(); cancelled.get() })
        }
        val success = when (val value = result.value) {
            is CandidateScoringResult.Success -> RuntimeBenchmarkWorkload.validatedScore(request, value)
            is CandidateScoringResult.Failure -> { requireBench(value.error == RuntimeErrorCode.CANCELLED, 11); null }
        }
        emitTimed(4, result, config = attempt.toLong(), outcome = if (success == null) 1 else 2,
            tokens = success?.scores?.sumOf { it.scoredTokenCount.toLong() } ?: 0,
            scores = success?.scores?.size?.toLong() ?: 0, nativeMs = success?.durationMillis ?: -1,
            aux0 = if (result.endedNs >= signalledNs) result.endedNs - signalledNs else -1,
            aux1 = signalledNs - admittedNs)
    }

    private fun verifiedModel(): File {
        val directory = InstrumentationRegistry.getInstrumentation().context.filesDir.canonicalFile
        val model = File(directory, "qualification-model.gguf")
        requireBench(model.canonicalFile.parentFile == directory && model.isFile, 20)
        requireBench(model.length() == RuntimeBenchmarkWorkload.MODEL_BYTES, 21)
        val digest = MessageDigest.getInstance("SHA-256")
        model.inputStream().use { stream ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val count = stream.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        val actual = digest.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
        requireBench(actual == RuntimeBenchmarkWorkload.MODEL_SHA256, 22)
        return model
    }

    private fun nativeHashes() {
        requireBench(Process.is64Bit() && Build.SUPPORTED_ABIS.firstOrNull() == "arm64-v8a", 24)
        val context = InstrumentationRegistry.getInstrumentation().context
        ZipFile(context.applicationInfo.sourceDir).use { apk ->
            listOf("librune_llama.so", "libc++_shared.so").forEachIndexed { index, name ->
                val entry = apk.getEntry("lib/arm64-v8a/$name") ?: throw BenchmarkFailure(25)
                val digest = MessageDigest.getInstance("SHA-256")
                apk.getInputStream(entry).use { stream ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val count = stream.read(buffer)
                        if (count < 0) break
                        digest.update(buffer, 0, count)
                    }
                }
                val chunks = digest.digest().toList().chunked(4).map { bytes ->
                    bytes.fold(0L) { sum, byte -> (sum shl 8) or (byte.toLong() and 255) }
                }
                requireBench(InstrumentationRegistry.getArguments().getString("runeBenchmarkNative$index") == chunks.joinToString(":"), 27)
                val fields = longArrayOf(1, 8, profileCode, sequence++, index.toLong(), -1, 0, 0,
                    *chunks.toLongArray(), 0, 0)
                InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
                    putString("rune_bench", RuntimeBenchmarkWorkload.row(*fields))
                })
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun buildCode(): Long {
        val context = InstrumentationRegistry.getInstrumentation().context
        val metadata = context.packageManager.getApplicationInfo(context.packageName, PackageManager.GET_META_DATA).metaData
        return when (metadata?.getString("rune.runtime.benchmark.buildType")) {
            "debug" -> 0L
            "release" -> 1L
            else -> throw BenchmarkFailure(23)
        }
    }

    private fun <T> timed(seconds: Long, cancel: () -> Unit = {}, afterStart: () -> Unit = {}, block: () -> T): Timed<T> {
        val done = CountDownLatch(1)
        val value = AtomicReference<Timed<T>?>()
        val failed = AtomicBoolean(false)
        Thread {
            try {
                val wall = SystemClock.elapsedRealtimeNanos()
                val cpu = Process.getElapsedCpuTime()
                val result = block()
                val ended = SystemClock.elapsedRealtimeNanos()
                value.set(Timed(result, ended - wall, Process.getElapsedCpuTime() - cpu, ended))
            } catch (_: Throwable) { failed.set(true) }
            finally { done.countDown() }
        }.apply { isDaemon = true; name = "rune-benchmark-call"; start() }
        try {
            afterStart()
            if (!done.await(seconds, TimeUnit.SECONDS)) throw BenchmarkFailure(30)
        } catch (failure: Throwable) {
            cancel()
            if (!done.await(5, TimeUnit.SECONDS)) terminateProcess()
            throw failure
        }
        requireBench(!failed.get(), 31)
        return value.get() ?: throw BenchmarkFailure(32)
    }

    private fun terminateProcess(): Nothing {
        // Only the dedicated instrumentation process; never an app/user process selected by ID.
        Process.killProcess(Process.myPid())
        throw BenchmarkFailure(33)
    }

    private fun requireBench(condition: Boolean, code: Int) { if (!condition) throw BenchmarkFailure(code) }

    private fun memory(): LongArray {
        val pss = try { Debug.MemoryInfo().also { Debug.getMemoryInfo(it) }.totalPss.toLong() * 1024 } catch (_: Exception) { -1L }
        val rss = try {
            File("/proc/self/status").useLines { lines ->
                lines.firstOrNull { it.startsWith("VmRSS:") }?.trim()?.split(Regex("\\s+"))?.getOrNull(1)?.toLong()?.times(1024) ?: -1L
            }
        } catch (_: Exception) { -1L }
        val native = try { Debug.getNativeHeapAllocatedSize() } catch (_: Exception) { -1L }
        val java = java.lang.Runtime.getRuntime().let { it.totalMemory() - it.freeMemory() }
        return longArrayOf(pss, rss, native, java)
    }

    private fun <T> emitTimed(kind: Long, timed: Timed<T>, config: Long = -1, iteration: Long = -1,
        outcome: Long = 0, tokens: Long = 0, scores: Long = 0, nativeMs: Long = -1, aux0: Long = 0, aux1: Long = 0) =
        emit(kind, config, iteration, outcome, timed.wallNs, timed.cpuMs, tokens, scores, nativeMs, aux0, aux1)

    private fun emit(kind: Long, config: Long = -1, iteration: Long = -1, outcome: Long = 0,
        wallNs: Long = 0, cpuMs: Long = 0, tokens: Long = 0, scores: Long = 0, nativeMs: Long = -1, aux0: Long = 0, aux1: Long = 0) {
        val mem = memory()
        val row = RuntimeBenchmarkWorkload.row(1, kind, profileCode, sequence++, config, iteration, outcome,
            wallNs, cpuMs, tokens, scores, nativeMs, mem[0], mem[1], mem[2], mem[3], aux0, aux1)
        InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply { putString("rune_bench", row) })
    }
}
