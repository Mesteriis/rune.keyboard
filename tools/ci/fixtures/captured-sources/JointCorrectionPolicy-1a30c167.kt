package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryThresholds
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

/** A decided null candidate retains the original; a null choice leaves the baseline untouched. */
data class JointCorrectionChoice(val candidate: GeneratedCandidate?, val rescue: Boolean = false, val wordContext: Boolean = false, val contextual: Boolean = false, val grammarRevision: Boolean = false, val nounCaseRevision: Boolean = false)

enum class JointCorrectionRefusal {
    NOT_QUALIFIED, RESULT_NOT_READY, SEARCH_INCOMPLETE, ORIGINAL_VALID, RARE_ORIGINAL,
    PROTECTED_FORM, RESOURCE_UNAVAILABLE, NO_CANDIDATES, SCORE_TOO_LOW, INSUFFICIENT_MARGIN,
    ORIGINAL_PREFERRED, REPLACEMENT_VETOED,
    UNCHANGED, PREVIOUS_NOT_UNAMBIGUOUS_FINITE, PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE,
    LEMMA_UNAVAILABLE, DIFFERENT_LEMMA, NO_INFINITIVE_CUE,
    PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL, PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE, NO_ACCUSATIVE_CUE,
}
data class JointCorrectionEvaluation(
    val choice: JointCorrectionChoice? = null,
    val refusal: JointCorrectionRefusal? = null,
    val admissionRefusal: io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal? = null,
    val rescueAttempted: Boolean = false,
    val rescueRefusal: JointCorrectionRefusal? = null,
    val rescueAdmissionRefusal: io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal? = null,
    val contextualAttempted: Boolean = false,
    val contextualRefusal: JointCorrectionRefusal? = null,
    val contextualAdmissionRefusal: io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal? = null,
    val wordContextAttempted: Boolean = false,
    val wordContextRefusal: JointCorrectionRefusal? = null,
    val wordContextAdmissionRefusal: io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal? = null,
    val grammarRevisionAttempted: Boolean = false,
    val grammarRevisionRefusal: JointCorrectionRefusal? = null,
    val grammarRevisionAdmissionRefusal: io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal? = null,
    val nounCaseAttempted: Boolean = false,
    val nounCaseRefusal: JointCorrectionRefusal? = null,
    val nounCaseAdmissionRefusal: io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal? = null,
)

internal data class JointCorrectionThresholds(val short: RecoveryThresholds, val long: RecoveryThresholds, val retention: RecoveryThresholds = long)

/** One comparable model scores all sources and the original. No thresholds are fitted on-device. */
internal object JointCorrectionPolicy {
    const val VERSION = 1
    fun select(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, thresholds: JointCorrectionThresholds, baselineWord: String? = null): JointCorrectionChoice? =
        evaluate(models, context, generation, language, thresholds, baselineWord).choice

    fun evaluate(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, thresholds: JointCorrectionThresholds, baselineWord: String? = null): JointCorrectionEvaluation {
        fun refused(reason: JointCorrectionRefusal) = JointCorrectionEvaluation(refusal = reason)
        val original = generation.original ?: return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val pool = generation.jointSearch
        if (language != KeyboardLanguage.RUSSIAN || original.length !in 3..32 || pool.alternatives.size > 64)
            return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (generation.isValidWord) return refused(JointCorrectionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null) return refused(JointCorrectionRefusal.PROTECTED_FORM)
        if (!generation.jointEvaluated) return refused(JointCorrectionRefusal.RESULT_NOT_READY)
        if (!pool.isComplete) return refused(JointCorrectionRefusal.SEARCH_INCOMPLETE)
        if (pool.alternatives.isEmpty()) return refused(JointCorrectionRefusal.NO_CANDIDATES)
        if (!models.jointReady || !models.contextReady) return refused(JointCorrectionRefusal.RESOURCE_UNAVAILABLE)
        val scores = listOf(models.jointOriginalScore(context, original)) +
            pool.alternatives.map { models.jointScore(context, original, it) }
        val policy = if (original.length <= 4) thresholds.short else if (baselineWord != null) thresholds.retention else thresholds.long
        if (scores.any { !it.isFinite() }) return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val order = scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { it })
        if (scores[order[0]] < policy.minimumScore) return refused(JointCorrectionRefusal.SCORE_TOO_LOW)
        if (scores[order[0]] - scores[order[1]] < policy.minimumMargin)
            return refused(JointCorrectionRefusal.INSUFFICIENT_MARGIN)
        val winner = order[0]
        val selected = pool.alternatives.getOrNull(winner - 1)
        val retained = selected?.takeIf { baselineWord == null || it.text == baselineWord }
        return JointCorrectionEvaluation(JointCorrectionChoice(retained), when {
            selected == null -> JointCorrectionRefusal.ORIGINAL_PREFERRED
            retained == null -> JointCorrectionRefusal.REPLACEMENT_VETOED
            else -> null
        })
    }
}
