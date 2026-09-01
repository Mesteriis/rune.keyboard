package io.github.mesteriis.rune.keyboard.intelligence.model

import android.content.Context
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryStateStore
import io.github.mesteriis.rune.keyboard.intelligence.delivery.EmbeddedModelDescriptor
import java.io.File

class ModelSnapshotReader(
    context: Context,
    private val available: ModelDescriptor = EmbeddedModelDescriptor.load(context),
) {
    private val store = DeliveryStateStore.forApplication(context)
    private val root = store.stateFile.parentFile!!

    fun read(): ModelSnapshot {
        val candidateName = "${available.id}-${available.version}"
        val candidateFile = File(root, "candidates/$candidateName/${available.fileName}")
        val candidate = if (candidateFile.isFile) VerifiedCandidate(available, candidateName) else null
        return ModelSnapshot(
            available = available,
            active = null,
            rollback = null,
            candidate = candidate,
            updateAvailable = false,
            operation = OperationStateMapper.map(store.read()),
        )
    }
}
