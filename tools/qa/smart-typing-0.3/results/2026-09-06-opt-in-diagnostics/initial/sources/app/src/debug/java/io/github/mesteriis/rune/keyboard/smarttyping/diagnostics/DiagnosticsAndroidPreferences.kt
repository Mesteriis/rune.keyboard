package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.content.Context

/** Fixed debug preference capability. Called only by the managed writer. */
internal class DiagnosticsAndroidPreferences(private val context: Context) {
    fun read(): Map<String, *> = context.getSharedPreferences(NAME, Context.MODE_PRIVATE).all
    fun write(value: DiagnosticsPreferences): Boolean = context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
        .edit().putBoolean(DiagnosticsPreferences.METADATA, value.metadata)
        .putBoolean(DiagnosticsPreferences.TEXT, value.text)
        .putInt(DiagnosticsPreferences.CONSENT, if (value.text) 1 else 0).commit()
    companion object { const val NAME = "rune_debug_typing_diagnostics" }
}
