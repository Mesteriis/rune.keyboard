package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import android.net.Uri
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.runtime.AtomicModelPointerStore
import java.io.File
import java.io.IOException

class ModelDeliveryManager(
    private val context: Context,
    private val descriptor: ModelDescriptor = EmbeddedModelDescriptor.load(context),
) {
    private val store = DeliveryStateStore.forApplication(context)
    private val downloads = ModelDownloadClient(context)
    private val space = ModelStorageSpace(
        ModelDownloadClient.externalStaging(context),
        store.stateFile.parentFile!!,
    )
    private val root = store.stateFile.parentFile!!
    private val operationGate = ModelOperationGate(root)
    private val targetDirectory = "${descriptor.id}-${descriptor.version}"

    fun enqueueDownload(allowMetered: Boolean = false): Long = operationGate.withLock {
        enqueueDownloadLocked(allowMetered)
    }

    private fun enqueueDownloadLocked(allowMetered: Boolean): Long {
        requireNoDeleteRecovery()
        requireTargetNotActive()
        store.write(DeliveryJournal(JournalOperation.QUEUED, downloadId = null, allowMetered = allowMetered))
        return try {
            space.requireCapacity(descriptor)
            downloads.enqueue(descriptor, allowMetered).also { id ->
                store.write(DeliveryJournal(JournalOperation.QUEUED, id, allowMetered))
                ModelDeliveryJobScheduler.schedule(context)
            }
        } catch (error: CandidateInstallException) {
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = error.failureCode))
            throw error
        } catch (error: Exception) {
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.DOWNLOAD_FAILED))
            throw error
        }
    }

    fun downloadOverMeteredNetwork(): Long = operationGate.withLock {
        requireNoDeleteRecovery()
        val journal = store.read()
        val id = requireNotNull(journal.downloadId) { "downloadId is missing" }
        require(downloads.query(id) == DownloadObservation.PAUSED) { "download is not paused" }
        val action = DeliveryReconciler.requestMeteredOverride(
            journal.copy(operation = JournalOperation.WAITING_UNMETERED),
        )
        downloads.remove(action.removeDownloadId)
        enqueueDownloadLocked(allowMetered = action.requeueAllowedOverMetered)
    }

    fun reconcileOnSettingsOpen() {
        ModelDeliveryJobScheduler.schedule(context)
    }

    fun retry(): Long? = operationGate.withLock {
        requireNoDeleteRecovery()
        val candidate = File(
            root,
            "candidates/$targetDirectory/${descriptor.fileName}",
        )
        if (candidate.isFile) {
            store.write(
                DeliveryJournal(
                    operation = JournalOperation.SELF_TESTING,
                    activationPhase = ActivationPhase.CANDIDATE_SELF_TEST,
                    activationDirectory = targetDirectory,
                ),
            )
            ModelDeliveryJobScheduler.schedule(context)
            return@withLock null
        }
        enqueueDownloadLocked(allowMetered = false)
    }

    fun cancel() {
        ModelDeliveryJobScheduler.cancel(context)
        operationGate.withLock(::cancelLocked)
    }

    private fun cancelLocked() {
        requireNoDeleteRecovery()
        val current = store.read()
        current.downloadId?.let(downloads::remove) ?: downloads.removeMatching(descriptor)
        store.write(DeliveryJournal())
    }

    fun importDocument(uri: Uri) = operationGate.withLock {
        requireNoDeleteRecovery()
        requireTargetNotActive()
        SafModelTransfer(context, descriptor).import(uri)
    }

    fun exportActive(activeModel: File, uri: Uri) = operationGate.withLock {
        requireNoDeleteRecovery()
        SafModelTransfer(context, descriptor).export(activeModel, uri)
    }

    fun deleteAllModels() {
        ModelDeliveryJobScheduler.cancel(context)
        operationGate.withLock {
            val current = store.read()
            store.write(
                DeliveryJournal(
                    operation = JournalOperation.FAILED,
                    failureCode = ModelFailureCode.DELETE_FAILED,
                ),
            )
            current.downloadId?.let(downloads::remove) ?: downloads.removeMatching(descriptor)
            ModelFilesCleaner(
                root = root,
                markComplete = { store.write(DeliveryJournal()) },
            ).deleteAll()
        }
    }

    private fun requireNoDeleteRecovery() {
        check(store.read().failureCode != ModelFailureCode.DELETE_FAILED) {
            "model deletion must be completed before another operation"
        }
    }

    private fun requireTargetNotActive() {
        check(AtomicModelPointerStore(root).read().activeDirectory != targetDirectory) {
            "model version is already active"
        }
    }
}

internal class ModelFilesCleaner(
    private val root: File,
    private val markDeleting: () -> Unit = {},
    private val markComplete: () -> Unit = {},
    private val clearPointer: () -> Unit = { AtomicModelPointerStore(root).delete() },
    private val deleteRecursively: (File) -> Boolean = File::deleteRecursively,
) {
    fun deleteAll() {
        // The durable tombstone prevents a restarted reconciler from reviving a leftover candidate.
        markDeleting()
        deleteDirectory("candidates")
        deleteDirectory(".installing")
        // Clear the pointer before removing versions it could reference. Any leftover version is
        // unreferenced and the durable tombstone keeps the delete action available for retry.
        clearPointer()
        deleteDirectory("versions")
        markComplete()
    }

    private fun deleteDirectory(name: String) {
        val target = File(root, name)
        check(target.parentFile == root) { "refusing to remove an unscoped path" }
        if (target.exists() && (!deleteRecursively(target) || target.exists())) {
            throw IOException("cannot delete model directory: $name")
        }
    }
}
