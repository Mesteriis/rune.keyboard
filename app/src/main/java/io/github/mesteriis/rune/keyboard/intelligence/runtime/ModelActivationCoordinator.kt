package io.github.mesteriis.rune.keyboard.intelligence.runtime

import android.content.Context
import android.os.Build
import android.os.Debug
import android.system.Os
import android.system.OsConstants
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ActivationPhase
import io.github.mesteriis.rune.keyboard.intelligence.delivery.CandidateInstaller
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryJournal
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

class ModelActivationCoordinator internal constructor(
    private val store: DeliveryStateStore,
    private val descriptor: ModelDescriptor,
    private val runtime: LocalModelRuntime,
    private val diagnostics: RuntimeDiagnosticsSink,
    private val pointerStore: ModelPointerStore = AtomicModelPointerStore(store.stateFile.parentFile!!),
    private val transaction: ModelActivationActions = ModelActivationTransaction(
        store.stateFile.parentFile!!,
        pointerStore,
    ),
) : AutoCloseable {
    private val root = store.stateFile.parentFile!!
    private val availableDirectory = "${descriptor.id}-${descriptor.version}"
    private val safeDirectory = Regex("[a-z0-9][a-z0-9._-]{0,126}")

    constructor(
        context: Context,
        descriptor: ModelDescriptor,
        runtime: LocalModelRuntime = LlamaLocalModelRuntime(),
        diagnostics: RuntimeDiagnosticsSink = RuntimeDiagnosticsProvider.instance,
    ) : this(DeliveryStateStore.forApplication(context), descriptor, runtime, diagnostics)

    fun canResumeOrActivate(journal: DeliveryJournal): Boolean {
        val directory = activationDirectory(journal) ?: return false
        if (journal.operation == JournalOperation.SELF_TESTING && journal.activationPhase != null) {
            return true
        }
        val candidate = File(root, "candidates/$directory")
        val version = File(root, "versions/$directory")
        return candidate.isDirectory ||
            journal.operation == JournalOperation.SELF_TESTING && version.isDirectory
    }

    fun resumeOrActivate(journal: DeliveryJournal): Boolean {
        if (!canResumeOrActivate(journal)) return false
        val directory = requireNotNull(activationDirectory(journal))
        return try {
            when (journal.activationPhase) {
                ActivationPhase.CLEAR_POINTER_COMMIT -> resumeClearPointer(journal)
                ActivationPhase.ROLLBACK_COMMIT -> resumeRollback(journal)
                ActivationPhase.ACTIVE_VALIDATION -> finishActiveValidation(directory)
                ActivationPhase.POINTER_COMMIT -> commitPointerAndValidate(directory)
                ActivationPhase.CANDIDATE_SELF_TEST -> selfTestCandidate(directory)
                null -> when {
                    modelFile("candidates", directory) != null -> selfTestCandidate(directory)
                    journal.operation == JournalOperation.SELF_TESTING &&
                        modelFile("versions", directory) != null -> {
                        store.write(selfTesting(ActivationPhase.POINTER_COMMIT, directory))
                        commitPointerAndValidate(directory)
                    }
                    else -> fail(ModelFailureCode.RUNTIME_LOAD_FAILED)
                }
            }
        } catch (_: Exception) {
            val durable = runCatching { store.read() }.getOrNull()
            if (durable?.isResumableCommit(directory) == true) {
                runtime.unload()
                false
            } else {
                fail(ModelFailureCode.RUNTIME_SELF_TEST_FAILED)
            }
        }
    }

    private fun selfTestCandidate(directory: String): Boolean {
        val candidate = modelFile("candidates", directory)
            ?: return fail(ModelFailureCode.RUNTIME_LOAD_FAILED)
        store.write(selfTesting(ActivationPhase.CANDIDATE_SELF_TEST, directory))
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
        recordDiagnostics(
            directory,
            loadMillis,
            selfTest,
            (System.nanoTime() - unloadStart) / 1_000_000,
        )
        store.write(selfTesting(ActivationPhase.POINTER_COMMIT, directory))
        return commitPointerAndValidate(directory)
    }

    private fun commitPointerAndValidate(directory: String): Boolean {
        transaction.activate(directory)
        store.write(selfTesting(ActivationPhase.ACTIVE_VALIDATION, directory))
        return finishActiveValidation(directory)
    }

    private fun finishActiveValidation(directory: String): Boolean {
        val pointer = pointerStore.read()
        check(pointer.activeDirectory == directory) { "activation pointer was not committed" }
        return validateActiveOrRollback(directory)
    }

    private fun validateActiveOrRollback(directory: String): Boolean {
        val pointer = pointerStore.read()
        check(pointer.activeDirectory == directory) { "activation pointer changed during validation" }
        val active = requireNotNull(pointer.activeDirectory)
        val activeModel = installedModelFile(active)
        val activeFailure = if (activeModel == null) {
            ModelFailureCode.RUNTIME_LOAD_FAILED
        } else {
            runtimeFailureFor(activeModel)
        }
        if (activeFailure == null) {
            store.write(DeliveryJournal())
            return true
        }
        if (activeFailure == ModelFailureCode.RUNTIME_CANCELLED) return pauseValidation()
        val rollback = pointer.rollbackDirectory ?: return quarantine(directory, activeFailure)
        val rollbackModel = installedModelFile(rollback)
        val rollbackFailure = if (rollbackModel == null) {
            ModelFailureCode.RUNTIME_LOAD_FAILED
        } else {
            runtimeFailureFor(rollbackModel)
        }
        if (rollbackFailure == ModelFailureCode.RUNTIME_CANCELLED) return pauseValidation()
        if (rollbackFailure != null) {
            return quarantine(directory, ModelFailureCode.ROLLBACK_FAILED)
        }
        store.write(
            selfTesting(
                phase = ActivationPhase.ROLLBACK_COMMIT,
                directory = directory,
                failureCode = activeFailure,
            ),
        )
        transaction.resumeRollback(directory)
        store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = activeFailure))
        return false
    }

    private fun resumeRollback(journal: DeliveryJournal): Boolean {
        val failure = journal.failureCode ?: ModelFailureCode.RUNTIME_SELF_TEST_FAILED
        transaction.resumeRollback(requireNotNull(journal.activationDirectory))
        store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = failure))
        return false
    }

    private fun quarantine(directory: String, failure: ModelFailureCode): Boolean {
        store.write(
            selfTesting(
                phase = ActivationPhase.CLEAR_POINTER_COMMIT,
                directory = directory,
                failureCode = failure,
            ),
        )
        transaction.clearPointerAndVersions()
        store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = failure))
        return false
    }

    private fun resumeClearPointer(journal: DeliveryJournal): Boolean {
        val failure = journal.failureCode ?: ModelFailureCode.ROLLBACK_FAILED
        transaction.clearPointerAndVersions()
        store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = failure))
        return false
    }

    fun cancelCurrentOperation() {
        runtime.cancelCurrentOperation()
    }

    override fun close() {
        runtime.close()
    }

    private fun installedModelFile(directory: String): File? = runCatching {
        modelFile("versions", directory)
    }.getOrNull()

    private fun modelFile(parent: String, directory: String): File? {
        if (!safeDirectory.matches(directory)) return null
        val modelDirectory = File(root, "$parent/$directory")
        val manifest = File(modelDirectory, CandidateInstaller.MODEL_MANIFEST_NAME)
        val installed = runCatching { ModelManifestParser.parse(manifest.readText()) }.getOrNull() ?: return null
        return File(modelDirectory, installed.fileName).takeIf(File::isFile)
    }

    private fun runtimeFailureFor(model: File): ModelFailureCode? {
        if (!model.isFile) return ModelFailureCode.RUNTIME_LOAD_FAILED
        return try {
            when (val load = runtime.load(model)) {
                is ModelLoadResult.Failure -> runtimeFailure(load.code, loadPhase = true)
                is ModelLoadResult.Success -> when (val test = runtime.selfTest()) {
                    is ModelSelfTestResult.Failure -> runtimeFailure(test.code, loadPhase = false)
                    is ModelSelfTestResult.Success -> null
                }
            }
        } catch (_: Exception) {
            ModelFailureCode.RUNTIME_SELF_TEST_FAILED
        } finally {
            runtime.unload()
        }
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

    private fun pauseValidation(): Boolean {
        runtime.unload()
        val directory = requireNotNull(store.read().activationDirectory)
        store.write(selfTesting(ActivationPhase.ACTIVE_VALIDATION, directory))
        return false
    }

    private fun selfTesting(
        phase: ActivationPhase,
        directory: String,
        failureCode: ModelFailureCode? = null,
    ) = DeliveryJournal(
        operation = JournalOperation.SELF_TESTING,
        failureCode = failureCode,
        activationPhase = phase,
        activationDirectory = directory,
    )

    private fun recordDiagnostics(
        directory: String,
        loadMillis: Long,
        test: ModelSelfTestResult.Success,
        unloadMillis: Long,
    ) {
        if (!diagnostics.enabled) return
        runCatching {
            val memory = Debug.MemoryInfo().also(Debug::getMemoryInfo)
            diagnostics.record(
                RuntimeDiagnosticsSnapshot(
                    runtimeCommit = RUNTIME_COMMIT,
                    abi = Build.SUPPORTED_ABIS.firstOrNull().orEmpty(),
                    backend = "cpu-portable",
                    model = directory,
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
    }

    private fun processRssKb(): Long = runCatching {
        val residentPages = File("/proc/self/statm").readText().trim().split(Regex("\\s+"))[1].toLong()
        residentPages * Os.sysconf(OsConstants._SC_PAGESIZE) / 1024
    }.getOrDefault(0L)

    private fun activationDirectory(journal: DeliveryJournal): String? {
        journal.activationDirectory?.let { directory ->
            return directory.takeIf(safeDirectory::matches)
        }
        if (journal.activationPhase != null) return null
        val candidate = File(root, "candidates/$availableDirectory")
        val version = File(root, "versions/$availableDirectory")
        return availableDirectory.takeIf {
            candidate.isDirectory || journal.operation == JournalOperation.SELF_TESTING && version.isDirectory
        }
    }

    private fun DeliveryJournal.isResumableCommit(directory: String): Boolean =
        operation == JournalOperation.SELF_TESTING &&
            activationDirectory == directory &&
            activationPhase in setOf(
                ActivationPhase.POINTER_COMMIT,
                ActivationPhase.ACTIVE_VALIDATION,
                ActivationPhase.ROLLBACK_COMMIT,
                ActivationPhase.CLEAR_POINTER_COMMIT,
            )

    private companion object {
        const val RUNTIME_COMMIT = "36b10154383b60eb15baac2c7a40d2a5f784faa7"
    }
}
