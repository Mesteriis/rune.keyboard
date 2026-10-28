package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration

data class LocalCorrectionDecision(val canonicalKey: String)

/** Pure numeric policy over the complete distance-one neighborhood. */
object LocalCorrectionPolicy {
    const val VERSION = 1

    fun decide(generation: CandidateGeneration, language: KeyboardLanguage): LocalCorrectionDecision? {
        val original = generation.original ?: return null
        val evidence = generation.localSearch
        val casePattern = CasePattern.analyze(original)
        val supportedCase = casePattern == CasePattern.LOWER ||
            (casePattern == CasePattern.TITLE && language == KeyboardLanguage.RUSSIAN)
        if (evidence.completion != CandidateCompletion.COMPLETE || generation.isValidWord ||
            generation.protectedReason != null || original.codePointCount(0, original.length) < 5 ||
            !supportedCase ||
            evidence.alternatives.isEmpty()) return null
        val snapshot = generation.copy(alternatives = evidence.alternatives,
            completion = CandidateCompletion.COMPLETE)
        val coefficients = coefficients(language) ?: return null
        val proposal = CandidateRanker.proposeLocal(snapshot, coefficients.weights) ?: return null
        val selected = CandidateRanker.choose(proposal, coefficients.thresholds)
        val winner = evidence.alternatives.getOrNull(selected - 1) ?: return null
        if (winner.language != language || winner.isFallback) return null
        return LocalCorrectionDecision(winner.canonicalKey)
    }

    fun coefficients(language: KeyboardLanguage): SpellingCoefficients? = when (language) {
        // Kept available for suggestion/replay experiments; release qualification remains false.
        KeyboardLanguage.ENGLISH -> SpellingCoefficients(
            RankingWeights(4, 1, 2, 4, 1), RankingThresholds(48, 8, 5))
        KeyboardLanguage.RUSSIAN -> SpellingCoefficients(
            RankingWeights(2, 2, 0, 0, 0), RankingThresholds(64, 24, 7))
        KeyboardLanguage.SPANISH -> SpellingCoefficients(
            RankingWeights(2, 1, 2, 4, 0), RankingThresholds(38, 13, 7))
    }
}
