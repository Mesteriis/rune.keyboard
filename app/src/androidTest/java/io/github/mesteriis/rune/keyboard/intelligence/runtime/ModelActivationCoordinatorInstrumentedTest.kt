package io.github.mesteriis.rune.keyboard.intelligence.runtime

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ActivationPhase
import io.github.mesteriis.rune.keyboard.intelligence.delivery.CandidateInstaller
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryJournal
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryStateStore
import io.github.mesteriis.rune.keyboard.intelligence.delivery.JournalOperation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelFailureCode
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelManifestParser
import io.github.mesteriis.rune.runtime.llama.LocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.ModelLoadResult
import io.github.mesteriis.rune.runtime.llama.ModelSelfTestResult
import io.github.mesteriis.rune.runtime.llama.RuntimeErrorCode
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ModelActivationCoordinatorInstrumentedTest {
    @Test
    fun resumesSelfTestingJournalFromMovedVersion() {
        val fixture = fixture("moved")
        fixture.installVersion("old-active")
        fixture.installVersion("old-rollback")
        fixture.installVersion(fixture.versionName)
        fixture.pointerStore.write(ActiveModelPointer("old-active", "old-rollback"))
        fixture.store.write(DeliveryJournal(JournalOperation.SELF_TESTING))

        val result = fixture.coordinator(FakeRuntime()).resumeOrActivate(fixture.store.read())

        assertTrue(result)
        assertEquals(ActiveModelPointer(fixture.versionName, "old-active"), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "versions/old-rollback").exists())
        assertEquals(JournalOperation.IDLE, fixture.store.read().operation)
    }

    @Test
    fun failedPostCommitReloadPromotesPreviousActive() {
        val fixture = fixture("rollback")
        fixture.installVersion("old-active")
        fixture.installCandidate()
        fixture.pointerStore.write(ActiveModelPointer("old-active", null))
        fixture.store.write(DeliveryJournal(JournalOperation.INSTALLING))
        val runtime = FakeRuntime { file ->
            if (file.path.contains("versions/${fixture.versionName}")) {
                ModelLoadResult.Failure(RuntimeErrorCode.MODEL_LOAD_FAILED)
            } else {
                ModelLoadResult.Success(1)
            }
        }

        val result = fixture.coordinator(runtime).resumeOrActivate(fixture.store.read())

        assertFalse(result)
        assertEquals(ActiveModelPointer("old-active", null), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "versions/${fixture.versionName}").exists())
        assertEquals(JournalOperation.FAILED, fixture.store.read().operation)
        assertEquals(ModelFailureCode.RUNTIME_LOAD_FAILED, fixture.store.read().failureCode)
    }

    @Test
    fun committedSelfTestingJournalDoesNotRotateRollbackAgain() {
        val fixture = fixture("committed")
        fixture.installVersion(fixture.versionName)
        fixture.installVersion("old-active")
        fixture.pointerStore.write(ActiveModelPointer(fixture.versionName, "old-active"))
        fixture.store.write(DeliveryJournal(JournalOperation.SELF_TESTING))

        val result = fixture.coordinator(FakeRuntime()).resumeOrActivate(fixture.store.read())

        assertTrue(result)
        assertEquals(ActiveModelPointer(fixture.versionName, "old-active"), fixture.pointerStore.read())
        assertTrue(File(fixture.root, "versions/old-active/model.gguf").isFile)
        assertEquals(JournalOperation.IDLE, fixture.store.read().operation)
    }

    @Test
    fun idleActiveModelDoesNotRequestRuntimeWork() {
        val fixture = fixture("idle")
        fixture.installVersion(fixture.versionName)
        fixture.pointerStore.write(ActiveModelPointer(fixture.versionName, null))
        val runtime = FakeRuntime()
        val coordinator = fixture.coordinator(runtime)

        val idle = DeliveryJournal(JournalOperation.IDLE)
        assertFalse(coordinator.canResumeOrActivate(idle))
        assertFalse(coordinator.resumeOrActivate(idle))
        assertTrue(runtime.loadedFiles.isEmpty())
    }

    @Test
    fun rollbackPhaseAfterPointerCommitCannotReactivateFailedVersion() {
        val fixture = fixture("rollback-recovery")
        fixture.installVersion("old-active")
        fixture.installVersion(fixture.versionName)
        fixture.pointerStore.write(ActiveModelPointer("old-active", null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                failureCode = ModelFailureCode.RUNTIME_SELF_TEST_FAILED,
                activationPhase = ActivationPhase.ROLLBACK_COMMIT,
                activationDirectory = fixture.versionName,
            ),
        )
        val runtime = FakeRuntime()

        val result = fixture.coordinator(runtime).resumeOrActivate(fixture.store.read())

        assertFalse(result)
        assertEquals(ActiveModelPointer("old-active", null), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "versions/${fixture.versionName}").exists())
        assertTrue(runtime.loadedFiles.isEmpty())
        assertEquals(JournalOperation.FAILED, fixture.store.read().operation)
    }

    @Test
    fun recoveryUsesPersistedActivationDirectoryAfterDescriptorChanges() {
        val fixture = fixture("descriptor-change")
        fixture.installVersion("old-active")
        fixture.installVersion(fixture.versionName)
        fixture.pointerStore.write(ActiveModelPointer("old-active", null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                activationPhase = ActivationPhase.POINTER_COMMIT,
                activationDirectory = fixture.versionName,
            ),
        )
        val nextDescriptor = descriptor.copy(version = "0.2.0")
        val runtime = FakeRuntime()

        val result = fixture.coordinator(runtime, nextDescriptor).resumeOrActivate(fixture.store.read())

        assertTrue(result)
        assertEquals(ActiveModelPointer(fixture.versionName, "old-active"), fixture.pointerStore.read())
        assertTrue(runtime.loadedFiles.single().path.contains("versions/${fixture.versionName}"))
    }

    @Test
    fun legacyPhaseWithoutActivationDirectoryFailsClosed() {
        val fixture = fixture("phase-without-identity")
        fixture.installCandidate()
        fixture.installVersion("old-active")
        fixture.pointerStore.write(ActiveModelPointer("old-active", null))
        val journal = DeliveryJournal(
            operation = JournalOperation.SELF_TESTING,
            activationPhase = ActivationPhase.POINTER_COMMIT,
        )
        fixture.store.write(journal)
        val runtime = FakeRuntime()
        val coordinator = fixture.coordinator(runtime)

        assertFalse(coordinator.canResumeOrActivate(journal))
        assertFalse(coordinator.resumeOrActivate(journal))
        assertEquals(ActiveModelPointer("old-active", null), fixture.pointerStore.read())
        assertTrue(File(fixture.root, "candidates/${fixture.versionName}").isDirectory)
        assertTrue(runtime.loadedFiles.isEmpty())
    }

    @Test
    fun rollbackCommitFailureKeepsDurablePhaseForRetry() {
        val fixture = fixture("rollback-commit-failure")
        fixture.installVersion("old-active")
        fixture.installCandidate()
        fixture.pointerStore.write(ActiveModelPointer("old-active", null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.INSTALLING,
                activationDirectory = fixture.versionName,
            ),
        )
        val realTransaction = ModelActivationTransaction(fixture.root, fixture.pointerStore)
        val throwingTransaction = object : ModelActivationActions {
            override fun activate(candidateDirectory: String) = realTransaction.activate(candidateDirectory)

            override fun resumeRollback(failedDirectory: String) {
                throw java.io.IOException("injected rollback pointer failure")
            }

            override fun clearPointerAndVersions() = realTransaction.clearPointerAndVersions()
        }
        val runtime = FakeRuntime { file ->
            if (file.path.contains("versions/${fixture.versionName}")) {
                ModelLoadResult.Failure(RuntimeErrorCode.MODEL_LOAD_FAILED)
            } else {
                ModelLoadResult.Success(1)
            }
        }

        val result = fixture.coordinator(runtime, transaction = throwingTransaction)
            .resumeOrActivate(fixture.store.read())

        assertFalse(result)
        assertEquals(
            ActiveModelPointer(fixture.versionName, "old-active"),
            fixture.pointerStore.read(),
        )
        assertEquals(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                failureCode = ModelFailureCode.RUNTIME_LOAD_FAILED,
                activationPhase = ActivationPhase.ROLLBACK_COMMIT,
                activationDirectory = fixture.versionName,
            ),
            fixture.store.read(),
        )
    }

    @Test
    fun failedActiveAndRollbackClearPointerInsteadOfExposingBadModel() {
        val fixture = fixture("both-invalid")
        fixture.installVersion("old-active")
        fixture.installCandidate()
        fixture.pointerStore.write(ActiveModelPointer("old-active", null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.INSTALLING,
                activationDirectory = fixture.versionName,
            ),
        )
        val runtime = FakeRuntime { file ->
            if (file.path.contains("candidates/")) {
                ModelLoadResult.Success(1)
            } else {
                ModelLoadResult.Failure(RuntimeErrorCode.MODEL_LOAD_FAILED)
            }
        }

        val result = fixture.coordinator(runtime).resumeOrActivate(fixture.store.read())

        assertFalse(result)
        assertEquals(ActiveModelPointer(null, null), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "versions").listFiles().orEmpty().any(File::isDirectory))
        assertEquals(JournalOperation.FAILED, fixture.store.read().operation)
        assertEquals(ModelFailureCode.ROLLBACK_FAILED, fixture.store.read().failureCode)
    }

    @Test
    fun clearPointerPhaseFinishesCleanupAfterPointerCommitCrash() {
        val fixture = fixture("clear-pointer-recovery")
        fixture.installVersion("old-active")
        fixture.installVersion(fixture.versionName)
        fixture.pointerStore.write(ActiveModelPointer(null, null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                failureCode = ModelFailureCode.ROLLBACK_FAILED,
                activationPhase = ActivationPhase.CLEAR_POINTER_COMMIT,
                activationDirectory = fixture.versionName,
            ),
        )
        val runtime = FakeRuntime()

        val result = fixture.coordinator(runtime).resumeOrActivate(fixture.store.read())

        assertFalse(result)
        assertEquals(ActiveModelPointer(null, null), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "versions").listFiles().orEmpty().any(File::isDirectory))
        assertTrue(runtime.loadedFiles.isEmpty())
        assertEquals(JournalOperation.FAILED, fixture.store.read().operation)
        assertEquals(ModelFailureCode.ROLLBACK_FAILED, fixture.store.read().failureCode)
    }

    @Test
    fun sameVersionImportReturnsToReadyWithoutRotatingOrStalling() {
        val fixture = fixture("same-version-import")
        fixture.installVersion(fixture.versionName)
        fixture.installCandidate()
        fixture.pointerStore.write(ActiveModelPointer(fixture.versionName, null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                activationPhase = ActivationPhase.CANDIDATE_SELF_TEST,
                activationDirectory = fixture.versionName,
            ),
        )
        val runtime = FakeRuntime()

        val result = fixture.coordinator(runtime).resumeOrActivate(fixture.store.read())

        assertTrue(result)
        assertEquals(ActiveModelPointer(fixture.versionName, null), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "candidates/${fixture.versionName}").exists())
        assertTrue(File(fixture.root, "versions/${fixture.versionName}/model.gguf").isFile)
        assertEquals(JournalOperation.IDLE, fixture.store.read().operation)
    }

    @Test
    fun legacySameVersionCandidateCannotMaskCorruptRetainedActive() {
        val fixture = fixture("same-version-corrupt-active")
        fixture.installVersion(fixture.versionName)
        fixture.installCandidate()
        fixture.pointerStore.write(ActiveModelPointer(fixture.versionName, null))
        fixture.store.write(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                activationPhase = ActivationPhase.CANDIDATE_SELF_TEST,
                activationDirectory = fixture.versionName,
            ),
        )
        val runtime = FakeRuntime { file ->
            if (file.path.contains("candidates/")) {
                ModelLoadResult.Success(1)
            } else {
                ModelLoadResult.Failure(RuntimeErrorCode.MODEL_LOAD_FAILED)
            }
        }

        val result = fixture.coordinator(runtime).resumeOrActivate(fixture.store.read())

        assertFalse(result)
        assertEquals(ActiveModelPointer(null, null), fixture.pointerStore.read())
        assertFalse(File(fixture.root, "candidates/${fixture.versionName}").exists())
        assertFalse(File(fixture.root, "versions/${fixture.versionName}").exists())
        assertEquals(JournalOperation.FAILED, fixture.store.read().operation)
        assertEquals(ModelFailureCode.RUNTIME_LOAD_FAILED, fixture.store.read().failureCode)
    }

    @Test
    fun concurrentPointerStoreInstancesSerializeWithinOneProcess() {
        val fixture = fixture("pointer-lock")
        val first = AtomicModelPointerStore(fixture.root)
        val second = AtomicModelPointerStore(fixture.root)
        val start = CountDownLatch(1)
        val failure = AtomicReference<Throwable>()
        val workers = listOf(
            Thread {
                start.await(5, TimeUnit.SECONDS)
                runCatching {
                    repeat(100) { first.write(ActiveModelPointer("version-$it", null)) }
                }.exceptionOrNull()?.let(failure::set)
            },
            Thread {
                start.await(5, TimeUnit.SECONDS)
                runCatching { repeat(100) { second.read() } }.exceptionOrNull()?.let(failure::set)
            },
        )

        workers.forEach(Thread::start)
        start.countDown()
        workers.forEach(Thread::join)

        assertEquals(null, failure.get())
    }

    @Test
    fun pointerStoreRecoversCommittedBackupWhenBaseFileIsMissing() {
        val fixture = fixture("pointer-backup")
        val expected = ActiveModelPointer("active-version", "rollback-version")
        File(fixture.root, "active-model.json.bak").apply {
            parentFile?.mkdirs()
            writeText(ActiveModelPointerCodec.encode(expected))
        }

        assertEquals(expected, AtomicModelPointerStore(fixture.root).read())
        assertTrue(File(fixture.root, "active-model.json").isFile)
    }

    @Test
    fun deletingPointerLeavesNoAtomicFileThatCanRestoreAnActiveModel() {
        val fixture = fixture("pointer-delete")
        fixture.pointerStore.write(ActiveModelPointer("active", "rollback"))

        fixture.pointerStore.delete()

        assertEquals(ActiveModelPointer(null, null), fixture.pointerStore.read())
        listOf("active-model.json", "active-model.json.new", "active-model.json.bak").forEach { name ->
            assertFalse(File(fixture.root, name).exists())
        }
    }

    private fun fixture(name: String): Fixture {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val root = File(context.cacheDir, "activation-$name-${System.nanoTime()}")
        return Fixture(root, DeliveryStateStore(root), descriptor)
    }

    private data class Fixture(
        val root: File,
        val store: DeliveryStateStore,
        val descriptor: ModelDescriptor,
    ) {
        val versionName = "${descriptor.id}-${descriptor.version}"
        val pointerStore = AtomicModelPointerStore(root)

        fun installCandidate() = install("candidates", versionName)
        fun installVersion(directory: String) = install("versions", directory)

        fun coordinator(
            runtime: LocalModelRuntime,
            availableDescriptor: ModelDescriptor = descriptor,
            transaction: ModelActivationActions = ModelActivationTransaction(root, pointerStore),
        ) = ModelActivationCoordinator(
            store = store,
            descriptor = availableDescriptor,
            runtime = runtime,
            diagnostics = DisabledDiagnostics,
            pointerStore = pointerStore,
            transaction = transaction,
        )

        private fun install(parent: String, directory: String) {
            val target = File(root, "$parent/$directory")
            File(target, descriptor.fileName).apply { parentFile?.mkdirs(); writeText("model") }
            File(target, CandidateInstaller.MODEL_MANIFEST_NAME)
                .writeText(ModelManifestParser.encode(descriptor))
        }
    }

    private class FakeRuntime(
        private val loadResult: (File) -> ModelLoadResult = { ModelLoadResult.Success(1) },
    ) : LocalModelRuntime {
        val loadedFiles = mutableListOf<File>()

        override fun load(modelFile: File): ModelLoadResult {
            loadedFiles += modelFile
            return loadResult(modelFile)
        }

        override fun selfTest() = ModelSelfTestResult.Success(promptMillis = 1, firstTokenMillis = 2)
        override fun cancelCurrentOperation() = Unit
        override fun unload() = Unit
    }

    private object DisabledDiagnostics : RuntimeDiagnosticsSink {
        override val enabled = false
        override fun record(snapshot: RuntimeDiagnosticsSnapshot) = Unit
        override fun latest(): RuntimeDiagnosticsSnapshot? = null
    }

    private companion object {
        val descriptor = ModelDescriptor(
            id = "rune-text-test",
            version = "0.1.0",
            displayName = "Rune Test",
            fileName = "model.gguf",
            downloadUrl = "https://github.com/Mesteriis/rune.keyboard/releases/download/test/model.gguf",
            sha256 = "00".repeat(32),
            sizeBytes = 5,
            runtimeApi = 1,
            minimumRuneVersionCode = 2,
            ggufVersion = 3,
            architecture = "qwen3",
            fileType = 15,
        )
    }
}
