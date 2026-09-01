package io.github.mesteriis.rune.keyboard.intelligence.model

import android.content.Context
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryStateStore
import io.github.mesteriis.rune.keyboard.intelligence.delivery.EmbeddedModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelDownloadClient
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
        val journal = store.read()
        val download = journal.downloadId?.let(downloads::query)
        return ModelSnapshot(
            available = available,
            active = null,
            rollback = null,
            candidate = candidate,
            updateAvailable = false,
            operation = OperationStateMapper.map(journal, download),
        )
    }
}
