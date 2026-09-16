package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal

data class AutomaticTypingDecision(
    val allowed: Boolean,
    val refusal: AutomaticAdmissionRefusal? = null,
)

/** Main-thread hooks over Rune-owned text only. Called after acknowledged editor changes. */
interface TypingPersonalization {
    fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Boolean = true
    /** Existing implementations that only override [allowsAutomatic] retain exactly their decision. */
    fun automaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        val allowed = allowsAutomatic(generation, candidate, language)
        return AutomaticTypingDecision(allowed,
            if (allowed) null else AutomaticAdmissionRefusal.NOT_QUALIFIED)
    }
    fun preference(original: String, candidate: String, language: KeyboardLanguage): Double = 0.0
    fun contextualPreference(context: String, original: String, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Double = preference(original, candidate.text, language)
    fun accepted(original: String, replacement: String, language: KeyboardLanguage) {}
    fun rejected(original: String, replacement: String, language: KeyboardLanguage) {}
    fun confirmed(word: String, language: KeyboardLanguage) {}
    fun committed(prefix: String, word: String, retypedFrom: String?, language: KeyboardLanguage) {}
    fun continuations(context: String, language: KeyboardLanguage): List<String> = emptyList()
    fun clearPending() {}
}

object NoTypingPersonalization : TypingPersonalization
