package io.github.mesteriis.rune.keyboard.intelligence.ui

import io.github.mesteriis.rune.keyboard.intelligence.model.InstalledModel
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelFailure
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelOperationState
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelSnapshot
import io.github.mesteriis.rune.keyboard.intelligence.model.VerifiedCandidate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelSettingsViewStateTest {
    private val descriptor = ModelDescriptor("rune-text-v1", "0.1.0", "Rune Text 0.1", "model.gguf", "https://github.com/Mesteriis/rune.keyboard/releases/download/tag/model.gguf", "a".repeat(64), 10, 1, 2, 3, "qwen3", 15)

    @Test
    fun notInstalledOffersDownloadAndImport() {
        val view = ModelSettingsViewState.from(snapshot())
        assertEquals(ModelCardStatus.NOT_INSTALLED, view.status)
        assertTrue(view.canDownload)
        assertTrue(view.canImport)
        assertFalse(view.canExport)
    }

    @Test
    fun candidateSelfTestIsBusyAndNotReady() {
        val view = ModelSettingsViewState.from(snapshot(candidate = VerifiedCandidate(descriptor, "candidate"), operation = ModelOperationState.SelfTesting))
        assertEquals(ModelCardStatus.VERIFYING_CANDIDATE, view.status)
        assertTrue(view.isBusy)
        assertFalse(view.canDownload)
    }

    @Test
    fun failedUpdateKeepsReadyActionsAndFailure() {
        val view = ModelSettingsViewState.from(snapshot(active = InstalledModel(descriptor, "active"), update = true, operation = ModelOperationState.Failed(ModelFailure.HashMismatch)))
        assertEquals(ModelCardStatus.READY, view.status)
        assertTrue(view.canExport)
        assertTrue(view.canDelete)
        assertEquals("hash_mismatch", view.failureCode)
    }

    @Test
    fun interruptedDeleteKeepsDeleteActionWithoutVisibleModelFiles() {
        val view = ModelSettingsViewState.from(
            snapshot(operation = ModelOperationState.Failed(ModelFailure.Internal("delete_failed"))),
        )

        assertEquals(ModelCardStatus.NOT_INSTALLED, view.status)
        assertTrue(view.canDelete)
        assertFalse(view.canDownload)
        assertFalse(view.canImport)
        assertFalse(view.canExport)
    }

    @Test
    fun currentActiveVersionRejectsRedundantImport() {
        val active = InstalledModel(descriptor, "${descriptor.id}-${descriptor.version}")

        val view = ModelSettingsViewState.from(snapshot(active = active))

        assertFalse(view.canImport)
        assertTrue(view.canExport)
    }

    private fun snapshot(
        active: InstalledModel? = null,
        candidate: VerifiedCandidate? = null,
        update: Boolean = false,
        operation: ModelOperationState = ModelOperationState.Idle,
    ) = ModelSnapshot(descriptor, active, null, candidate, update, operation)
}
