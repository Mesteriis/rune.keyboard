package io.github.mesteriis.rune.keyboard.ime.gesture

/**
 * Backspace hold acceleration (INPUT-104). Deletion stays per code point at every speed —
 * word deletion would require reading the surrounding text.
 */
object BackspaceRepeatSchedule {
    const val INITIAL_INTERVAL_MILLIS = 55L
    const val FAST_INTERVAL_MILLIS = 33L
    const val TURBO_INTERVAL_MILLIS = 18L

    const val FAST_AFTER_REPEATS = 8
    const val TURBO_AFTER_REPEATS = 24

    fun intervalMillis(repeatCount: Int): Long = when {
        repeatCount >= TURBO_AFTER_REPEATS -> TURBO_INTERVAL_MILLIS
        repeatCount >= FAST_AFTER_REPEATS -> FAST_INTERVAL_MILLIS
        else -> INITIAL_INTERVAL_MILLIS
    }
}
