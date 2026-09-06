package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

data class CanonicalCase(val text: String, val unambiguous: Boolean) {
    override fun toString(): String = "CanonicalCase(redacted)"
}

fun interface CanonicalCaseLexicon {
    /** Exact bounded lookup. Implementations must not retain [key]. */
    fun lookup(language: KeyboardLanguage, key: String): CanonicalCase?

    companion object {
        val EMPTY = CanonicalCaseLexicon { _, _ -> null }
    }
}
