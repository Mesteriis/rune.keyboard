package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import kotlin.math.tanh

/** Frozen unified model: character context is an input feature, never an added score bonus. */
internal class ContextualRanker private constructor(
    private val weights: ObliviousTreeRanker,
    private val wiki: WordPairFeatures,
    private val conversation: WordPairFeatures,
    private val grammar: GrammaticalContextFeatures,
    private val revisionScope: InfinitiveRevisionScope,
) {
    /** Share validated immutable feature indices; only the numeric weights differ. */
    fun withWeights(bytes: ByteArray): ContextualRanker? =
        ObliviousTreeRanker.decode(bytes, FEATURES)?.let {
            ContextualRanker(it, wiki, conversation, grammar, revisionScope)
        }

    fun allowsInfinitiveRevision(context: String, previous: String, proposed: String,
        morphology: MorphologyLexicon): Boolean = revisionScope.refusal(context, previous, proposed, morphology) == null

    fun score(models: ExperimentModels, context: String, original: String, candidate: GeneratedCandidate): Double {
        if (candidate.language != KeyboardLanguage.RUSSIAN) return Double.NaN
        return score(models, context, original, candidate.text, candidate.unitDistance,
            candidate.frequencyRank, candidate.editFeatures.editCost.toDouble(), candidate.isFallback)
    }

    fun originalScore(models: ExperimentModels, context: String, original: String): Double =
        score(models, context, original, original, 0, Int.MAX_VALUE, 0.0, false)

    private fun score(models: ExperimentModels, context: String, original: String, word: String,
        distance: Int, frequency: Int, editCost: Double, fallback: Boolean): Double {
        if (!models.contextReady || original.length !in 1..128 || word.length !in 1..128) return Double.NaN
        val features = ExperimentModels.rankFeatures(context, original, word, distance, frequency, editCost, fallback) +
            wiki.extract(context, original, word) + conversation.extract(context, original, word) +
            doubleArrayOf(models.contextScore(context, word, KeyboardLanguage.RUSSIAN)) + grammar.extract(context, word)
        return 0.8 * tanh(weights.score(features) / 4.0)
    }

    companion object {
        const val FEATURES = RankFeatures.COUNT + 6 + 6 + 1 + GrammaticalContextFeatures.COUNT
        fun create(bytes: ByteArray, wiki: WordPairFeatures, conversation: WordPairFeatures,
            dictionary: GrammarFeatureDictionary): ContextualRanker? =
            ObliviousTreeRanker.decode(bytes, FEATURES)?.let {
                ContextualRanker(it, wiki, conversation, GrammaticalContextFeatures(dictionary),
                    InfinitiveRevisionScope(dictionary))
            }
    }
}
