package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

/** A separate frozen model compares the original and the complete pool after primary abstention. */
internal object JointRescuePolicy {
    fun select(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): GeneratedCandidate? = evaluate(models, context, generation, language).choice?.candidate

    fun evaluate(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): JointCorrectionEvaluation {
        fun refused(reason: JointCorrectionRefusal) = JointCorrectionEvaluation(refusal = reason)
        val original = generation.original ?: return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (language != KeyboardLanguage.RUSSIAN || original.length !in 5..32 ||
            generation.jointSearch.alternatives.size > 64) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (generation.isValidWord) return refused(JointCorrectionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null) return refused(JointCorrectionRefusal.PROTECTED_FORM)
        if (!generation.jointEvaluated) return refused(JointCorrectionRefusal.RESULT_NOT_READY)
        if (!generation.jointSearch.isComplete) return refused(JointCorrectionRefusal.SEARCH_INCOMPLETE)
        if (generation.jointSearch.alternatives.isEmpty()) return refused(JointCorrectionRefusal.NO_CANDIDATES)
        if (!models.rescueReady || !models.contextReady) return refused(JointCorrectionRefusal.RESOURCE_UNAVAILABLE)
        val pool = generation.jointSearch.alternatives
        val scores = listOf(models.rescueOriginalScore(context, original)) +
            pool.map { models.rescueScore(context, original, it) }
        if (scores.any { !it.isFinite() }) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val order = scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { it })
        val policy = JointRescueQualification.thresholds
        if (scores[order[0]] < policy.minimumScore) return refused(JointCorrectionRefusal.SCORE_TOO_LOW)
        if (scores[order[0]] - scores[order[1]] < policy.minimumMargin)
            return refused(JointCorrectionRefusal.INSUFFICIENT_MARGIN)
        val candidate = pool.getOrNull(order[0] - 1)
            ?: return refused(JointCorrectionRefusal.ORIGINAL_PREFERRED)
        if (candidate.frequencyRank !in 1..50_000) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        return JointCorrectionEvaluation(JointCorrectionChoice(candidate, rescue = true))
    }
}
