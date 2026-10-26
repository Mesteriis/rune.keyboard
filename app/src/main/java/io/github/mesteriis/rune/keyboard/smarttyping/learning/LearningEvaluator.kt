package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

data class LearningEvaluation(
    val heldOut: Int, val evaluated: Int, val unavailable: Int, val missingCandidates: Int,
    val baselineTop: Int, val learnedTop: Int, val identities: Int, val baselinePreserved: Int,
    val learnedPreserved: Int, val policyMatches: Int, val improvements: Int, val regressions: Int,
    val cancelled: Boolean, val promotion: LearningPromotionDecision,
)

data class LearningPromotionDecision(
    val promotionApproved: Boolean,
    /** Candidate stays inactive; an already-canarying caller must restore its rollback slot. */
    val rollbackRequired: Boolean,
    val reasons: List<String>,
)

/** Local top-suggestion replay only. Frozen training evidence never includes held-out expected words. */
object LearningEvaluator {
    /** Stable ties preserve the local generator order, matching the live preference ordering. */
    fun rerank(snapshot: LearningSnapshot, original: String, language: KeyboardLanguage,
        alternatives: List<GeneratedCandidate>): List<GeneratedCandidate> =
        rerank(snapshot.candidatePolicy(), original, language, alternatives)

    private fun rerank(policy: LearningPatternPolicy, original: String, language: KeyboardLanguage,
        alternatives: List<GeneratedCandidate>): List<GeneratedCandidate> = alternatives.sortedByDescending {
        LearningModel.preference(policy, original, it.text, language)
    }

    fun evaluate(snapshot: LearningSnapshot,
        generate: (String, KeyboardLanguage) -> CandidateGeneration,
        cancelled: () -> Boolean = { false }): LearningEvaluation = evaluatePolicies(snapshot,
        snapshot.activePolicy, snapshot.candidatePolicy(), generate, cancelled)

    /** Canary replay: the rollback slot is baseline and the current active slot is challenged. */
    fun evaluateRollback(snapshot: LearningSnapshot,
        generate: (String, KeyboardLanguage) -> CandidateGeneration,
        cancelled: () -> Boolean = { false }): LearningEvaluation? = snapshot.rollbackPolicy?.let {
        evaluatePolicies(snapshot, it, snapshot.activePolicy, generate, cancelled)
    }

    private fun evaluatePolicies(snapshot: LearningSnapshot, baselinePolicy: LearningPatternPolicy,
        learnedPolicy: LearningPatternPolicy,
        generate: (String, KeyboardLanguage) -> CandidateGeneration,
        cancelled: () -> Boolean): LearningEvaluation {
        val conflict = snapshot.evidence.groupBy { it.language to it.originalHash }.filterValues { rows ->
            rows.any { it.source == FeedbackSource.REJECTED || it.conflicted } || rows.map { it.expectedHash }.distinct().size > 1
        }.keys
        val rows = snapshot.examples.filter { it.holdout && it.source != FeedbackSource.REJECTED && (it.language to it.originalHash) !in conflict }
        var evaluated = 0; var unavailable = 0; var missing = 0; var baseline = 0; var learned = 0
        var identities = 0; var preserved = 0; var learnedPreserved = 0; var policy = 0
        var improvements = 0; var regressions = 0; var stopped = false
        for (row in rows) {
            if (cancelled()) { stopped = true; break }
            val original = checkNotNull(row.original); val expected = checkNotNull(row.expected)
            val generation = generate(original, row.language)
            if (cancelled() || generation.completion == CandidateCompletion.CANCELLED) { stopped = true; break }
            if (generation.completion !in setOf(CandidateCompletion.COMPLETE, CandidateCompletion.VALID_WORD, CandidateCompletion.PROTECTED)) { unavailable++; continue }
            evaluated++
            val alternatives = generation.alternatives
            val baselineOrder = rerank(baselinePolicy, original, row.language, alternatives)
            val base = baselineOrder.firstOrNull()?.text ?: original
            val reordered = rerank(learnedPolicy, original, row.language, alternatives)
            val personalized = reordered.firstOrNull()?.text ?: original
            fun same(value: String) = LearningModel.normalize(value) == expected
            val baseCorrect = same(base)
            val learnedCorrect = same(personalized)
            if (baseCorrect) baseline++
            if (learnedCorrect) learned++
            if (!baseCorrect && learnedCorrect) improvements++
            if (baseCorrect && !learnedCorrect) regressions++
            if (expected != original && alternatives.none { same(it.text) }) missing++
            if (expected == original) { identities++; if (same(base)) preserved++; if (same(personalized)) learnedPreserved++ }
            val policyWord = LocalCorrectionPolicy.decide(generation, row.language)?.canonicalKey ?: original
            if (same(policyWord)) policy++
        }
        val decision = promotionDecision(evaluated, evaluated - identities, identities, baseline,
            learned, preserved, learnedPreserved, improvements, regressions, unavailable, stopped,
            learnedPolicy != baselinePolicy)
        return LearningEvaluation(rows.size, evaluated, unavailable, missing, baseline, learned,
            identities, preserved, learnedPreserved, policy, improvements, regressions, stopped, decision)
    }

    fun completePolicyEvidence(evaluation: LearningEvaluation): Boolean =
        !evaluation.cancelled && evaluation.unavailable == 0 &&
            evaluation.evaluated >= MINIMUM_HOLDOUT &&
            evaluation.evaluated - evaluation.identities >= MINIMUM_CORRECTIONS &&
            evaluation.identities >= MINIMUM_IDENTITIES

    fun rollbackQualified(evaluation: LearningEvaluation): Boolean =
        completePolicyEvidence(evaluation) && evaluation.promotion.rollbackRequired

    internal fun promotionDecision(
        evaluated: Int,
        correctionRows: Int,
        identities: Int,
        baselineTop: Int,
        learnedTop: Int,
        baselinePreserved: Int,
        learnedPreserved: Int,
        improvements: Int,
        regressions: Int,
        unavailable: Int,
        cancelled: Boolean,
        candidateChanged: Boolean,
    ): LearningPromotionDecision {
        val reasons = ArrayList<String>()
        if (cancelled) reasons += "CANCELLED"
        if (!candidateChanged) reasons += "CANDIDATE_UNCHANGED"
        if (evaluated < MINIMUM_HOLDOUT || correctionRows < MINIMUM_CORRECTIONS ||
            identities < MINIMUM_IDENTITIES) reasons += "INSUFFICIENT_HOLDOUT"
        if (unavailable != 0) reasons += "INCOMPLETE_EVALUATION"
        if (regressions != 0) reasons += "NEW_REGRESSION"
        if (learnedPreserved < baselinePreserved) reasons += "IDENTITY_REGRESSION"
        if (improvements == 0 || learnedTop <= baselineTop) reasons += "NO_NET_IMPROVEMENT"
        return LearningPromotionDecision(
            promotionApproved = reasons.isEmpty(),
            rollbackRequired = regressions != 0 || learnedPreserved < baselinePreserved || learnedTop < baselineTop,
            reasons = reasons,
        )
    }

    const val MINIMUM_HOLDOUT = 20
    const val MINIMUM_CORRECTIONS = 10
    const val MINIMUM_IDENTITIES = 5
}
