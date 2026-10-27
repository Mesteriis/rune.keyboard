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
    private val nounCaseScope: NounCaseRevisionScope,
) {
    /** Share validated immutable feature indices; only the numeric weights differ. */
    fun withWeights(bytes: ByteArray): ContextualRanker? =
        ObliviousTreeRanker.decode(bytes, FEATURES)?.let {
            ContextualRanker(it, wiki, conversation, grammar, revisionScope, nounCaseScope)
        }

    fun allowsInfinitiveRevision(context: String, previous: String, proposed: String,
        morphology: MorphologyLexicon): Boolean = revisionScope.refusal(context, previous, proposed, morphology) == null

    fun revisionPrecondition(context: String, previous: String, morphology: MorphologyLexicon) =
        revisionScope.preconditionRefusal(context, previous, morphology)
    fun revisionRefusal(context: String, previous: String, proposed: String, morphology: MorphologyLexicon) =
        revisionScope.refusal(context, previous, proposed, morphology)

    fun nounCasePrecondition(context: String, previous: String, morphology: MorphologyLexicon) =
        nounCaseScope.preconditionRefusal(context, previous, morphology)
    fun nounCaseRefusal(context: String, previous: String, proposed: String, morphology: MorphologyLexicon) =
        nounCaseScope.refusal(context, previous, proposed, morphology)

    fun score(models: ExperimentModels, context: String, original: String, candidate: GeneratedCandidate): Double {
        if (candidate.language != KeyboardLanguage.RUSSIAN) return Double.NaN
        return score(models, context, original, candidate.text, candidate.unitDistance,
            candidate.frequencyRank, candidate.editFeatures.editCost.toDouble(), candidate.isFallback)
    }

    fun originalScore(models: ExperimentModels, context: String, original: String): Double =
        score(models, context, original, original, 0, Int.MAX_VALUE, 0.0, false)

    /** Reuse the exact installed feature indices without applying its numeric weights. */
    fun candidateFeatures(models: ExperimentModels, context: String, original: String,
        candidate: GeneratedCandidate): DoubleArray? =
        if (candidate.language != KeyboardLanguage.RUSSIAN) null else features(models, context, original,
            candidate.text, candidate.unitDistance, candidate.frequencyRank,
            candidate.editFeatures.editCost.toDouble(), candidate.isFallback)

    fun originalFeatures(models: ExperimentModels, context: String, original: String): DoubleArray? =
        features(models, context, original, original, 0, Int.MAX_VALUE, 0.0, false)

    private fun score(models: ExperimentModels, context: String, original: String, word: String,
        distance: Int, frequency: Int, editCost: Double, fallback: Boolean): Double {
        val values = features(models, context, original, word, distance, frequency, editCost, fallback) ?: return Double.NaN
        return 0.8 * tanh(weights.score(values) / 4.0)
    }

    private fun features(models: ExperimentModels, context: String, original: String, word: String,
        distance: Int, frequency: Int, editCost: Double, fallback: Boolean): DoubleArray? {
        if (!models.contextReady || original.length !in 1..128 || word.length !in 1..128) return null
        val values = ExperimentModels.rankFeatures(context, original, word, distance, frequency, editCost, fallback) +
            wiki.extract(context, original, word) + conversation.extract(context, original, word) +
            doubleArrayOf(models.contextScore(context, word, KeyboardLanguage.RUSSIAN)) + grammar.extract(context, word)
        return values.takeIf { it.size == FEATURES && it.all(Double::isFinite) }
    }

    companion object {
        const val FEATURES = RankFeatures.COUNT + 6 + 6 + 1 + GrammaticalContextFeatures.COUNT
        fun create(bytes: ByteArray, wiki: WordPairFeatures, conversation: WordPairFeatures,
            dictionary: GrammarFeatureDictionary): ContextualRanker? =
            ObliviousTreeRanker.decode(bytes, FEATURES)?.let {
                ContextualRanker(it, wiki, conversation, GrammaticalContextFeatures(dictionary),
                    InfinitiveRevisionScope(dictionary), NounCaseRevisionScope(dictionary))
            }
    }
}
