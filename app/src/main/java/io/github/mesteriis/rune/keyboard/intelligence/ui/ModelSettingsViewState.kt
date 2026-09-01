package io.github.mesteriis.rune.keyboard.intelligence.ui

import io.github.mesteriis.rune.keyboard.intelligence.model.ModelOperationState
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelSnapshot

enum class ModelCardStatus {
    NOT_INSTALLED,
    VERIFYING_CANDIDATE,
    READY,
    UPDATE_AVAILABLE,
}

data class ModelSettingsViewState(
    val status: ModelCardStatus,
    val canDownload: Boolean,
    val canImport: Boolean,
    val canExport: Boolean,
    val canDelete: Boolean,
    val isBusy: Boolean,
    val failureCode: String?,
) {
    companion object {
        fun from(snapshot: ModelSnapshot): ModelSettingsViewState {
            val operation = snapshot.operation
            val isBusy = operation !is ModelOperationState.Idle &&
                operation !is ModelOperationState.Failed
            val status = when {
                snapshot.active != null && operation is ModelOperationState.Failed -> ModelCardStatus.READY
                snapshot.active != null && snapshot.updateAvailable -> ModelCardStatus.UPDATE_AVAILABLE
                snapshot.active != null -> ModelCardStatus.READY
                snapshot.candidate != null -> ModelCardStatus.VERIFYING_CANDIDATE
                else -> ModelCardStatus.NOT_INSTALLED
            }
            return ModelSettingsViewState(
                status = status,
                canDownload = !isBusy,
                canImport = !isBusy,
                canExport = snapshot.active != null && !isBusy,
                canDelete = snapshot.active != null || snapshot.rollback != null ||
                    snapshot.candidate != null || isBusy,
                isBusy = isBusy,
                failureCode = (operation as? ModelOperationState.Failed)?.failure?.stableCode,
            )
        }
    }
}
