package io.github.mesteriis.rune.keyboard.ime.editor

/**
 * Rules for the double-space-to-period conversion (SPACE-002).
 *
 * The decision needs the two characters directly before the cursor. That bounded read happens
 * only for eligible editors (plain text, never passwords, never TYPE_NULL) and the text is
 * never stored, logged, or compared against anything but these rules.
 */
object DoubleSpacePeriod {
    private val FORBIDDEN_PRECEDING = setOf('.', ',', '!', '?')

    /** [before] is the result of `getTextBeforeCursor(2, 0)` taken at the second space tap. */
    fun canConvert(before: CharSequence?): Boolean {
        if (before == null || before.length < 2) return false
        val separator = before[before.length - 1]
        val preceding = before[before.length - 2]
        return separator == ' ' &&
            !preceding.isWhitespace() &&
            preceding !in FORBIDDEN_PRECEDING
    }

    /** Verifies that the text still looks like our own conversion before undoing it. */
    fun canRevert(before: CharSequence?): Boolean {
        if (before == null || before.length < 2) return false
        return before[before.length - 2] == '.' && before[before.length - 1] == ' '
    }
}
