package io.github.mesteriis.rune.keyboard.intelligence.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelSnapshotTest {
    private val descriptor = ModelDescriptor(
        id = "rune-text-v1",
        version = "0.1.0",
        displayName = "Rune Text 0.1",
        fileName = "model.gguf",
        downloadUrl = "https://github.com/Mesteriis/rune.keyboard/releases/download/tag/model.gguf",
        sha256 = "a".repeat(64),
        sizeBytes = 1,
        runtimeApi = 1,
        minimumRuneVersionCode = 2,
        ggufVersion = 3,
        architecture = "qwen3",
        fileType = 15,
    )

    @Test
    fun failedUpdateDoesNotHideActiveModel() {
        val installed = InstalledModel(descriptor, "rune-text-v1-0.1.0")
        val snapshot = ModelSnapshot(
            available = descriptor.copy(version = "0.2.0"),
            active = installed,
            rollback = null,
            candidate = null,
            updateAvailable = true,
            operation = ModelOperationState.Failed(ModelFailure.HashMismatch),
        )

        assertTrue(snapshot.isReady)
        assertTrue(snapshot.isUpdateAvailable)
        assertFalse(snapshot.isNotInstalled)
    }
}
