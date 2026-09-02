package io.github.mesteriis.rune.keyboard.ime.editor

/**
 * Rules for the double-space-to-period conversion (SPACE-002).
 *
 * The decision uses only the current Rune-owned RAM suffix supplied by the typing controller.
 * It never reads an editor. Undo belongs to the controller's single transaction.
 */
object DoubleSpacePeriod {
    private val FORBIDDEN_PRECEDING = setOf('.', ',', '!', '?')

    /** [before] is a Rune-owned suffix, never surrounding text obtained from the editor. */
    fun canConvert(before: CharSequence?): Boolean {
        if (before == null || before.length < 2) return false
        val separator = before[before.length - 1]
        val preceding = before[before.length - 2]
        return separator == ' ' &&
            !preceding.isWhitespace() &&
            preceding !in FORBIDDEN_PRECEDING
    }

}
