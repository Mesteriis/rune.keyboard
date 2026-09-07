package io.github.mesteriis.rune.keyboard.intelligence.readiness

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.ipc.QualifiedModelArtifact
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelResolver
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import java.io.File

/** Invoke off main. Reads bounded metadata and stats only; never creates storage or opens GGUF. */
class DiskModelReadinessProbe(private val root: () -> File) {
    fun read(cancelled: () -> Boolean): ModelReadinessHint {
        if (cancelled()) return ModelReadinessHint.UNKNOWN
        return try {
            val directory = root()
            if (!directory.isDirectory) return ModelReadinessHint.MISSING
            val gate = ModelOperationGate(directory)
            gate.tryWithReadLock {
                if (cancelled()) return@tryWithReadLock ModelReadinessHint.UNKNOWN
                val model = ActiveModelResolver(directory).resolve()
                if (cancelled()) ModelReadinessHint.UNKNOWN
                else if (model == null) ModelReadinessHint.MISSING
                else if (!QualifiedModelArtifact.accepts(model.descriptor.sha256, model.descriptor.runtimeApi))
                    ModelReadinessHint.BROKEN else ModelReadinessHint.READY
            } ?: ModelReadinessHint.UNKNOWN
        } catch (_: Exception) { ModelReadinessHint.BROKEN }
    }
}
