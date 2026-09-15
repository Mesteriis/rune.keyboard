package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

/** Main-thread hooks over Rune-owned text only. Called after acknowledged editor changes. */
interface TypingPersonalization {
    fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Boolean = true
    fun preference(original: String, candidate: String, language: KeyboardLanguage): Double = 0.0
    fun accepted(original: String, replacement: String, language: KeyboardLanguage) {}
    fun rejected(original: String, replacement: String, language: KeyboardLanguage) {}
    fun confirmed(word: String, language: KeyboardLanguage) {}
    fun committed(prefix: String, word: String, retypedFrom: String?, language: KeyboardLanguage) {}
    fun continuations(context: String, language: KeyboardLanguage): List<String> = emptyList()
    fun clearPending() {}
}

object NoTypingPersonalization : TypingPersonalization
