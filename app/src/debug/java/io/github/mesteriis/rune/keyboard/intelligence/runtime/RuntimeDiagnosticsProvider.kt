package io.github.mesteriis.rune.keyboard.intelligence.runtime

object RuntimeDiagnosticsProvider {
    val instance: RuntimeDiagnosticsSink = InMemoryRuntimeDiagnostics()
}

private class InMemoryRuntimeDiagnostics : RuntimeDiagnosticsSink {
    override val enabled = true
    @Volatile private var value: RuntimeDiagnosticsSnapshot? = null
    override fun record(snapshot: RuntimeDiagnosticsSnapshot) { value = snapshot }
    override fun latest(): RuntimeDiagnosticsSnapshot? = value
}
