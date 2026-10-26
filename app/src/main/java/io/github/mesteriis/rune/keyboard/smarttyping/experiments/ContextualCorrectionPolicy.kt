package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ContextualQualification
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

/** Apply the frozen score point to the exact existing baseline; admission remains external. */
internal object ContextualCorrectionPolicy {
    const val VERSION = 1
    fun evaluate(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, baseline: JointCorrectionEvaluation, baselineWord: String?,
        admission: (GeneratedCandidate) -> AutomaticAdmissionRefusal?): JointCorrectionEvaluation {
        fun refused(reason: JointCorrectionRefusal) = baseline.copy(contextualAttempted = true, contextualRefusal = reason)
        val original = generation.original ?: return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (!ContextualQualification.enabled(language, original.length)) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (generation.isValidWord) return refused(JointCorrectionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null) return refused(JointCorrectionRefusal.PROTECTED_FORM)
        if (!generation.jointEvaluated) return refused(JointCorrectionRefusal.RESULT_NOT_READY)
        val pool = generation.jointSearch
        if (!pool.isComplete) return refused(JointCorrectionRefusal.SEARCH_INCOMPLETE)
        if (pool.alternatives.isEmpty()) return refused(JointCorrectionRefusal.NO_CANDIDATES)
        if (pool.alternatives.size > 64 || pool.alternatives.any { it.language != language || it.unitDistance !in 1..3 })
            return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (!models.contextualReady) return refused(JointCorrectionRefusal.RESOURCE_UNAVAILABLE)
        val scores = listOf(models.contextualOriginalScore(context, original)) +
            pool.alternatives.map { models.contextualScore(context, original, it) }
        if (scores.any { !it.isFinite() }) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val order = scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { it })
        if (scores[order[0]] < ContextualQualification.MINIMUM_SCORE) return refused(JointCorrectionRefusal.SCORE_TOO_LOW)
        if (scores[order[0]] - scores[order[1]] < ContextualQualification.MINIMUM_MARGIN)
            return refused(JointCorrectionRefusal.INSUFFICIENT_MARGIN)
        val selected = pool.alternatives.getOrNull(order[0] - 1)
        if (selected != null) {
            val refusal = admission(selected)
            if (refusal != null) return baseline.copy(contextualAttempted = true, contextualAdmissionRefusal = refusal)
        }
        val previous = if (baseline.choice != null) baseline.choice.candidate?.text ?: original else baselineWord ?: original
        val retained = selected?.takeIf { previous == original || it.text == previous }
        if ((retained?.text ?: original) == previous) return baseline.copy(contextualAttempted = true,
            contextualRefusal = if (retained == null) JointCorrectionRefusal.ORIGINAL_PREFERRED else null)
        return baseline.copy(choice = JointCorrectionChoice(retained, contextual = true), contextualAttempted = true,
            contextualRefusal = when {
                selected == null -> JointCorrectionRefusal.ORIGINAL_PREFERRED
                retained == null -> JointCorrectionRefusal.REPLACEMENT_VETOED
                else -> null
            })
    }
}
