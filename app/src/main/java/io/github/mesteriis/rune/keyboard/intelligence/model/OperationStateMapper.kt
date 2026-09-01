package io.github.mesteriis.rune.keyboard.intelligence.model

import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryJournal
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DownloadObservation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.JournalOperation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelFailureCode

object OperationStateMapper {
    fun map(journal: DeliveryJournal, download: DownloadObservation?): ModelOperationState {
        if (
            journal.downloadId != null &&
            journal.operation in setOf(
                JournalOperation.QUEUED,
                JournalOperation.WAITING_UNMETERED,
                JournalOperation.DOWNLOADING,
            )
        ) {
            when (download) {
                DownloadObservation.PENDING -> return ModelOperationState.Queued
                DownloadObservation.RUNNING -> return ModelOperationState.Downloading(0, 0)
                DownloadObservation.PAUSED -> return ModelOperationState.WaitingForUnmeteredNetwork
                DownloadObservation.FAILED, DownloadObservation.MISSING ->
                    return ModelOperationState.Failed(ModelFailure.DownloadFailed)
                DownloadObservation.SUCCESSFUL, null -> Unit
            }
        }
        return map(journal)
    }

    fun map(journal: DeliveryJournal): ModelOperationState = when (journal.operation) {
        JournalOperation.IDLE -> ModelOperationState.Idle
        JournalOperation.QUEUED -> ModelOperationState.Queued
        JournalOperation.WAITING_UNMETERED -> ModelOperationState.WaitingForUnmeteredNetwork
        JournalOperation.DOWNLOADING -> ModelOperationState.Downloading(0, 0)
        JournalOperation.VERIFYING -> ModelOperationState.Verifying
        JournalOperation.INSTALLING -> ModelOperationState.Installing
        JournalOperation.SELF_TESTING -> ModelOperationState.SelfTesting
        JournalOperation.IMPORTING -> ModelOperationState.Importing
        JournalOperation.EXPORTING -> ModelOperationState.Exporting
        JournalOperation.FAILED -> ModelOperationState.Failed(mapFailure(journal.failureCode))
    }

    private fun mapFailure(code: ModelFailureCode?): ModelFailure = when (code) {
        ModelFailureCode.DOWNLOAD_MISSING, ModelFailureCode.DOWNLOAD_FAILED -> ModelFailure.DownloadFailed
        ModelFailureCode.HASH_MISMATCH -> ModelFailure.HashMismatch
        ModelFailureCode.SIZE_MISMATCH -> ModelFailure.SizeMismatch
        ModelFailureCode.INVALID_GGUF -> ModelFailure.InvalidGguf
        ModelFailureCode.INSUFFICIENT_SPACE -> ModelFailure.InsufficientSpace
        ModelFailureCode.IMPORT_FAILED -> ModelFailure.ImportFailed
        ModelFailureCode.EXPORT_FAILED -> ModelFailure.ExportFailed
        ModelFailureCode.RUNTIME_LOAD_FAILED -> ModelFailure.Internal("runtime_load_failed")
        ModelFailureCode.RUNTIME_SELF_TEST_FAILED -> ModelFailure.Internal("runtime_self_test_failed")
        ModelFailureCode.RUNTIME_CANCELLED -> ModelFailure.Cancelled
        ModelFailureCode.ROLLBACK_FAILED -> ModelFailure.Internal("rollback_failed")
        ModelFailureCode.IO_ERROR, null -> ModelFailure.Internal("io_error")
    }
}
