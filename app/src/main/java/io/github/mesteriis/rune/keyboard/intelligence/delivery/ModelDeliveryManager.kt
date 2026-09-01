package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import android.net.Uri
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import java.io.File

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

    fun enqueueDownload(allowMetered: Boolean = false): Long {
        return try {
            space.requireCapacity(descriptor)
            store.write(DeliveryJournal(JournalOperation.QUEUED, downloadId = null, allowMetered = allowMetered))
            downloads.enqueue(descriptor, allowMetered).also { id ->
                store.write(DeliveryJournal(JournalOperation.QUEUED, id, allowMetered))
            }
        } catch (error: CandidateInstallException) {
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = error.failureCode))
            throw error
        } catch (error: Exception) {
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.DOWNLOAD_FAILED))
            throw error
        }
    }

    fun downloadOverMeteredNetwork(): Long {
        val action = DeliveryReconciler.requestMeteredOverride(store.read())
        downloads.remove(action.removeDownloadId)
        return enqueueDownload(allowMetered = action.requeueAllowedOverMetered)
    }

    fun reconcileOnSettingsOpen() {
        ModelDeliveryJobScheduler.schedule(context)
    }

    fun retry(): Long? {
        val candidate = File(
            store.stateFile.parentFile,
            "candidates/${descriptor.id}-${descriptor.version}/${descriptor.fileName}",
        )
        if (candidate.isFile) {
            store.write(DeliveryJournal())
            ModelDeliveryJobScheduler.schedule(context)
            return null
        }
        return enqueueDownload()
    }

    fun cancel() {
        ModelDeliveryJobScheduler.cancel(context)
        val current = store.read()
        current.downloadId?.let(downloads::remove) ?: downloads.removeMatching(descriptor)
        store.write(DeliveryJournal())
    }

    fun importDocument(uri: Uri) = SafModelTransfer(context, descriptor).import(uri)

    fun exportActive(activeModel: File, uri: Uri) = SafModelTransfer(context, descriptor).export(activeModel, uri)

    fun deleteAllModels() {
        cancel()
        val root = store.stateFile.parentFile!!
        listOf("versions", "candidates", ".installing").forEach { name ->
            val target = File(root, name)
            check(target.parentFile == root) { "refusing to remove an unscoped path" }
            target.deleteRecursively()
        }
        File(root, "active-model.json").delete()
    }
}
