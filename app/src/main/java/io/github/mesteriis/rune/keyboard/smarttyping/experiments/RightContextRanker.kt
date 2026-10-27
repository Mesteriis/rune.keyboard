package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import kotlin.math.tanh

/** Experimental numeric scoring only; no source admission, registration or editor authority. */
internal class RightContextRanker private constructor(
    private val weights: ObliviousTreeRanker,
    private val base: ContextualRanker,
    private val features: RightContextRevisionFeatures,
) {
    fun score(models: ExperimentModels, leftContext: String, original: String, rightContext: String,
        applied: String, candidate: GeneratedCandidate): Double {
        val lexical = base.candidateFeatures(models, leftContext, original, candidate) ?: return Double.NaN
        val vector = features.build(lexical, leftContext, rightContext, applied, candidate.text) ?: return Double.NaN
        return 0.8 * tanh(weights.score(vector) / 4.0)
    }

    fun originalScore(models: ExperimentModels, leftContext: String, original: String,
        rightContext: String, applied: String): Double {
        val lexical = base.originalFeatures(models, leftContext, original) ?: return Double.NaN
        val vector = features.build(lexical, leftContext, rightContext, applied, original) ?: return Double.NaN
        return 0.8 * tanh(weights.score(vector) / 4.0)
    }

    companion object {
        fun create(bytes: ByteArray, base: ContextualRanker, dictionary: GrammarFeatureDictionary,
            pastDictionary: GrammarFeatureDictionary): RightContextRanker? =
            ObliviousTreeRanker.decode(bytes, RightContextRevisionFeatures.COUNT)?.let {
                RightContextRanker(it, base, RightContextRevisionFeatures(dictionary, pastDictionary))
            }
    }
}
