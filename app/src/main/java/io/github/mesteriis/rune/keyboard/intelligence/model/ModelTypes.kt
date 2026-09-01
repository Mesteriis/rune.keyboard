package io.github.mesteriis.rune.keyboard.intelligence.model

data class ModelDescriptor(
    val id: String,
    val version: String,
    val displayName: String,
    val fileName: String,
    val downloadUrl: String,
    val sha256: String,
    val sizeBytes: Long,
    val runtimeApi: Int,
    val minimumRuneVersionCode: Int,
    val ggufVersion: Int,
    val architecture: String,
    val fileType: Int,
)

data class InstalledModel(
    val descriptor: ModelDescriptor,
    val directoryName: String,
)

data class VerifiedCandidate(
    val descriptor: ModelDescriptor,
    val directoryName: String,
)

sealed interface ModelFailure {
    val stableCode: String

    data object HashMismatch : ModelFailure { override val stableCode = "hash_mismatch" }
    data object SizeMismatch : ModelFailure { override val stableCode = "size_mismatch" }
    data object InvalidGguf : ModelFailure { override val stableCode = "invalid_gguf" }
    data object InsufficientSpace : ModelFailure { override val stableCode = "insufficient_space" }
    data object DownloadFailed : ModelFailure { override val stableCode = "download_failed" }
    data object ImportFailed : ModelFailure { override val stableCode = "import_failed" }
    data object ExportFailed : ModelFailure { override val stableCode = "export_failed" }
    data object Cancelled : ModelFailure { override val stableCode = "cancelled" }
    data class Internal(override val stableCode: String) : ModelFailure
}

sealed interface ModelOperationState {
    data object Idle : ModelOperationState
    data object Queued : ModelOperationState
    data object WaitingForUnmeteredNetwork : ModelOperationState
    data class Downloading(val bytesDownloaded: Long, val totalBytes: Long) : ModelOperationState
    data object Verifying : ModelOperationState
    data object Installing : ModelOperationState
    data object SelfTesting : ModelOperationState
    data object Importing : ModelOperationState
    data object Exporting : ModelOperationState
    data class Failed(val failure: ModelFailure) : ModelOperationState
}

data class ModelSnapshot(
    val available: ModelDescriptor,
    val active: InstalledModel?,
    val rollback: InstalledModel?,
    val candidate: VerifiedCandidate?,
    val updateAvailable: Boolean,
    val operation: ModelOperationState,
) {
    val isNotInstalled: Boolean get() = active == null && candidate == null
    val isReady: Boolean get() = active != null
    val isUpdateAvailable: Boolean get() = active != null && updateAvailable
}
