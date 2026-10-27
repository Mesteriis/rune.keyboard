package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Front-coded exact lookup with no resident per-word objects and no query cache. */
class PackedRareWordLexicon private constructor(
    private val bytes: ByteBuffer,
    private val count: Int,
    private val blocks: Int,
    private val dataOffset: Int,
) : RareWordLexicon {
    override fun lookup(key: String): RareWordMembership {
        if (key.isEmpty() || !TokenUnicode.bounded(key)) return RareWordMembership.UNAVAILABLE
        val query = try { TokenUnicode.folded(key).toByteArray(Charsets.UTF_8) }
        catch (_: IllegalArgumentException) { return RareWordMembership.UNAVAILABLE }
        if (query.size > MAX_WORD_BYTES) return RareWordMembership.UNAVAILABLE
        val word = ByteArray(MAX_WORD_BYTES)
        return try {
            var low = 0
            var high = blocks - 1
            var selected = -1
            while (low <= high) {
                val middle = (low + high).ushr(1)
                val offset = dataOffset + bytes.getInt(HEADER_BYTES + 4 * middle)
                val length = readWord(offset, word, 0).first
                if (compare(word, length, query) <= 0) { selected = middle; low = middle + 1 }
                else high = middle - 1
            }
            if (selected < 0) return RareWordMembership.ABSENT
            var offset = dataOffset + bytes.getInt(HEADER_BYTES + 4 * selected)
            val end = dataOffset + bytes.getInt(HEADER_BYTES + 4 * (selected + 1))
            var length = 0
            repeat(minOf(BLOCK_SIZE, count - selected * BLOCK_SIZE)) {
                val decoded = readWord(offset, word, length)
                length = decoded.first
                val next = decoded.second
                check(next <= end)
                val comparison = compare(word, length, query)
                if (comparison == 0) {
                    val rank = bytes.getInt(offset + 2)
                    check(rank in 1..count)
                    return RareWordMembership(true, true, rank)
                }
                if (comparison > 0) return RareWordMembership.ABSENT
                offset = next
            }
            check(offset == end)
            RareWordMembership.ABSENT
        } catch (_: Exception) {
            RareWordMembership.UNAVAILABLE
        } finally {
            query.fill(0); word.fill(0)
        }
    }

    private fun readWord(offset: Int, word: ByteArray, previousLength: Int): Pair<Int, Int> {
        val prefix = bytes.get(offset).toInt() and 255
        val suffix = bytes.get(offset + 1).toInt() and 255
        check(prefix <= previousLength && suffix > 0 && prefix + suffix <= MAX_WORD_BYTES)
        for (index in 0 until suffix) word[prefix + index] = bytes.get(offset + 6 + index)
        return Pair(prefix + suffix, offset + 6 + suffix)
    }

    private fun compare(word: ByteArray, length: Int, query: ByteArray): Int {
        for (index in 0 until minOf(length, query.size)) {
            val difference = (word[index].toInt() and 255) - (query[index].toInt() and 255)
            if (difference != 0) return difference
        }
        return length - query.size
    }

    companion object {
        const val BLOCK_SIZE = 32
        private const val HEADER_BYTES = 24
        private const val MAX_WORD_BYTES = 64
        private const val MAX_ASSET_BYTES = 16 * 1024 * 1024

        fun open(source: ByteBuffer, expectedSha256: String? = null): RareWordLexicon = try {
            val bytes = source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN)
            val size = bytes.limit()
            check(size in (HEADER_BYTES + 40)..MAX_ASSET_BYTES)
            PackedAssetDigest.verify(bytes, expectedSha256)
            check((0..7).map { bytes.get(it).toInt().toChar() }.joinToString("") == "RUNERAR1")
            check(bytes.getInt(8) == BLOCK_SIZE)
            val count = bytes.getInt(12)
            val blocks = bytes.getInt(16)
            val dataOffset = bytes.getInt(20)
            check(count in 1..1_000_000 && blocks == (count + BLOCK_SIZE - 1) / BLOCK_SIZE)
            check(dataOffset == HEADER_BYTES + 4 * (blocks + 1) && dataOffset < size - 32)
            var last = -1
            for (block in 0..blocks) {
                val offset = bytes.getInt(HEADER_BYTES + 4 * block)
                check(offset > last && offset <= size - 32 - dataOffset)
                if (block == 0) check(offset == 0)
                if (block < blocks) check(bytes.get(dataOffset + offset).toInt() == 0)
                last = offset
            }
            check(last == size - 32 - dataOffset)
            PackedRareWordLexicon(bytes, count, blocks, dataOffset)
        } catch (_: Exception) {
            RareWordLexicon.UNAVAILABLE
        }
    }
}
