package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

/** Legacy-first frozen cascade: a retrained model runs only when the qualified v1 abstains. */
internal object CompactAutoCorrectionPolicy {
    const val VERSION = 4
    const val POLICY_SHA256 = "5057e9e955fafdc507e06b4b1e88307b4dd2201d6864a9620b39e23358a33acd"
    const val LEGACY_MINIMUM_SCORE = 0.2962572457107321
    const val LEGACY_MINIMUM_MARGIN = 0.42795266413380256
    const val RETRAINED_MINIMUM_SCORE = 0.24258020149114667
    const val RETRAINED_MINIMUM_MARGIN = 0.45231463979111636

    fun select(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): GeneratedCandidate? {
        if (language != KeyboardLanguage.RUSSIAN || !models.learnedReady ||
            !models.legacyAutomaticReady || !models.contextReady ||
            generation.original == null || generation.isValidWord || generation.protectedReason != null ||
            generation.localSearch.completion != CandidateCompletion.COMPLETE ||
            generation.compactAlternatives.isEmpty() || generation.compactAlternatives.size > 64 ||
            LocalCorrectionPolicy.decide(generation, language) != null) return null
        return selectStage(models, context, generation, true, LEGACY_MINIMUM_SCORE,
            LEGACY_MINIMUM_MARGIN) ?: selectStage(models, context, generation, false,
            RETRAINED_MINIMUM_SCORE, RETRAINED_MINIMUM_MARGIN)
    }

    internal fun hasUnresolvedRussianEEhRival(selected: String, keys: List<String>): Boolean {
        for (right in keys) {
            if (selected == right) continue
            val left = selected
            if (left.length != right.length) continue
            var differences = 0
            var confusable = false
            for (index in left.indices) if (left[index] != right[index]) {
                differences++
                confusable = (left[index] == 'е' && right[index] == 'э') ||
                    (left[index] == 'э' && right[index] == 'е')
                if (differences > 1) break
            }
            if (differences == 1 && confusable) return true
        }
        return false
    }

    private fun selectStage(models: ExperimentModels, context: String, generation: CandidateGeneration,
        legacy: Boolean, minimumScore: Double, minimumMargin: Double): GeneratedCandidate? {
        val originalText = generation.original ?: return null
        val alternatives = generation.compactAlternatives
        if (alternatives.size < 2 && generation.completion != CandidateCompletion.COMPLETE) return null
        val scores = alternatives.map { models.compactScore(context, originalText, it, legacy) }
        if (scores.any { !it.isFinite() }) return null
        val order = scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { it })
        val top = order.first()
        val original = models.compactOriginalScore(context, originalText, KeyboardLanguage.RUSSIAN, legacy)
        if (!original.isFinite()) return null
        val second = order.getOrNull(1)?.let(scores::get) ?: Double.NEGATIVE_INFINITY
        val margin = scores[top] - maxOf(original, second)
        val selected = alternatives[top]
        return selected.takeIf { scores[top] >= minimumScore && margin >= minimumMargin &&
            !hasUnresolvedRussianEEhRival(selected.terminalKey, alternatives.map { it.terminalKey }) }
    }
}
