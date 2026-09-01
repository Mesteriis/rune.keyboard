package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import android.os.ParcelFileDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import java.io.File

class ModelInstallCoordinator(
    context: Context,
    private val descriptor: ModelDescriptor = EmbeddedModelDescriptor.load(context),
) {
    private val appContext = context.applicationContext
    private val store = DeliveryStateStore.forApplication(appContext)
    private val root: File = store.stateFile.parentFile!!
    private val downloads = ModelDownloadClient(appContext)
    private val space = ModelStorageSpace(ModelDownloadClient.externalStaging(appContext), root)

    fun run() {
        val journal = store.read()
        val candidate = File(root, "candidates/${descriptor.id}-${descriptor.version}/${descriptor.fileName}")
        if (candidate.isFile) {
            journal.downloadId?.let(downloads::remove)
            store.write(DeliveryJournal())
            return
        }
        if (journal.operation == JournalOperation.IDLE) return
        val id = journal.downloadId ?: downloads.findMatching(descriptor)?.also { recoveredId ->
            store.write(journal.copy(downloadId = recoveredId))
        } ?: run {
            fail(journal, ModelFailureCode.DOWNLOAD_MISSING)
            return
        }
        when (downloads.query(id)) {
            DownloadObservation.PENDING, DownloadObservation.RUNNING ->
                store.write(journal.copy(operation = JournalOperation.DOWNLOADING))
            DownloadObservation.PAUSED ->
                store.write(journal.copy(operation = JournalOperation.WAITING_UNMETERED))
            DownloadObservation.SUCCESSFUL -> install(id, journal)
            DownloadObservation.FAILED -> fail(journal, ModelFailureCode.DOWNLOAD_FAILED)
            DownloadObservation.MISSING -> fail(journal, ModelFailureCode.DOWNLOAD_MISSING)
        }
    }

    private fun install(id: Long, journal: DeliveryJournal) {
        try {
            space.requireCapacity(descriptor)
            store.write(journal.copy(operation = JournalOperation.VERIFYING, failureCode = null))
            downloads.open(id).use { descriptorFile ->
                ParcelFileDescriptor.AutoCloseInputStream(descriptorFile).use { input ->
                    CandidateInstaller(root).install(input, descriptor) {
                        store.write(journal.copy(operation = JournalOperation.INSTALLING, failureCode = null))
                    }
                }
            }
            downloads.remove(id)
            store.write(DeliveryJournal())
        } catch (error: CandidateInstallException) {
            fail(journal, error.failureCode)
        } catch (_: Exception) {
            fail(journal, ModelFailureCode.IO_ERROR)
        }
    }

    private fun fail(journal: DeliveryJournal, code: ModelFailureCode) {
        store.write(journal.copy(operation = JournalOperation.FAILED, failureCode = code))
    }
}
