package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

/**
 * Calibration-selected total-score margins; release qualification is separate.
 * Request ownership and explicit editor selection stay with the caller.
 */
object ContextualPunctuationPolicy {
    data class Score(val candidateId: Int, val sumLogProbability: Double, val tokenCount: Int)

    fun choose(expectedCandidateIds: List<Int>, scores: List<Score>): Int? {
        if (expectedCandidateIds.size !in 2..8 || 0 !in expectedCandidateIds ||
            expectedCandidateIds.any { it < 0 } ||
            expectedCandidateIds.distinct().size != expectedCandidateIds.size ||
            scores.size != expectedCandidateIds.size ||
            scores.any { !it.sumLogProbability.isFinite() || it.sumLogProbability > 0 || it.tokenCount !in 1..255 } ||
            scores.map { it.candidateId }.toSet() != expectedCandidateIds.toSet()) return null

        val original = scores.single { it.candidateId == 0 }.sumLogProbability
        val punctuation = scores.filter { it.candidateId != 0 }.sortedWith(
            compareByDescending<Score> { it.sumLogProbability }.thenBy { it.candidateId })
        val winner = punctuation.first()
        val rival = punctuation.getOrNull(1) ?: return null
        // Alternative complete continuations have different lengths: compare sums, never token averages.
        if (winner.sumLogProbability - original <= MINIMUM_ORIGINAL_ADVANTAGE ||
            winner.sumLogProbability - rival.sumLogProbability < MINIMUM_RIVAL_ADVANTAGE) return null
        return winner.candidateId
    }

    private const val MINIMUM_ORIGINAL_ADVANTAGE = 0.5
    private const val MINIMUM_RIVAL_ADVANTAGE = 4.0
}
