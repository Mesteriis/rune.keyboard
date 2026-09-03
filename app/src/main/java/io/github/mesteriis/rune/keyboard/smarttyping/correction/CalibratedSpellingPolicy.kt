package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration

/** Numeric evidence only. Calibration is not authorization to write an automatic correction. */
data class CalibratedRanking(val candidateIds: List<Int>, val preferredId: Int, val usedModel: Boolean)

data class SpellingCoefficients(
    val weights: RankingWeights,
    val thresholds: RankingThresholds,
    val modelWeight: Int = 0,
) {
    init { require(modelWeight in listOf(0, 1, 2, 4, 8)) }
}

/**
 * Four-candidate calibration from 2026-09-03-combined-calibration. Until final holdout
 * qualification these coefficients affect suggestions only. No model request or editor access.
 */
object CalibratedSpellingPolicy {
    const val MAXIMUM_ALTERNATIVES = 3

    fun coefficients(language: KeyboardLanguage, model: Boolean): SpellingCoefficients = when (language) {
        KeyboardLanguage.ENGLISH -> if (model) EN_MODEL else EN_DETERMINISTIC
        KeyboardLanguage.RUSSIAN -> if (model) RU_MODEL else RU_DETERMINISTIC
        KeyboardLanguage.SPANISH -> if (model) ES_MODEL else ES_DETERMINISTIC
    }

    fun rank(generation: CandidateGeneration, language: KeyboardLanguage,
        scores: List<RankingModelScore>? = null): CalibratedRanking? {
        val model = coefficients(language, true)
        val combined = scores?.let { CandidateRanker.rank(generation, model.weights, model.modelWeight, it) }
        val selected = if (combined != null) model else coefficients(language, false)
        val ordered = combined ?: CandidateRanker.rank(generation, selected.weights) ?: return null
        // Larger returned sets may show ordering, but have no preferred calibration candidate.
        val preferred = if (generation.alternatives.size > MAXIMUM_ALTERNATIVES) 0 else
            CandidateRanker.choose(CandidateRanker.proposal(generation, ordered), selected.thresholds)
        return CalibratedRanking(ordered.map { it.candidateId }, preferred, combined != null)
    }

    private val EN_DETERMINISTIC = SpellingCoefficients(RankingWeights(4, 1, 2, 4, 1), RankingThresholds(48, 8, 1))
    private val RU_DETERMINISTIC = SpellingCoefficients(RankingWeights(4, 1, 2, 0, 0), RankingThresholds(40, 8, 5))
    private val ES_DETERMINISTIC = SpellingCoefficients(RankingWeights(2, 0, 2, 4, 0), RankingThresholds(16, 4, 5))
    private val EN_MODEL = SpellingCoefficients(RankingWeights(4, 1, 2, 4, 0), RankingThresholds(40, 8, 1), 1)
    private val RU_MODEL = SpellingCoefficients(RankingWeights(4, 1, 2, 0, 0), RankingThresholds(40, 8, 5), 1)
    private val ES_MODEL = SpellingCoefficients(RankingWeights(2, 1, 2, 0, 0), RankingThresholds(20, 2, 5), 1)
}
