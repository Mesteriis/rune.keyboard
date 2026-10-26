package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.correction.InfinitiveRevisionQualification
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import java.util.Locale

/** Reconsider an existing finite replacement; every refusal retains the installed result. */
internal object InfinitiveRevisionPolicy {
    const val VERSION = 1
    fun evaluate(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, baseline: JointCorrectionEvaluation, baselineWord: String?,
        morphology: MorphologyLexicon, admission: (GeneratedCandidate) -> AutomaticAdmissionRefusal?): JointCorrectionEvaluation {
        fun refused(reason: JointCorrectionRefusal) = baseline.copy(grammarRevisionAttempted = true, grammarRevisionRefusal = reason)
        val original = generation.original ?: return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (!InfinitiveRevisionQualification.enabled(language, original.length)) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (generation.isValidWord) return refused(JointCorrectionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null) return refused(JointCorrectionRefusal.PROTECTED_FORM)
        if (!models.grammarRevisionReady) return refused(JointCorrectionRefusal.RESOURCE_UNAVAILABLE)
        if (!generation.jointEvaluated) return refused(JointCorrectionRefusal.RESULT_NOT_READY)
        val pool = generation.jointSearch
        if (!pool.isComplete) return refused(JointCorrectionRefusal.SEARCH_INCOMPLETE)
        if (pool.alternatives.isEmpty()) return refused(JointCorrectionRefusal.NO_CANDIDATES)
        if (pool.alternatives.size > 64 || pool.alternatives.any { it.language != language || it.unitDistance !in 1..3 })
            return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val source = morphology.lookup(language, original.lowercase(Locale.ROOT))
        if (!source.available) return baseline.copy(grammarRevisionAttempted = true,
            grammarRevisionAdmissionRefusal = AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (source.present) return refused(JointCorrectionRefusal.ORIGINAL_VALID)
        val previous = if (baseline.choice != null) baseline.choice.candidate?.text ?: original else baselineWord ?: original
        if (previous == original) return refused(JointCorrectionRefusal.ORIGINAL_PREFERRED)
        if (pool.alternatives.none { it.text == previous }) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        models.grammarRevisionPrecondition(context, previous, morphology)?.let {
            return refused(JointCorrectionRefusal.valueOf(it.name))
        }
        val scores = listOf(models.grammarRevisionOriginalScore(context, original)) +
            pool.alternatives.map { models.grammarRevisionScore(context, original, it) }
        if (scores.any { !it.isFinite() }) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val order = scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { it })
        if (scores[order[0]] < InfinitiveRevisionQualification.MINIMUM_SCORE) return refused(JointCorrectionRefusal.SCORE_TOO_LOW)
        if (scores[order[0]] - scores[order[1]] < InfinitiveRevisionQualification.MINIMUM_MARGIN)
            return refused(JointCorrectionRefusal.INSUFFICIENT_MARGIN)
        val selected = pool.alternatives.getOrNull(order[0] - 1) ?: return refused(JointCorrectionRefusal.ORIGINAL_PREFERRED)
        models.grammarRevisionScopeRefusal(context, previous, selected.text, morphology)?.let {
            return refused(JointCorrectionRefusal.valueOf(it.name))
        }
        admission(selected)?.let { return baseline.copy(grammarRevisionAttempted = true, grammarRevisionAdmissionRefusal = it) }
        return baseline.copy(choice = JointCorrectionChoice(selected, grammarRevision = true), grammarRevisionAttempted = true)
    }
}
