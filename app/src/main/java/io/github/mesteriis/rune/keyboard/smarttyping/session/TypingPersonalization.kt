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
    /** Display-only preference after a joint abstention; it cannot authorize a replacement. */
    fun abstainingJointPreference(context: String, original: String, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Double = 0.0
    fun wordContextAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision = AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
    fun rescueAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision = AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
    fun jointAutomaticEvaluation(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, baselineWord: String? = null) =
        io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionEvaluation(
            jointAutomaticChoice(context, generation, language, baselineWord))
    fun awaitingJointCandidates(generation: CandidateGeneration, language: KeyboardLanguage): Boolean = false
    fun jointAutomaticChoice(context: String, generation: CandidateGeneration, language: KeyboardLanguage, baselineWord: String? = null):
        io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice? = null
    fun contextualAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision = AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
    fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision = AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)

    fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Boolean = true
    /** Existing implementations that only override [allowsAutomatic] retain exactly their decision. */
    fun automaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        val allowed = allowsAutomatic(generation, candidate, language)
        return AutomaticTypingDecision(allowed,
            if (allowed) null else AutomaticAdmissionRefusal.NOT_QUALIFIED)
    }
    /** A second model decision must recheck the whole candidate pool and personal vetoes. */
    fun refinementDecision(generation: CandidateGeneration, word: String,
        language: KeyboardLanguage, comparedWords: List<String> = emptyList()): AutomaticTypingDecision {
        if (word == generation.original) return AutomaticTypingDecision(true)
        val all = generation.alternatives + generation.compactAlternatives + generation.neighborRecovery.alternatives
        val candidate = all.firstOrNull { it.text == word } ?: return AutomaticTypingDecision(false)
        return automaticDecision(generation.copy(alternatives = all.distinctBy { it.canonicalKey },
            localSearch = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalSearchEvidence.NONE),
            candidate.copy(kind = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind.SPELLING), language)
    }
    fun preference(original: String, candidate: String, language: KeyboardLanguage): Double = 0.0
    fun contextualPreference(context: String, original: String, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Double = preference(original, candidate.text, language)
    fun recoveryAutomaticCandidate(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): GeneratedCandidate? = null
    fun recoveryAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision = AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
    fun compactAutomaticCandidate(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): GeneratedCandidate? = null
    fun compactAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision =
        AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
    fun accepted(original: String, replacement: String, language: KeyboardLanguage) {}
    fun rejected(original: String, replacement: String, language: KeyboardLanguage) {}
    fun confirmed(word: String, language: KeyboardLanguage) {}
    fun committed(prefix: String, word: String, retypedFrom: String?, language: KeyboardLanguage) {}
    fun continuations(context: String, language: KeyboardLanguage): List<String> = emptyList()
    fun clearPending() {}
}

object NoTypingPersonalization : TypingPersonalization
