package io.github.mesteriis.rune.keyboard.intelligence.runtime

import android.content.Context
import android.os.Build
import android.os.Debug
import android.system.Os
import android.system.OsConstants
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryJournal
import io.github.mesteriis.rune.keyboard.intelligence.delivery.CandidateInstaller
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryStateStore
import io.github.mesteriis.rune.keyboard.intelligence.delivery.JournalOperation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelFailureCode
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelManifestParser
import io.github.mesteriis.rune.runtime.llama.LlamaLocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.LocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.ModelLoadResult
import io.github.mesteriis.rune.runtime.llama.ModelSelfTestResult
import io.github.mesteriis.rune.runtime.llama.RuntimeErrorCode
import java.io.File

class ModelActivationCoordinator(
    context: Context,
    private val descriptor: ModelDescriptor,
    private val runtime: LocalModelRuntime = LlamaLocalModelRuntime(),
    private val diagnostics: RuntimeDiagnosticsSink = RuntimeDiagnosticsProvider.instance,
) : AutoCloseable {
    private val store = DeliveryStateStore.forApplication(context)
    private val root = store.stateFile.parentFile!!
    private val pointerStore = AtomicModelPointerStore(root)
    private val transaction = ModelActivationTransaction(root, pointerStore)
    private val versionName = "${descriptor.id}-${descriptor.version}"

    fun activateCandidate(): Boolean {
        val candidate = File(root, "candidates/$versionName/${descriptor.fileName}")
        if (!candidate.isFile) return false
        store.write(DeliveryJournal(operation = JournalOperation.SELF_TESTING))
        return try {
            val loadMillis = when (val load = runtime.load(candidate)) {
                is ModelLoadResult.Failure -> return fail(runtimeFailure(load.code, loadPhase = true))
                is ModelLoadResult.Success -> load.loadMillis
            }
            val selfTest = when (val test = runtime.selfTest()) {
                is ModelSelfTestResult.Failure -> return fail(runtimeFailure(test.code, loadPhase = false))
                is ModelSelfTestResult.Success -> test
            }
            val unloadStart = System.nanoTime()
            runtime.unload()
            recordDiagnostics(loadMillis, selfTest, (System.nanoTime() - unloadStart) / 1_000_000)
            transaction.activate(versionName)
            store.write(DeliveryJournal())
            true
        } catch (_: Exception) {
            fail(ModelFailureCode.RUNTIME_SELF_TEST_FAILED)
        }
    }

    fun validateActiveOrRollback(): Boolean {
        val pointer = pointerStore.read()
        val active = pointer.activeDirectory ?: return false
        if (installedModelFile(active)?.let(::selfTest) == true) return true
        val rollback = pointer.rollbackDirectory ?: return fail(ModelFailureCode.ROLLBACK_FAILED)
        if (installedModelFile(rollback)?.let(::selfTest) != true) {
            return fail(ModelFailureCode.ROLLBACK_FAILED)
        }
        transaction.rollback()
        store.write(DeliveryJournal())
        return true
    }

    fun cancelCurrentOperation() {
        runtime.cancelCurrentOperation()
    }

    override fun close() {
        runtime.close()
    }

    private fun installedModelFile(directory: String): File? = runCatching {
        val versionDirectory = File(root, "versions/$directory")
        val manifest = File(versionDirectory, CandidateInstaller.MODEL_MANIFEST_NAME)
        val installed = ModelManifestParser.parse(manifest.readText())
        File(versionDirectory, installed.fileName)
    }.getOrNull()

    private fun selfTest(model: File): Boolean {
        if (!model.isFile) return false
        val loaded = runtime.load(model) is ModelLoadResult.Success
        val passed = loaded && runtime.selfTest() is ModelSelfTestResult.Success
        runtime.unload()
        return passed
    }

    private fun runtimeFailure(code: RuntimeErrorCode, loadPhase: Boolean): ModelFailureCode = when (code) {
        RuntimeErrorCode.CANCELLED -> ModelFailureCode.RUNTIME_CANCELLED
        else -> if (loadPhase) ModelFailureCode.RUNTIME_LOAD_FAILED else ModelFailureCode.RUNTIME_SELF_TEST_FAILED
    }

    private fun fail(code: ModelFailureCode): Boolean {
        runtime.unload()
        store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = code))
        return false
    }

    private fun recordDiagnostics(loadMillis: Long, test: ModelSelfTestResult.Success, unloadMillis: Long) {
        if (!diagnostics.enabled) return
        val memory = Debug.MemoryInfo().also(Debug::getMemoryInfo)
        diagnostics.record(
            RuntimeDiagnosticsSnapshot(
                runtimeCommit = RUNTIME_COMMIT,
                abi = Build.SUPPORTED_ABIS.firstOrNull().orEmpty(),
                backend = "cpu-portable",
                model = "${descriptor.id}-${descriptor.version}",
                quantization = "Q4_K_M",
                loadMillis = loadMillis,
                promptMillis = test.promptMillis,
                firstTokenMillis = test.firstTokenMillis,
                unloadMillis = unloadMillis,
                rssKb = processRssKb(),
                totalPssKb = memory.totalPss,
                totalPrivateDirtyKb = memory.totalPrivateDirty,
            ),
        )
    }

    private fun processRssKb(): Long = runCatching {
        val residentPages = File("/proc/self/statm").readText().trim().split(Regex("\\s+"))[1].toLong()
        residentPages * Os.sysconf(OsConstants._SC_PAGESIZE) / 1024
    }.getOrDefault(0L)

    private companion object {
        const val RUNTIME_COMMIT = "36b10154383b60eb15baac2c7a40d2a5f784faa7"
    }
}
