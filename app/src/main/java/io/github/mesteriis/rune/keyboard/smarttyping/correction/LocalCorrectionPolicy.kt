package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration

data class LocalCorrectionDecision(val canonicalKey: String)
enum class LocalCorrectionRefusal {
    SEARCH_INCOMPLETE, ORIGINAL_VALID, PROTECTED_FORM, TOO_SHORT, NO_CANDIDATES,
    WINNER_AMBIGUOUS, INSUFFICIENT_MARGIN, NOT_QUALIFIED,
}
data class LocalCorrectionEvaluation(
    val decision: LocalCorrectionDecision? = null,
    val refusal: LocalCorrectionRefusal? = null,
)

/** Pure numeric policy over the complete distance-one neighborhood. */
object LocalCorrectionPolicy {
    const val VERSION = 1

    fun decide(generation: CandidateGeneration, language: KeyboardLanguage): LocalCorrectionDecision? =
        evaluate(generation, language).decision

    /** Mirrors the original short-circuit order and adds no new admission path. */
    fun evaluate(generation: CandidateGeneration, language: KeyboardLanguage): LocalCorrectionEvaluation {
        val original = generation.original ?: return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.NOT_QUALIFIED)
        val evidence = generation.localSearch
        val casePattern = CasePattern.analyze(original)
        val supportedCase = casePattern == CasePattern.LOWER ||
            (casePattern == CasePattern.TITLE && language == KeyboardLanguage.RUSSIAN)
        if (evidence.completion != CandidateCompletion.COMPLETE)
            return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.SEARCH_INCOMPLETE)
        if (generation.isValidWord) return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null)
            return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.PROTECTED_FORM)
        if (original.codePointCount(0, original.length) < 5)
            return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.TOO_SHORT)
        if (!supportedCase) return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.NOT_QUALIFIED)
        if (evidence.alternatives.isEmpty())
            return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.NO_CANDIDATES)
        val snapshot = generation.copy(alternatives = evidence.alternatives,
            completion = CandidateCompletion.COMPLETE)
        val coefficients = coefficients(language)
            ?: return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.NOT_QUALIFIED)
        val proposal = CandidateRanker.proposeLocal(snapshot, coefficients.weights)
            ?: return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.NOT_QUALIFIED)
        val choice = CandidateRanker.chooseWithReason(proposal, coefficients.thresholds)
        val winner = evidence.alternatives.getOrNull(choice.candidateId - 1) ?: return LocalCorrectionEvaluation(
            refusal = when (choice.refusal) {
                RankingRefusal.TOO_SHORT -> LocalCorrectionRefusal.TOO_SHORT
                RankingRefusal.WINNER_AMBIGUOUS -> LocalCorrectionRefusal.WINNER_AMBIGUOUS
                RankingRefusal.INSUFFICIENT_MARGIN -> LocalCorrectionRefusal.INSUFFICIENT_MARGIN
                else -> LocalCorrectionRefusal.NOT_QUALIFIED
            })
        if (winner.language != language || winner.isFallback)
            return LocalCorrectionEvaluation(refusal = LocalCorrectionRefusal.NOT_QUALIFIED)
        return LocalCorrectionEvaluation(decision = LocalCorrectionDecision(winner.canonicalKey))
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
