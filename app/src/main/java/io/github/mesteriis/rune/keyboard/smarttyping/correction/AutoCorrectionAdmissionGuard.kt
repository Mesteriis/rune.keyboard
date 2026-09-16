package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon

enum class AutomaticAdmissionRefusal {
    MORPHOLOGY_UNAVAILABLE, ORIGINAL_VALID, WINNER_AMBIGUOUS, RIVAL_OTHER_LEMMA, NOT_QUALIFIED,
}
data class AutomaticAdmissionDecision(
    val allowed: Boolean,
    val refusal: AutomaticAdmissionRefusal? = null,
)

/**
 * Additional automatic-action veto, never a ranker or a qualification grant. Suggestions survive.
 * Call only AFTER every existing automatic policy and editor ownership gate has admitted a winner.
 */
class AutoCorrectionAdmissionGuard(private val lexicon: MorphologyLexicon) {
    fun allows(generation: CandidateGeneration, candidate: GeneratedCandidate): Boolean =
        evaluate(generation, candidate).allowed

    fun evaluate(generation: CandidateGeneration, candidate: GeneratedCandidate): AutomaticAdmissionDecision {
        if (candidate.language != KeyboardLanguage.RUSSIAN) return AutomaticAdmissionDecision(true)
        val original = generation.original ?: return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val source = TokenUnicode.folded(original)
        // Case-only spelling identity is not a word substitution; existing case eligibility owns it.
        if (candidate.kind == GeneratedCandidateKind.CANONICAL_CASE &&
            source == TokenUnicode.folded(candidate.text)) return AutomaticAdmissionDecision(true)
        val originalEvidence = lexicon.lookup(candidate.language, source)
        if (!originalEvidence.available)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (originalEvidence.present)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.ORIGINAL_VALID)
        val winner = lexicon.lookup(candidate.language, candidate.terminalKey)
        val lemma = winner.lemmaId
        if (!winner.available)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (!winner.present || lemma == null)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.WINNER_AMBIGUOUS)
        val cost = candidate.editFeatures.editCost
        if (!cost.isFinite() || cost < 0)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        // One quarter of a unit edit is a conservative plausibility band, not calibrated confidence.
        // A frequency gap cannot resolve equally plausible words from different lemma families.
        for (other in generation.localSearch.alternatives + generation.alternatives) {
            if (other.language != candidate.language || other.terminalKey == candidate.terminalKey) continue
            val otherCost = other.editFeatures.editCost
            if (!otherCost.isFinite() || otherCost < 0)
                return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
            if (otherCost > cost + PLAUSIBLE_EDIT_COST_MARGIN) continue
            val evidence = lexicon.lookup(other.language, other.terminalKey)
            if (!evidence.available)
                return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
            if (!evidence.present || evidence.lemmaId == null)
                return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.WINNER_AMBIGUOUS)
            if (evidence.lemmaId != lemma)
                return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.RIVAL_OTHER_LEMMA)
        }
        return AutomaticAdmissionDecision(true)
    }

    companion object {
        const val PLAUSIBLE_EDIT_COST_MARGIN = 0.25
    }
}
