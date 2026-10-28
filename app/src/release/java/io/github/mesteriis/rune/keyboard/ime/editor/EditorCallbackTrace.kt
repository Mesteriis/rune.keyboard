package io.github.mesteriis.rune.keyboard.ime.editor

object EditorCallbackTrace {
    const val STATIONARY_CURSOR = 1
    const val COMPOSING_SPAN = 2
    const val SESSION_DISABLED_EXTERNALLY = 4
    const val SESSION_ENABLED = 8
    const val EXTERNAL_CHANGE = 16
    const val INVALID_SELECTION = 32
    const val MASK = 63
    fun record(flags: Int) = Unit
}
