package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon

enum class AutomaticAdmissionRefusal {
    MORPHOLOGY_UNAVAILABLE, ORIGINAL_VALID, WINNER_AMBIGUOUS, RIVAL_OTHER_LEMMA, NOT_QUALIFIED,
    TARGET_UNKNOWN, RIVAL_UNKNOWN, RESOURCE_UNAVAILABLE,
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
    /** Extra veto after the separate rescue source has passed its own quality qualification. */
    internal fun evaluateRescue(generation: CandidateGeneration, candidate: GeneratedCandidate): AutomaticAdmissionDecision =
        evaluateQualifiedPool(generation, candidate, 5)

    internal fun evaluateWordContext(generation: CandidateGeneration, candidate: GeneratedCandidate): AutomaticAdmissionDecision {
        if (generation.isValidWord) return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null) return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        if (!io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordContextPolicy.isReviewedPair(
                generation.original.orEmpty(), candidate.text) || candidate.unitDistance != 1)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return evaluateQualifiedPool(generation, candidate, 3)
    }

    private fun evaluateQualifiedPool(generation: CandidateGeneration, candidate: GeneratedCandidate,
        minimumLength: Int): AutomaticAdmissionDecision {
        if (candidate.language != KeyboardLanguage.RUSSIAN || generation.original?.length !in minimumLength..32 ||
            !generation.jointEvaluated || !generation.jointSearch.isComplete ||
            candidate !in generation.jointSearch.alternatives || candidate.frequencyRank !in 1..50_000 ||
            !candidate.editFeatures.editCost.isFinite() || candidate.editFeatures.editCost < 0)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val original = lexicon.lookup(candidate.language, TokenUnicode.folded(generation.original!!))
        val target = lexicon.lookup(candidate.language, candidate.terminalKey)
        if (!original.available || !target.available)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (original.present) return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.ORIGINAL_VALID)
        return if (target.present) AutomaticAdmissionDecision(true)
        else AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.TARGET_UNKNOWN)
    }
    fun allows(generation: CandidateGeneration, candidate: GeneratedCandidate): Boolean =
        evaluate(generation, candidate).allowed

    fun evaluate(generation: CandidateGeneration, candidate: GeneratedCandidate): AutomaticAdmissionDecision =
        evaluate(generation, candidate, emptySet())

    /** Same-request model evidence can resolve only rivals actually included in that comparison. */
    internal fun evaluateRefinement(generation: CandidateGeneration, candidate: GeneratedCandidate,
        comparedWords: List<String>): AutomaticAdmissionDecision = evaluate(generation.copy(
            alternatives = (generation.alternatives + generation.localSearch.alternatives +
                generation.neighborRecovery.alternatives).distinctBy { it.canonicalKey },
            localSearch = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalSearchEvidence.NONE),
        candidate.copy(kind = GeneratedCandidateKind.SPELLING), comparedWords.toSet())

    /** Called after the qualified joint model compared the original and its complete pool. */
    internal fun evaluateJoint(generation: CandidateGeneration, candidate: GeneratedCandidate,
        qualifiedAmbiguousWinner: Boolean): AutomaticAdmissionDecision {
        if (!generation.jointEvaluated || !generation.jointSearch.isComplete ||
            candidate !in generation.jointSearch.alternatives)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val compared = listOf(generation.original.orEmpty()) + generation.jointSearch.alternatives.map { it.text }
        val decision = evaluateRefinement(generation.copy(alternatives = generation.jointSearch.alternatives),
            candidate, compared)
        if (decision.allowed || !qualifiedAmbiguousWinner ||
            decision.refusal != AutomaticAdmissionRefusal.WINNER_AMBIGUOUS) return decision
        // A missing lemma is not a missing word. This separate cohort still requires a known
        // target and exactly one alternative in the exhaustive distance-one search. Competing
        // local words, incomplete searches and other admission paths retain the existing veto.
        val winner = lexicon.lookup(candidate.language, candidate.terminalKey)
        if (!winner.available || !winner.present || winner.lemmaId != null ||
            !candidate.editFeatures.editCost.isFinite() || candidate.editFeatures.editCost < 0 ||
            !generation.localSearch.isComplete ||
            generation.localSearch.alternatives.singleOrNull()?.canonicalKey != candidate.canonicalKey)
            return decision
        return AutomaticAdmissionDecision(true)
    }

    private fun evaluate(generation: CandidateGeneration, candidate: GeneratedCandidate,
        modelCompared: Set<String>): AutomaticAdmissionDecision {
        if (candidate.language != KeyboardLanguage.RUSSIAN) return AutomaticAdmissionDecision(true)
        val original = generation.original ?: return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val source = TokenUnicode.folded(original)
        // Case-only spelling identity is not a word substitution; existing case eligibility owns it.
        if (candidate.kind == GeneratedCandidateKind.CANONICAL_CASE &&
            source == TokenUnicode.folded(candidate.text)) return AutomaticAdmissionDecision(true)
        // The finite reviewed source owns its exact substitution policy. Recheck the complete
        // mapping identity here so a mislabeled candidate cannot bypass morphology admission.
        if (candidate.kind == GeneratedCandidateKind.COMMON_CONFUSION) {
            val target = CommonConfusions.target(candidate.language, source)
            val display = target?.let { CasePattern.analyze(original).preserve(it) }
            return if (target != null && candidate.terminalKey == target && candidate.text == display)
                AutomaticAdmissionDecision(true)
            else AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        }
        val originalEvidence = lexicon.lookup(candidate.language, source)
        if (!originalEvidence.available)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (originalEvidence.present)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.ORIGINAL_VALID)
        // General-local admission has its own frozen >=99% qualification over the complete
        // distance-one set. Morphology adds protection for a dictionary-valid original, but its
        // incomplete/ambiguous lemma graph must not revoke an independently qualified winner.
        if (LocalCorrectionPolicy.decide(generation, candidate.language)?.canonicalKey == candidate.canonicalKey)
            return AutomaticAdmissionDecision(true)
        val winner = lexicon.lookup(candidate.language, candidate.terminalKey)
        val lemma = winner.lemmaId
        if (!winner.available)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (!winner.present)
            return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.TARGET_UNKNOWN)
        if (lemma == null)
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
                return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.RIVAL_UNKNOWN)
            if (evidence.lemmaId != lemma && (candidate.text !in modelCompared || other.text !in modelCompared))
                return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.RIVAL_OTHER_LEMMA)
        }
        return AutomaticAdmissionDecision(true)
    }

    companion object {
        const val VERSION = 1
        const val PLAUSIBLE_EDIT_COST_MARGIN = 0.25
    }
}

/** Additional public-word veto shared by Android and replay; never creates or ranks a winner. */
object PublicOriginalProtection {
    /** Manual suggestions remain useful even when a lower-case short entity protects the original. */
    fun manualPreference(original: String, candidate: GeneratedCandidate, morphology: MorphologyLexicon,
        rareWords: RareWordLexicon): Double {
        if (candidate.language != KeyboardLanguage.RUSSIAN || original.length !in 3..4 ||
            CasePattern.analyze(original) != CasePattern.LOWER || candidate.unitDistance !in 1..2 ||
            candidate.frequencyRank < 1) return 0.0
        val key = TokenUnicode.folded(original)
        val morph = morphology.lookup(candidate.language, key)
        val rare = rareWords.lookup(key)
        if (!morph.available || morph.present || !rare.available || !rare.present) return 0.0
        return 0.5 / (1.0 + candidate.frequencyRank / 5000.0) / candidate.unitDistance
    }

    fun evaluate(generation: CandidateGeneration, candidate: GeneratedCandidate,
        rareWords: RareWordLexicon): AutomaticAdmissionDecision {
        if (candidate.language != KeyboardLanguage.RUSSIAN ||
            candidate.kind == GeneratedCandidateKind.CANONICAL_CASE ||
            candidate.kind == GeneratedCandidateKind.COMMON_CONFUSION) return AutomaticAdmissionDecision(true)
        val original = generation.original
            ?: return AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val source = rareWords.lookup(TokenUnicode.folded(original))
        return when {
            !source.available -> AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
            source.present -> AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.ORIGINAL_VALID)
            else -> AutomaticAdmissionDecision(true)
        }
    }
}
