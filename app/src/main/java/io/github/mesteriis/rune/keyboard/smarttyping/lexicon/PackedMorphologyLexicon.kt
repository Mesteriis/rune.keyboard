package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest

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
                val length = readWord(offset, word, 0).first
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
                val decoded = readWord(offset, word, length)
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

    private fun readWord(offset: Int, word: ByteArray, previousLength: Int): Pair<Int, Int> {
        val prefix = bytes.get(offset).toInt() and 255
        val suffix = bytes.get(offset + 1).toInt() and 255
        check(prefix <= previousLength && suffix > 0 && prefix + suffix <= MAX_WORD_BYTES)
        for (i in 0 until suffix) word[prefix + i] = bytes.get(offset + 6 + i)
        return Pair(prefix + suffix, offset + 6 + suffix)
    }

    private fun compare(word: ByteArray, length: Int, query: ByteArray): Int {
        for (i in 0 until minOf(length, query.size)) {
            val result = (word[i].toInt() and 255) - (query[i].toInt() and 255)
            if (result != 0) return result
        }
        return length - query.size
    }

    companion object {
        const val BLOCK_SIZE = 32
        const val MAX_ASSET_BYTES = 96 * 1024 * 1024
        private const val HEADER_BYTES = 24
        private const val MAX_WORD_BYTES = 64

        /** Worker-only checksum validation; shares immutable mapped pages, bounded 16 KiB scratch. */
        fun open(source: ByteBuffer, expectedSha256: String? = null): MorphologyLexicon = try {
            val bytes = source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN)
            bytes.position(0)
            val size = bytes.limit()
            check(size in (HEADER_BYTES + 40)..MAX_ASSET_BYTES)
            val digest = MessageDigest.getInstance("SHA-256")
            val entire = MessageDigest.getInstance("SHA-256")
            val scratch = ByteArray(16 * 1024)
            var cursor = 0
            while (cursor < size - 32) {
                check(!Thread.currentThread().isInterrupted)
                val width = minOf(scratch.size, size - 32 - cursor)
                bytes.position(cursor)
                bytes.get(scratch, 0, width)
                digest.update(scratch, 0, width)
                entire.update(scratch, 0, width)
                cursor += width
            }
            val trailer = ByteArray(32)
            bytes.position(size - 32)
            bytes.get(trailer)
            check(MessageDigest.isEqual(trailer, digest.digest()))
            entire.update(trailer)
            if (expectedSha256 != null) {
                val actual = entire.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
                check(actual == expectedSha256)
            }
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
                if (block < blocks) check(bytes.get(dataOffset + offset).toInt() == 0)
                last = offset
            }
            check(last == size - 32 - dataOffset)
            PackedMorphologyLexicon(bytes, count, blocks, dataOffset)
        } catch (_: Exception) {
            MorphologyLexicon.UNAVAILABLE
        }
    }
}
