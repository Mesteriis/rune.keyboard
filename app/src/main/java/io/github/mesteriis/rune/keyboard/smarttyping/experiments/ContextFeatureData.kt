package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import kotlin.math.ln

/** Count denominators are the mass of the frozen training table, not language probabilities. */
internal class WordPairFeatures private constructor(private val index: PackedContextIndex) {
    fun extract(context: String, original: String, candidate: String): DoubleArray {
        val previous = PREVIOUS.find(context.lowercase(Locale.ROOT))?.groupValues?.get(1)
            ?: return DoubleArray(6)
        val values = lookup(previous, candidate.lowercase(Locale.ROOT)) ?: IntArray(4)
        val originalCount = lookup(previous, original.lowercase(Locale.ROOT))?.get(0) ?: 0
        return doubleArrayOf(
            (ln(1.0 + values[0]) / SCALE).coerceAtMost(1.0),
            (ln(1.0 + values[1]) / SCALE).coerceAtMost(1.0),
            values[0].toDouble() / (1.0 + values[2]),
            values[0].toDouble() / (1.0 + values[3]),
            ((ln(1.0 + values[0]) - ln(1.0 + originalCount)) / SCALE).coerceIn(-1.0, 1.0),
            if (values[0] > 0) 1.0 else 0.0,
        )
    }

    private fun lookup(previous: String, word: String): IntArray? = index.payload("$previous\u0000$word")?.let {
        val data = ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN)
        IntArray(4) { data.int }
    }

    companion object {
        private val PREVIOUS = Regex("(?:^|[\\p{javaWhitespace}\\p{Zs}\\u0085])([а-яё]{1,20})[\\p{javaWhitespace}\\p{Zs}\\u0085]*$")
        private val SCALE = ln(10001.0)
        fun open(bytes: ByteBuffer, hash: String): WordPairFeatures? = validate(bytes, hash)

        fun validate(bytes: ByteBuffer, hash: String): WordPairFeatures? =
            PackedContextIndex.validate(bytes, "RUCNTX01", hash, ::validPayload)?.let(::WordPairFeatures)

        fun openPackaged(bytes: ByteBuffer, expectedBytes: Long): WordPairFeatures? =
            PackedContextIndex.openPackaged(bytes, "RUCNTX01", expectedBytes, ::validPayload)?.let(::WordPairFeatures)

        private fun validPayload(source: ByteBuffer, offset: Int, length: Int): Boolean {
            if (length != 16) return false
            val count = source.getInt(offset)
            val documents = source.getInt(offset + 4)
            return count > 0 && documents in 1..count && source.getInt(offset + 8) >= count &&
                source.getInt(offset + 12) >= count
        }
    }
}

internal data class GrammarAnalysis(
    val pos: String?, val case: String?, val number: String?, val gender: String?, val person: String?,
    val modal: Boolean, val accusativeVerb: Boolean,
)
internal data class GrammarWord(val ambiguity: Int, val analyses: List<GrammarAnalysis>)

internal class GrammarFeatureDictionary private constructor(private val index: PackedContextIndex) {
    fun analyses(word: String): GrammarWord {
        if (!WORD.matches(word)) return ABSENT
        val payload = index.payload(word.lowercase(Locale.ROOT)) ?: return ABSENT
        val source = ByteBuffer.wrap(payload).order(ByteOrder.LITTLE_ENDIAN)
        val ambiguity = source.get().toInt() and 255
        val count = source.get().toInt() and 255
        return GrammarWord(ambiguity, List(count) { decode(source.short.toInt() and 65535) })
    }

    companion object {
        private val WORD = Regex("[а-яёА-ЯЁ]{1,32}")
        private val ABSENT = GrammarWord(0, emptyList())
        private val POS = arrayOf(null, "NOUN", "ADJF", "ADJS", "VERB", "INFN", "PRTF", "PRTS", "GRND",
            "NPRO", "ADVB", "PRED", "PREP", "NUMR", "CONJ", "PRCL", "INTJ", "COMP")
        private val CASES = arrayOf(null, "nomn", "gent", "datv", "accs", "ablt", "loct", "voct")
        private val NUMBERS = arrayOf(null, "sing", "plur")
        private val GENDERS = arrayOf(null, "masc", "femn", "neut")
        private val PERSONS = arrayOf(null, "1per", "2per", "3per")
        private fun decode(code: Int) = GrammarAnalysis(POS[code and 31], CASES[(code ushr 5) and 7],
            NUMBERS[(code ushr 8) and 3], GENDERS[(code ushr 10) and 3], PERSONS[(code ushr 12) and 3],
            code and (1 shl 14) != 0, code and (1 shl 15) != 0)

        fun open(bytes: ByteBuffer, hash: String): GrammarFeatureDictionary? = validate(bytes, hash)

        fun validate(bytes: ByteBuffer, hash: String): GrammarFeatureDictionary? =
            PackedContextIndex.validate(bytes, "RUGRM001", hash, ::validPayload)?.let(::GrammarFeatureDictionary)

        fun openPackaged(bytes: ByteBuffer, expectedBytes: Long): GrammarFeatureDictionary? =
            PackedContextIndex.openPackaged(bytes, "RUGRM001", expectedBytes, ::validPayload)?.let(::GrammarFeatureDictionary)

        private fun validPayload(source: ByteBuffer, offset: Int, length: Int): Boolean {
            if (length < 4) return false
            val ambiguity = source.get(offset).toInt() and 255
            val count = source.get(offset + 1).toInt() and 255
            return ambiguity in 1..8 && count > 0 && length == 2 + 2 * count && (0 until count).all {
                val code = source.getShort(offset + 2 + 2 * it).toInt() and 65535
                (code and 31) < POS.size && ((code ushr 8) and 3) < NUMBERS.size
            }
        }
    }
}
