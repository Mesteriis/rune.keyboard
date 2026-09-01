package io.github.mesteriis.rune.keyboard.intelligence.runtime

data class RuntimeDiagnosticsSnapshot(
    val runtimeCommit: String,
    val abi: String,
    val backend: String,
    val model: String,
    val quantization: String,
    val loadMillis: Long,
    val promptMillis: Long,
    val firstTokenMillis: Long,
    val unloadMillis: Long,
    val rssKb: Long,
    val totalPssKb: Int,
    val totalPrivateDirtyKb: Int,
)

interface RuntimeDiagnosticsSink {
    val enabled: Boolean
    fun record(snapshot: RuntimeDiagnosticsSnapshot)
    fun latest(): RuntimeDiagnosticsSnapshot?
}
