package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import android.net.Uri
import android.util.AtomicFile
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
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

    fun enqueueDownload(allowMetered: Boolean = false): Long = operationGate.withLock {
        enqueueDownloadLocked(allowMetered)
    }

    private fun enqueueDownloadLocked(allowMetered: Boolean): Long {
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
        val candidate = File(
            root,
            "candidates/${descriptor.id}-${descriptor.version}/${descriptor.fileName}",
        )
        if (candidate.isFile) {
            store.write(DeliveryJournal())
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
        val current = store.read()
        current.downloadId?.let(downloads::remove) ?: downloads.removeMatching(descriptor)
        store.write(DeliveryJournal())
    }

    fun importDocument(uri: Uri) = operationGate.withLock {
        SafModelTransfer(context, descriptor).import(uri)
    }

    fun exportActive(activeModel: File, uri: Uri) = operationGate.withLock {
        SafModelTransfer(context, descriptor).export(activeModel, uri)
    }

    fun deleteAllModels() {
        ModelDeliveryJobScheduler.cancel(context)
        operationGate.withLock {
            val current = store.read()
            current.downloadId?.let(downloads::remove) ?: downloads.removeMatching(descriptor)
            listOf("versions", "candidates", ".installing").forEach { name ->
                val target = File(root, name)
                check(target.parentFile == root) { "refusing to remove an unscoped path" }
                if (target.exists() && !target.deleteRecursively()) {
                    throw IOException("cannot delete model directory")
                }
            }
            AtomicFile(File(root, "active-model.json")).delete()
            store.write(DeliveryJournal())
        }
    }
}
