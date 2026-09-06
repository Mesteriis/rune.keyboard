package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.content.Context

object TypingDiagnosticsProvider {
    fun create(context: Context): TypingDiagnostics = NoTypingDiagnostics
}
