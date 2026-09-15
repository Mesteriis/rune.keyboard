package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.tanh

/** Opt-in manual-ranking adjustments only. This type never admits automatic edits. */
class ExperimentModels internal constructor() {
    @Volatile private var ranker: ObliviousTreeRanker? = null
    @Volatile private var neural: CompactCharacterModel? = null
    @Volatile private var tapModel: CompactCharacterModel? = null
    val learnedReady: Boolean get() = ranker != null
    val contextReady: Boolean get() = neural != null
    val tapReady: Boolean get() = tapModel != null

    fun supports(language: KeyboardLanguage): Boolean = language == KeyboardLanguage.RUSSIAN

    fun rankScore(
        context: String,
        original: String,
        candidate: GeneratedCandidate,
        personalBonus: Double = 0.0,
        touchBonus: Double = 0.0,
    ): Double {
        val weights = ranker ?: return 0.0
        if (!supports(candidate.language) || original.length !in 1..128 || candidate.text.length !in 1..128) return 0.0
        val features = rankFeatures(context, original, candidate.text, candidate.unitDistance,
            candidate.frequencyRank, candidate.editFeatures.editCost.toDouble(), candidate.isFallback)
        val score = weights.score(features)
        return 0.8 * tanh(score / 4.0) + boundedBonus(personalBonus) + boundedBonus(touchBonus)
    }

    fun contextScore(context: String, candidate: String, language: KeyboardLanguage): Double {
        val model = neural ?: return 0.0
        if (!supports(language) || candidate.isEmpty() || candidate.length > 128) return 0.0
        var history = context.takeLast(RANKING_WINDOW).lowercase(Locale.ROOT)
        if (history.isNotEmpty() && !history.last().isWhitespace()) history += " "
        var total = 0.0
        val word = candidate.take(32).lowercase(Locale.ROOT) + " "
        for (letter in word) {
            val probability = model.probabilities(history)[characterId(letter)]
            total += ln(probability.coerceAtLeast(1e-9))
            history = (history + letter).takeLast(RANKING_WINDOW)
        }
        return ((total / word.length + 3.0) * 0.25).coerceIn(-0.5, 0.5)
    }

    /** Conditional probabilities over Russian letters, excluding the space class. */
    fun nextLetters(context: String, prefix: String, language: KeyboardLanguage): Map<Char, Double> {
        val model = tapModel ?: return emptyMap()
        if (!supports(language) || prefix.length > 128) return emptyMap()
        val history = context.takeLast(WINDOW).lowercase(Locale.ROOT).let {
            if (it.isNotEmpty() && !it.last().isWhitespace()) "$it " else it
        } + prefix.takeLast(WINDOW).lowercase(Locale.ROOT)
        val probabilities = model.probabilities(history)
        val letterTotal = probabilities.drop(1).sum()
        if (!letterTotal.isFinite() || letterTotal <= 0.0) return emptyMap()
        return (1 until ALPHABET.length).associate { ALPHABET[it] to probabilities[it] / letterTotal }
    }

    /** Invalid or missing assets leave their independent experiment unavailable. Off-thread caller. */
    internal fun loadRanker(bytes: ByteArray) {
        ranker = ObliviousTreeRanker.decode(bytes)
    }

    internal fun loadContext(bytes: ByteArray) {
        neural = decode(bytes, "REC2", RANKING_CONTEXT_FLOATS, intArrayOf(RANKING_WINDOW, RANKING_HIDDEN, ALPHABET.length))
            ?.let { CompactCharacterModel(it, RANKING_WINDOW, RANKING_HIDDEN) }
    }

    internal fun loadTapContext(bytes: ByteArray) {
        tapModel = decode(bytes, "REC1", CONTEXT_FLOATS, intArrayOf(WINDOW, HIDDEN, ALPHABET.length))
            ?.let { CompactCharacterModel(it, WINDOW, HIDDEN) }
    }

    companion object {
        internal const val ALPHABET = " абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        internal const val WINDOW = 24
        internal const val HIDDEN = 24
        internal const val RANK_FLOATS = RankFeatures.COUNT
        internal const val RANKING_WINDOW = 48
        internal const val RANKING_HIDDEN = 48
        internal const val RANKING_CONTEXT_FLOATS = RANKING_WINDOW * ALPHABET.length * RANKING_HIDDEN + RANKING_HIDDEN + RANKING_HIDDEN * ALPHABET.length + ALPHABET.length
        internal const val CONTEXT_FLOATS = WINDOW * ALPHABET.length * HIDDEN + HIDDEN + HIDDEN * ALPHABET.length + ALPHABET.length

        private fun boundedBonus(value: Double) = if (value.isFinite()) value.coerceIn(-0.2, 0.2) else 0.0
        internal fun characterId(c: Char): Int = ALPHABET.indexOf(c).coerceAtLeast(0)

        internal fun rankFeatures(context: String, original: String, candidate: String,
            distance: Int, frequency: Int, editCost: Double, fallback: Boolean): DoubleArray {
            return RankFeatures.extract(context, original, candidate, distance, frequency, editCost, fallback)
        }

        /** Fixed dimensions reject truncation, extra bytes, non-finite and oversized weights. */
        private fun decode(bytes: ByteArray, magic: String, count: Int, dimensions: IntArray): FloatArray? {
            if (bytes.size != 4 + dimensions.size * 4 + count * 4) return null
            val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            if (magic.any { buffer.get().toInt() != it.code }) return null
            if (dimensions.any { buffer.int != it }) return null
            val weights = FloatArray(count) { buffer.float }
            if (weights.any { !it.isFinite() || abs(it) > 32f }) return null
            return weights
        }
    }

    private class CompactCharacterModel(private val weights: FloatArray, private val window: Int, private val hiddenSize: Int) {
        fun probabilities(context: String): DoubleArray {
            val history = context.takeLast(window)
            val hiddenOffset = window * ALPHABET.length * hiddenSize
            val outputOffset = hiddenOffset + hiddenSize
            val biasOffset = outputOffset + hiddenSize * ALPHABET.length
            val hidden = DoubleArray(hiddenSize) { weights[hiddenOffset + it].toDouble() }
            for (position in 0 until window) {
                val index = position - (window - history.length)
                val id = if (index < 0) 0 else characterId(history[index])
                val offset = (position * ALPHABET.length + id) * hiddenSize
                for (j in hidden.indices) hidden[j] += weights[offset + j]
            }
            for (j in hidden.indices) hidden[j] = tanh(hidden[j])
            val result = DoubleArray(ALPHABET.length) { weights[biasOffset + it].toDouble() }
            for (j in hidden.indices) for (k in result.indices) {
                result[k] += hidden[j] * weights[outputOffset + j * ALPHABET.length + k]
            }
            val max = result.max()
            var total = 0.0
            for (k in result.indices) { result[k] = exp(result[k] - max); total += result[k] }
            for (k in result.indices) result[k] /= total
            return result
        }
    }
}
