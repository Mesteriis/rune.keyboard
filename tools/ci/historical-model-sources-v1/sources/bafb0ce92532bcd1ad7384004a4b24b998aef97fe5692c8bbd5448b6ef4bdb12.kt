package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration

/** Calibration grid coefficients. These numeric values do not carry holdout authorization. */
data class RankingWeights(val edit: Int, val frequency: Int, val repetition: Int, val fallback: Int, val length: Int) {
    init {
        require(edit in listOf(2, 4, 8) && frequency in 0..2 && repetition in listOf(0, 2) &&
            fallback in listOf(0, 4) && length in 0..1)
    }
}

data class RankingThresholds(val originalPenalty: Int, val minimumMargin: Int, val minimumLength: Int) {
    init {
        require(originalPenalty in 0..64 && minimumMargin in 1..64 && minimumLength in 1..32)
    }
}

/** Request-local raw evidence; IDs must cover original0 and every current alternative exactly once. */
data class RankingModelScore(val candidateId: Int, val sumLogProbability: Double, val tokenCount: Int)

data class RankedCandidate(val candidateId: Int, val penalty: Double) {
    init { require(candidateId in 1..64 && penalty.isFinite()) }
}

/** Numeric proposal only. The owner still requires quality, input-policy, mode and revision gates. */
data class RankingProposal(val candidateId: Int, val penalty: Double, val runnerUpPenalty: Double?, val tokenLength: Int) {
    init {
        require(candidateId in 1..64 && penalty.isFinite() && tokenLength in 1..32 &&
            (runnerUpPenalty == null || runnerUpPenalty.isFinite() && runnerUpPenalty >= penalty))
    }
}

/** Pure bounded ranking, no editor, model execution, payload retention or qualification state. */
object CandidateRanker {
    fun propose(generation: CandidateGeneration, weights: RankingWeights, modelWeight: Int = 0,
        modelScores: List<RankingModelScore>? = null): RankingProposal? {
        if (generation.prohibitsAutoReplace) return null
        val ranked = rank(generation, weights, modelWeight, modelScores) ?: return null
        return proposal(generation, ranked)
    }

    fun proposeLocal(generation: CandidateGeneration, weights: RankingWeights): RankingProposal? {
        if (generation.prohibitsAutoReplace) return null
        val ranked = rankInternal(generation, weights, 0, null, 64) ?: return null
        return proposal(generation, ranked)
    }

    /** Partial searches may order suggestions, but can never produce an automatic proposal. */
    fun rank(generation: CandidateGeneration, weights: RankingWeights, modelWeight: Int = 0,
        modelScores: List<RankingModelScore>? = null): List<RankedCandidate>? =
        rankInternal(generation, weights, modelWeight, modelScores, 7)

    private fun rankInternal(generation: CandidateGeneration, weights: RankingWeights, modelWeight: Int,
        modelScores: List<RankingModelScore>?, maximumCandidates: Int): List<RankedCandidate>? {
        require(modelWeight in listOf(0, 1, 2, 4, 8))
        if (generation.alternatives.isEmpty()) return null
        val original = generation.original ?: return null
        val tokenLength = original.codePointCount(0, original.length)
        if (tokenLength !in 1..32) return null
        val count = generation.alternatives.size
        if (count !in 1..maximumCandidates) return null
        val means = DoubleArray(count + 1)
        if (modelWeight != 0) {
            if (modelScores == null || modelScores.size != means.size) return null
            val seen = BooleanArray(means.size)
            for (score in modelScores) {
                if (score.candidateId !in means.indices || seen[score.candidateId] ||
                    !score.sumLogProbability.isFinite() || score.sumLogProbability > 0 || score.tokenCount !in 1..256) return null
                seen[score.candidateId] = true
                means[score.candidateId] = score.sumLogProbability / score.tokenCount
            }
        }
        val ranked = ArrayList<RankedCandidate>(count)
        for ((index, candidate) in generation.alternatives.withIndex()) {
            val quarters = candidate.editFeatures.editCost * 4
            if (!quarters.isFinite() || quarters !in 0.0..256.0 || quarters != quarters.toInt().toDouble() ||
                candidate.frequencyRank <= 0 || candidate.editFeatures.repeatedCharacterEdits !in 0..32 ||
                candidate.lengthDifference !in 0..32) return null
            val frequencyBand = 32 - Integer.numberOfLeadingZeros(candidate.frequencyRank - 1)
            val deterministic = quarters.toInt() * weights.edit + frequencyBand * weights.frequency -
                candidate.editFeatures.repeatedCharacterEdits * weights.repetition +
                (if (candidate.isFallback) weights.fallback else 0) + candidate.lengthDifference * weights.length
            // Preserve the Python operation order. Original's normalized score is the reference;
            // thresholds supply its independent OOV penalty. Nonfinite evidence fails closed.
            val penalty = deterministic - modelWeight * (means[index + 1] - means[0])
            if (!penalty.isFinite()) return null
            ranked.add(RankedCandidate(index + 1, penalty))
        }
        return ranked.sortedWith(compareBy<RankedCandidate> { it.penalty }.thenBy { it.candidateId })
    }

    internal fun proposal(generation: CandidateGeneration, ranked: List<RankedCandidate>): RankingProposal? {
        if (generation.prohibitsAutoReplace || ranked.isEmpty()) return null
        val original = generation.original ?: return null
        return RankingProposal(ranked.first().candidateId, ranked.first().penalty,
            ranked.getOrNull(1)?.penalty, original.codePointCount(0, original.length))
    }

    /** Original0 when either margin or minimum length is insufficient. No editor mutation. */
    fun choose(proposal: RankingProposal?, thresholds: RankingThresholds?): Int {
        if (proposal == null || thresholds == null || proposal.tokenLength < thresholds.minimumLength) return 0
        val rival = minOf(thresholds.originalPenalty.toDouble(), proposal.runnerUpPenalty ?: Double.POSITIVE_INFINITY)
        return if (rival - proposal.penalty >= thresholds.minimumMargin) proposal.candidateId else 0
    }
}
