package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.Context
import android.net.Uri
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.VerifiedCandidate
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

class SafModelTransfer(
    private val context: Context,
    private val descriptor: ModelDescriptor,
) {
    private val store = DeliveryStateStore.forApplication(context)
    private val root = store.stateFile.parentFile!!
    private val resolver = context.contentResolver
    private val activationDirectory = "${descriptor.id}-${descriptor.version}"

    fun import(uri: Uri): VerifiedCandidate {
        store.write(DeliveryJournal(operation = JournalOperation.IMPORTING))
        return try {
            ModelStorageSpace(ModelDownloadClient.externalStaging(context), root).requirePrivateCopyCapacity(descriptor)
            val candidate = requireNotNull(resolver.openInputStream(uri)) { "Document provider returned no input" }
                .use { input ->
                    CandidateInstaller(root).install(input, descriptor) {
                        store.write(
                            DeliveryJournal(
                                operation = JournalOperation.INSTALLING,
                                activationDirectory = activationDirectory,
                            ),
                        )
                    }
                }
            store.write(DeliveryJournal())
            candidate
        } catch (error: CandidateInstallException) {
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = error.failureCode))
            throw error
        } catch (error: Exception) {
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.IO_ERROR))
            throw error
        }
    }

    fun export(activeModel: File, uri: Uri) {
        require(activeModel.isFile) { "Active model is missing" }
        store.write(DeliveryJournal(operation = JournalOperation.EXPORTING))
        try {
            val descriptorFile = requireNotNull(resolver.openFileDescriptor(uri, "rwt")) {
                "Document provider returned no destination"
            }
            descriptorFile.use { destination ->
                FileInputStream(activeModel).use { input ->
                    FileOutputStream(destination.fileDescriptor).use { output ->
                        ModelFileExporter.copy(input, output) { resolver.delete(uri, null, null) }
                        output.fd.sync()
                    }
                }
            }
            store.write(DeliveryJournal())
        } catch (error: Exception) {
            runCatching { resolver.delete(uri, null, null) }
            store.write(DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.IO_ERROR))
            throw error
        }
    }
}
