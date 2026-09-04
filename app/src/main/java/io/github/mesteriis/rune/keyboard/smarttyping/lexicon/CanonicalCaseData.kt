package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets

internal class CanonicalCaseData private constructor(
    private val bytes: ByteArray,
    private val count: Int,
    private val recordsStart: Int,
) {
    fun lookup(key: String): CanonicalCase? {
        val query = key.toByteArray(StandardCharsets.UTF_8)
        var low = 0
        var high = count - 1
        while (low <= high) {
            val middle = (low + high).ushr(1)
            val record = recordsStart + offset(middle)
            val flags = bytes[record].toInt() and 0xff
            val keyLength = bytes[record + 1].toInt() and 0xff
            val valueLength = bytes[record + 2].toInt() and 0xff
            val order = compare(query, bytes, record + 3, keyLength)
            when {
                order < 0 -> high = middle - 1
                order > 0 -> low = middle + 1
                else -> {
                    val value = String(bytes, record + 3 + keyLength, valueLength, StandardCharsets.UTF_8)
                    return CanonicalCase(value, flags == 1)
                }
            }
        }
        return null
    }

    private fun offset(index: Int): Int {
        val position = HEADER_BYTES + index * 4
        return ((bytes[position].toInt() and 0xff) shl 24) or
            ((bytes[position + 1].toInt() and 0xff) shl 16) or
            ((bytes[position + 2].toInt() and 0xff) shl 8) or
            (bytes[position + 3].toInt() and 0xff)
    }

    companion object {
        private const val HEADER_BYTES = 8
        private val MAGIC = byteArrayOf('R'.code.toByte(), 'N'.code.toByte(), 'C'.code.toByte(), '1'.code.toByte())

        fun validate(bytes: ByteArray): CanonicalCaseData {
            require(bytes.size >= HEADER_BYTES + 4 && bytes.copyOfRange(0, 4).contentEquals(MAGIC)) { "CASE_HEADER" }
            val buffer = ByteBuffer.wrap(bytes)
            buffer.position(4)
            val count = buffer.int
            require(count in 1..100_000) { "CASE_COUNT" }
            val recordsStart = HEADER_BYTES.toLong() + (count.toLong() + 1) * 4
            require(recordsStart <= bytes.size) { "CASE_OFFSETS" }
            var previousOffset = 0
            var previousKey: ByteArray? = null
            for (index in 0 until count) {
                val offset = buffer.int
                require(offset == previousOffset) { "CASE_OFFSET" }
                val record = recordsStart.toInt() + offset
                require(record + 3 <= bytes.size) { "CASE_RECORD" }
                val flags = bytes[record].toInt() and 0xff
                val keyLength = bytes[record + 1].toInt() and 0xff
                val valueLength = bytes[record + 2].toInt() and 0xff
                require(flags in 0..1 && keyLength > 0 && valueLength > 0 &&
                    record.toLong() + 3 + keyLength + valueLength <= bytes.size) { "CASE_RECORD" }
                val keyBytes = bytes.copyOfRange(record + 3, record + 3 + keyLength)
                val valueBytes = bytes.copyOfRange(record + 3 + keyLength, record + 3 + keyLength + valueLength)
                val key = decode(keyBytes)
                val value = decode(valueBytes)
                require(TokenUnicode.bounded(key) && TokenUnicode.bounded(value) &&
                    TokenUnicode.nfc(key) == key && TokenUnicode.folded(key) == key &&
                    TokenUnicode.folded(value) == key && CasePattern.analyze(value) == CasePattern.TITLE &&
                    (previousKey == null || compare(previousKey!!, keyBytes, 0, keyBytes.size) < 0)) { "CASE_CANONICAL" }
                previousKey = keyBytes
                previousOffset += 3 + keyLength + valueLength
            }
            require(buffer.int == previousOffset && recordsStart + previousOffset == bytes.size.toLong()) { "CASE_LENGTH" }
            return CanonicalCaseData(bytes, count, recordsStart.toInt())
        }

        private fun decode(value: ByteArray): String = StandardCharsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(value)).toString()

        private fun compare(left: ByteArray, right: ByteArray, rightStart: Int, rightLength: Int): Int {
            val common = minOf(left.size, rightLength)
            for (index in 0 until common) {
                val a = left[index].toInt() and 0xff
                val b = right[rightStart + index].toInt() and 0xff
                if (a != b) return a.compareTo(b)
            }
            return left.size.compareTo(rightLength)
        }
    }
}
