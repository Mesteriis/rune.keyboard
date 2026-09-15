package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Exact public dictionary evidence. A missing lemma means analysis is ambiguous, never guessed. */
data class MorphologyMembership(val available: Boolean, val present: Boolean, val lemmaId: Int? = null) {
    companion object {
        val UNAVAILABLE = MorphologyMembership(false, false)
        val ABSENT = MorphologyMembership(true, false)
    }
}

/** Immutable, thread-safe lookup; loading/validation must finish on a worker before publication. */
fun interface MorphologyLexicon {
    fun lookup(language: KeyboardLanguage, key: String): MorphologyMembership

    companion object {
        val UNAVAILABLE = MorphologyLexicon { _, _ -> MorphologyMembership.UNAVAILABLE }
    }
}
