package io.github.mesteriis.rune.keyboard.intelligence.model

import android.content.Context
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryStateStore
import io.github.mesteriis.rune.keyboard.intelligence.delivery.EmbeddedModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelDownloadClient
import io.github.mesteriis.rune.keyboard.intelligence.delivery.CandidateInstaller
import io.github.mesteriis.rune.keyboard.intelligence.runtime.AtomicModelPointerStore
import java.io.File

class ModelSnapshotReader(
    context: Context,
    private val available: ModelDescriptor = EmbeddedModelDescriptor.load(context),
) {
    private val store = DeliveryStateStore.forApplication(context)
    private val root = store.stateFile.parentFile!!
    private val downloads = ModelDownloadClient(context)

    fun read(): ModelSnapshot {
        val candidateName = "${available.id}-${available.version}"
        val candidateFile = File(root, "candidates/$candidateName/${available.fileName}")
        val candidate = if (candidateFile.isFile) VerifiedCandidate(available, candidateName) else null
        val pointer = AtomicModelPointerStore(root).read()
        val active = pointer.activeDirectory?.let { directory -> installed(directory) }
        val rollback = pointer.rollbackDirectory?.let { directory -> installed(directory) }
        val journal = store.read()
        val mappedOperation = OperationStateMapper.map(journal)
        val operation = if (mappedOperation is ModelOperationState.Downloading && journal.downloadId != null) {
            downloads.progress(journal.downloadId)?.let {
                ModelOperationState.Downloading(it.bytesDownloaded, it.totalBytes)
            } ?: mappedOperation
        } else {
            mappedOperation
        }
        return ModelSnapshot(
            available = available,
            active = active,
            rollback = rollback,
            candidate = candidate,
            updateAvailable = active != null && active.directoryName != candidateName,
            operation = operation,
        )
    }

    private fun installed(directory: String): InstalledModel? {
        val versionDirectory = File(root, "versions/$directory")
        val manifest = File(versionDirectory, CandidateInstaller.MODEL_MANIFEST_NAME)
        val descriptor = runCatching { ModelManifestParser.parse(manifest.readText()) }.getOrNull() ?: return null
        val file = File(versionDirectory, descriptor.fileName)
        return if (file.isFile) InstalledModel(descriptor, directory) else null
    }
}
