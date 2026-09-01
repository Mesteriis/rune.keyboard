package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import android.os.ParcelFileDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import java.io.File

class ModelInstallCoordinator(
    context: Context,
    private val descriptor: ModelDescriptor = EmbeddedModelDescriptor.load(context),
) : AutoCloseable {
    private val appContext = context.applicationContext
    private val store = DeliveryStateStore.forApplication(appContext)
    private val root: File = store.stateFile.parentFile!!
    private val downloads = ModelDownloadClient(appContext)
    private val space = ModelStorageSpace(ModelDownloadClient.externalStaging(appContext), root)
    private val activationDirectory = "${descriptor.id}-${descriptor.version}"
    private val activation = io.github.mesteriis.rune.keyboard.intelligence.runtime.ModelActivationCoordinator(
        appContext,
        descriptor,
    )

    fun run(): Boolean {
        val journal = store.read()
        if (journal.operation != JournalOperation.FAILED && activation.canResumeOrActivate(journal)) {
            journal.downloadId?.let { downloadId -> runCatching { downloads.remove(downloadId) } }
            activation.resumeOrActivate(journal)
            return store.read().needsActivationRetry()
        }
        if (journal.operation == JournalOperation.FAILED) return false
        if (journal.operation == JournalOperation.IDLE) return false
        val id = journal.downloadId ?: downloads.findMatching(descriptor)?.also { recoveredId ->
            store.write(journal.copy(downloadId = recoveredId))
        } ?: run {
            fail(journal, ModelFailureCode.DOWNLOAD_MISSING)
            return false
        }
        return when (downloads.query(id)) {
            DownloadObservation.PENDING, DownloadObservation.RUNNING -> {
                store.write(journal.copy(operation = JournalOperation.DOWNLOADING))
                false
            }
            DownloadObservation.PAUSED -> {
                store.write(journal.copy(operation = JournalOperation.WAITING_UNMETERED))
                false
            }
            DownloadObservation.SUCCESSFUL -> install(id, journal)
            DownloadObservation.FAILED -> {
                fail(journal, ModelFailureCode.DOWNLOAD_FAILED)
                false
            }
            DownloadObservation.MISSING -> {
                fail(journal, ModelFailureCode.DOWNLOAD_MISSING)
                false
            }
        }
    }

    private fun install(id: Long, journal: DeliveryJournal): Boolean =
        try {
            space.requireCapacity(descriptor)
            store.write(journal.copy(operation = JournalOperation.VERIFYING, failureCode = null))
            downloads.open(id).use { descriptorFile ->
                ParcelFileDescriptor.AutoCloseInputStream(descriptorFile).use { input ->
                    CandidateInstaller(root).install(input, descriptor) {
                        store.write(
                            journal.copy(
                                operation = JournalOperation.INSTALLING,
                                failureCode = null,
                                activationDirectory = activationDirectory,
                            ),
                        )
                    }
                }
            }
            runCatching { downloads.remove(id) }
            activation.resumeOrActivate(store.read())
            store.read().needsActivationRetry()
        } catch (error: CandidateInstallException) {
            fail(journal, error.failureCode)
            false
        } catch (_: Exception) {
            fail(journal, ModelFailureCode.IO_ERROR)
            false
        }

    private fun fail(journal: DeliveryJournal, code: ModelFailureCode) {
        store.write(journal.copy(operation = JournalOperation.FAILED, failureCode = code))
    }

    fun cancelCurrentOperation() {
        activation.cancelCurrentOperation()
    }

    override fun close() {
        activation.close()
    }
}
