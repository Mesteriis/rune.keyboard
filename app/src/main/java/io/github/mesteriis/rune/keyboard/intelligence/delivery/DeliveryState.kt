package io.github.mesteriis.rune.keyboard.intelligence.delivery

enum class JournalOperation {
    IDLE,
    QUEUED,
    WAITING_UNMETERED,
    DOWNLOADING,
    VERIFYING,
    INSTALLING,
    SELF_TESTING,
    IMPORTING,
    EXPORTING,
    FAILED,
}

enum class ModelFailureCode {
    DOWNLOAD_MISSING,
    DOWNLOAD_FAILED,
    HASH_MISMATCH,
    SIZE_MISMATCH,
    INVALID_GGUF,
    INSUFFICIENT_SPACE,
    IO_ERROR,
    IMPORT_FAILED,
    EXPORT_FAILED,
}

data class DeliveryJournal(
    val operation: JournalOperation = JournalOperation.IDLE,
    val downloadId: Long? = null,
    val allowMetered: Boolean = false,
    val failureCode: ModelFailureCode? = null,
)

enum class DownloadObservation { MISSING, PENDING, RUNNING, PAUSED, SUCCESSFUL, FAILED }

data class PrivateObservation(
    val candidateExists: Boolean,
    val installingExists: Boolean,
) {
    companion object {
        val EMPTY = PrivateObservation(candidateExists = false, installingExists = false)
    }
}

sealed interface ReconcileAction {
    data object Idle : ReconcileAction
    data object WaitingForDownload : ReconcileAction
    data object WaitingForUnmeteredNetwork : ReconcileAction
    data class VerifyDownload(val downloadId: Long) : ReconcileAction
    data object AdoptVerifiedCandidate : ReconcileAction
    data object RemovePartialAndRetry : ReconcileAction
    data class Fail(val code: ModelFailureCode) : ReconcileAction
}

data class MeteredRequeue(
    val removeDownloadId: Long,
    val requeueAllowedOverMetered: Boolean,
    val requeueAllowedOverRoaming: Boolean,
)

object DeliveryReconciler {
    fun reconcile(
        journal: DeliveryJournal,
        download: DownloadObservation,
        privateFiles: PrivateObservation,
    ): ReconcileAction {
        if (privateFiles.candidateExists) return ReconcileAction.AdoptVerifiedCandidate
        if (privateFiles.installingExists) {
            return if (download == DownloadObservation.SUCCESSFUL) {
                ReconcileAction.RemovePartialAndRetry
            } else {
                ReconcileAction.Fail(ModelFailureCode.IO_ERROR)
            }
        }
        if (journal.operation == JournalOperation.IDLE) return ReconcileAction.Idle
        val id = journal.downloadId
        return when (download) {
            DownloadObservation.PENDING, DownloadObservation.RUNNING -> ReconcileAction.WaitingForDownload
            DownloadObservation.PAUSED -> ReconcileAction.WaitingForUnmeteredNetwork
            DownloadObservation.SUCCESSFUL -> if (id != null) {
                ReconcileAction.VerifyDownload(id)
            } else {
                ReconcileAction.Fail(ModelFailureCode.DOWNLOAD_MISSING)
            }
            DownloadObservation.FAILED -> ReconcileAction.Fail(ModelFailureCode.DOWNLOAD_FAILED)
            DownloadObservation.MISSING -> ReconcileAction.Fail(ModelFailureCode.DOWNLOAD_MISSING)
        }
    }

    fun requestMeteredOverride(journal: DeliveryJournal): MeteredRequeue {
        require(journal.operation == JournalOperation.WAITING_UNMETERED) { "operation is not waiting" }
        val id = requireNotNull(journal.downloadId) { "downloadId is missing" }
        return MeteredRequeue(id, requeueAllowedOverMetered = true, requeueAllowedOverRoaming = false)
    }
}
