package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Exact front-coded dictionary; no hash collisions and no per-word resident objects or query cache. */
class PackedMorphologyLexicon private constructor(
    private val bytes: ByteBuffer,
    private val count: Int,
    private val blocks: Int,
    private val dataOffset: Int,
) : MorphologyLexicon {
    override fun lookup(language: KeyboardLanguage, key: String): MorphologyMembership {
        if (language != KeyboardLanguage.RUSSIAN || key.isEmpty() || !TokenUnicode.bounded(key))
            return MorphologyMembership.UNAVAILABLE
        val query = try {
            TokenUnicode.folded(key).toByteArray(Charsets.UTF_8)
        } catch (_: IllegalArgumentException) {
            return MorphologyMembership.UNAVAILABLE
        }
        if (query.size > MAX_WORD_BYTES) return MorphologyMembership.UNAVAILABLE
        val word = ByteArray(MAX_WORD_BYTES)
        return try {
            var low = 0
            var high = blocks - 1
            var selected = -1
            while (low <= high) {
                val middle = (low + high).ushr(1)
                val offset = dataOffset + bytes.getInt(HEADER_BYTES + 4 * middle)
                val end = dataOffset + bytes.getInt(HEADER_BYTES + 4 * (middle + 1))
                val length = readWord(offset, end, word, 0).first
                if (compare(word, length, query) <= 0) {
                    selected = middle
                    low = middle + 1
                } else high = middle - 1
            }
            if (selected < 0) return MorphologyMembership.ABSENT
            var offset = dataOffset + bytes.getInt(HEADER_BYTES + 4 * selected)
            val end = dataOffset + bytes.getInt(HEADER_BYTES + 4 * (selected + 1))
            var length = 0
            repeat(minOf(BLOCK_SIZE, count - selected * BLOCK_SIZE)) {
                val decoded = readWord(offset, end, word, length)
                length = decoded.first
                val next = decoded.second
                check(next <= end)
                val comparison = compare(word, length, query)
                if (comparison == 0) {
                    val lemma = bytes.getInt(offset + 2)
                    check(lemma >= 0)
                    return MorphologyMembership(true, true, lemma.takeIf { it != 0 })
                }
                if (comparison > 0) return MorphologyMembership.ABSENT
                offset = next
            }
            check(offset == end)
            MorphologyMembership.ABSENT
        } catch (_: Exception) {
            MorphologyMembership.UNAVAILABLE
        } finally {
            query.fill(0)
            word.fill(0)
        }
    }

    private fun readWord(offset: Int, end: Int, word: ByteArray, previousLength: Int): Pair<Int, Int> {
        check(offset >= dataOffset && end <= bytes.limit() - 32 && offset + 6 < end)
        val prefix = bytes.get(offset).toInt() and 255
        val suffix = bytes.get(offset + 1).toInt() and 255
        check(prefix <= previousLength && suffix > 0 && prefix + suffix <= MAX_WORD_BYTES)
        check(offset + 6 + suffix <= end)
        check(bytes.getInt(offset + 2) >= 0)
        for (i in 0 until suffix) word[prefix + i] = bytes.get(offset + 6 + i)
        return Pair(prefix + suffix, offset + 6 + suffix)
    }

    private fun validateRecords() {
        val previous = ByteArray(MAX_WORD_BYTES)
        val word = ByteArray(MAX_WORD_BYTES)
        var previousLength = 0
        var visited = 0
        for (block in 0 until blocks) {
            check(!Thread.currentThread().isInterrupted)
            var offset = dataOffset + bytes.getInt(HEADER_BYTES + 4 * block)
            val end = dataOffset + bytes.getInt(HEADER_BYTES + 4 * (block + 1))
            var length = 0
            repeat(minOf(BLOCK_SIZE, count - visited)) {
                val decoded = readWord(offset, end, word, length)
                length = decoded.first
                if (visited > 0) check(compare(previous, previousLength, word, length) < 0)
                word.copyInto(previous, 0, 0, length)
                previousLength = length
                visited++
                offset = decoded.second
            }
            check(offset == end)
        }
        check(visited == count)
    }

    private fun compare(word: ByteArray, length: Int, query: ByteArray, queryLength: Int = query.size): Int {
        for (i in 0 until minOf(length, queryLength)) {
            val result = (word[i].toInt() and 255) - (query[i].toInt() and 255)
            if (result != 0) return result
        }
        return length - queryLength
    }

    companion object {
        const val BLOCK_SIZE = 32
        const val MAX_ASSET_BYTES = 96 * 1024 * 1024
        private const val HEADER_BYTES = 24
        private const val MAX_WORD_BYTES = 64

        /** Strict compatibility entry point; qualification/replay must use full validation. */
        fun open(source: ByteBuffer, expectedSha256: String? = null): MorphologyLexicon =
            validate(source, expectedSha256)

        /** Worker-only full identity, record ordering, block-boundary and payload validation. */
        fun validate(source: ByteBuffer, expectedSha256: String? = null): MorphologyLexicon = try {
            val bytes = source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN)
            check(bytes.limit() in (HEADER_BYTES + 40)..MAX_ASSET_BYTES)
            PackedAssetDigest.verify(bytes, expectedSha256)
            headers(bytes).also { it.validateRecords() }
        } catch (_: Exception) {
            MorphologyLexicon.UNAVAILABLE
        }

        /**
         * Only immutable, full mappings of signed APK assets, with the frozen packaged size.
         * No body SHA/record walk here: [validate] retains exhaustive qualification checks.
         */
        internal fun openPackaged(source: ByteBuffer, expectedBytes: Long): MorphologyLexicon = try {
            check(source.isReadOnly && source.position() == 0 && source.limit() == source.capacity())
            check(source.limit().toLong() == expectedBytes)
            headers(source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN))
        } catch (_: Exception) {
            MorphologyLexicon.UNAVAILABLE
        }

        private fun headers(bytes: ByteBuffer): PackedMorphologyLexicon {
            check(!Thread.currentThread().isInterrupted)
            val size = bytes.limit()
            check(size in (HEADER_BYTES + 40)..MAX_ASSET_BYTES)
            check((0..7).map { bytes.get(it).toInt().toChar() }.joinToString("") == "RUNEMRF1")
            check(bytes.getInt(8) == BLOCK_SIZE)
            val count = bytes.getInt(12)
            val blocks = bytes.getInt(16)
            val dataOffset = bytes.getInt(20)
            check(count in 1..6_000_000 && blocks == (count + BLOCK_SIZE - 1) / BLOCK_SIZE)
            check(dataOffset == HEADER_BYTES + 4 * (blocks + 1) && dataOffset < size - 32)
            var last = -1
            for (block in 0..blocks) {
                check(!Thread.currentThread().isInterrupted)
                val offset = bytes.getInt(HEADER_BYTES + 4 * block)
                check(offset > last && offset <= size - 32 - dataOffset)
                if (block == 0) check(offset == 0)
                else check(offset - last >= minOf(BLOCK_SIZE, count - (block - 1) * BLOCK_SIZE) * 7)
                last = offset
            }
            check(last == size - 32 - dataOffset)
            return PackedMorphologyLexicon(bytes, count, blocks, dataOffset)
        }
    }
}
