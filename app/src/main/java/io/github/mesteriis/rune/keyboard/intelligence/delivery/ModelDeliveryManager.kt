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
        space.requireCapacity(descriptor)
        store.write(DeliveryJournal(JournalOperation.QUEUED, downloadId = null, allowMetered = allowMetered))
        return try {
            downloads.enqueue(descriptor, allowMetered).also { id ->
                store.write(DeliveryJournal(JournalOperation.QUEUED, id, allowMetered))
            }
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

    fun cancel() {
        val current = store.read()
        current.downloadId?.let(downloads::remove) ?: downloads.removeMatching(descriptor)
        store.write(DeliveryJournal())
    }

    fun importDocument(uri: Uri) = SafModelTransfer(context, descriptor).import(uri)

    fun exportActive(activeModel: File, uri: Uri) = SafModelTransfer(context, descriptor).export(activeModel, uri)

    fun deleteAllModels() {
        cancel()
        val root = store.stateFile.parentFile!!
        listOf("active", "rollback", "candidates", ".installing").forEach { name ->
            val target = File(root, name)
            check(target.parentFile == root) { "refusing to remove an unscoped path" }
            target.deleteRecursively()
        }
        File(root, "active-model.json").delete()
    }
}
