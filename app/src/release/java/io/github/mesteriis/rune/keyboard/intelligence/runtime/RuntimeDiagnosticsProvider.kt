package io.github.mesteriis.rune.keyboard.intelligence.runtime

object RuntimeDiagnosticsProvider {
    val instance: RuntimeDiagnosticsSink = object : RuntimeDiagnosticsSink {
        override val enabled = false
        override fun record(snapshot: RuntimeDiagnosticsSnapshot) = Unit
        override fun latest(): RuntimeDiagnosticsSnapshot? = null
    }
}
