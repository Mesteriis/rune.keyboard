package io.github.mesteriis.rune.keyboard.smarttyping.touch

import kotlin.math.abs
import kotlin.math.ln

/** Experimental conservative heuristic; constants are safeguards, not measured quality claims. */
object DynamicTouchResolver {
    private const val CENTRE = 0.25
    private const val NEARBY = 0.75
    private const val MIN_PROBABILITY = 0.6
    private const val MIN_RATIO = 3.0
    private const val PRIOR_WEIGHT = 0.12
    private const val MAX_PRIOR_ADVANTAGE = 0.30
    private const val SCORE_MARGIN = 0.08

    fun propose(sample: PhysicalTouchSample, probabilities: Map<Char, Double>): Char {
        val original = sample.observedKey
        if (!sample.profile.valid() || sample.profile.language != "RUSSIAN" || !russian(original) ||
            sample.offsets.size !in 1..TouchCalibrationModel.MAX_NEIGHBOURS ||
            sample.offsets.map { it.key }.distinct().size != sample.offsets.size ||
            sample.offsets.any { !russian(it.key) || !it.x.isFinite() || !it.y.isFinite() } ||
            probabilities.size !in 1..33 || probabilities.any { !russian(it.key) || !it.value.isFinite() || it.value !in 0.0..1.0 }) return original
        val source = sample.offsets.singleOrNull { it.key == original } ?: return original
        if (abs(source.x) > 0.5 || abs(source.y) > 0.5 ||
            abs(source.x) <= CENTRE && abs(source.y) <= CENTRE) return original
        val originalProbability = probabilities[original] ?: 0.0
        val sourceDistance = source.x * source.x + source.y * source.y
        var best = original
        var bestMargin = SCORE_MARGIN
        // Stable iteration makes exact ties independent of the supplied layout/list ordering.
        for (candidate in sample.offsets.sortedBy { it.key }) {
            if (candidate.key == original || abs(candidate.x) > NEARBY || abs(candidate.y) > NEARBY) continue
            val probability = probabilities[candidate.key] ?: continue
            if (probability < MIN_PROBABILITY || probability < originalProbability * MIN_RATIO) continue
            val ratio = probability / originalProbability.coerceAtLeast(1e-6)
            val prior = (PRIOR_WEIGHT * ln(ratio)).coerceAtMost(MAX_PRIOR_ADVANTAGE)
            val margin = sourceDistance - candidate.x * candidate.x - candidate.y * candidate.y + prior
            if (margin > bestMargin) {
                bestMargin = margin
                best = candidate.key
            }
        }
        return best
    }

    private fun russian(key: Char): Boolean = key in 'а'..'я' || key == 'ё'
}
