package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.nio.ByteBuffer
import java.nio.ByteOrder
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedAssetDigest

/** Immutable mapped public feature data. Validation runs on a worker before publication. */
internal class PackedContextIndex private constructor(
    private val bytes: ByteBuffer,
    private val count: Int,
    private val blocks: Int,
    private val dataOffset: Int,
) {
    fun payload(key: String): ByteArray? {
        val query = key.toByteArray(Charsets.UTF_8)
        if (query.size !in 1..MAX_KEY_BYTES) return null
        var low = 0
        var high = blocks - 1
        var selected = -1
        while (low <= high) {
            val middle = (low + high).ushr(1)
            val offset = dataOffset + bytes.getInt(HEADER + 4 * middle)
            val length = unsigned(offset + 1)
            val comparison = compare(length, query.size) { index, left ->
                if (left) unsigned(offset + 4 + index) else query[index].toInt() and 255
            }
            if (comparison <= 0) { selected = middle; low = middle + 1 } else high = middle - 1
        }
        if (selected < 0) return null
        var offset = dataOffset + bytes.getInt(HEADER + 4 * selected)
        val word = ByteArray(MAX_KEY_BYTES)
        repeat(minOf(BLOCK, count - selected * BLOCK)) {
            val prefix = unsigned(offset)
            val suffix = unsigned(offset + 1)
            val payloadSize = bytes.getShort(offset + 2).toInt() and 65535
            for (index in 0 until suffix) word[prefix + index] = bytes.get(offset + 4 + index)
            val length = prefix + suffix
            val comparison = compare(length, query.size) { index, left ->
                if (left) word[index].toInt() and 255 else query[index].toInt() and 255
            }
            if (comparison == 0) return ByteArray(payloadSize) { bytes.get(offset + 4 + suffix + it) }
            if (comparison > 0) return null
            offset += 4 + suffix + payloadSize
        }
        return null
    }

    private fun unsigned(offset: Int) = bytes.get(offset).toInt() and 255

    companion object {
        const val BLOCK = 32
        const val MAX_BYTES = 128 * 1024 * 1024
        private const val HEADER = 24
        private const val MAX_KEY_BYTES = 255

        /** Caller retains immutable storage; payload validation must not retain or mutate the buffer. */
        fun open(source: ByteBuffer, magic: String, expectedSha256: String,
            validPayload: (ByteBuffer, Int, Int) -> Boolean): PackedContextIndex? = try {
            val bytes = source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN)
            val size = bytes.limit()
            require(magic.length == 8 && size in (HEADER + 42)..MAX_BYTES)
            PackedAssetDigest.verify(bytes, expectedSha256)
            var cursor: Int
            require(magic.indices.all { bytes.get(it).toInt() == magic[it].code })
            val width = bytes.getInt(8)
            val count = bytes.getInt(12)
            val blocks = bytes.getInt(16)
            val start = bytes.getInt(20)
            require(width == BLOCK && count in 1..8_000_000 && blocks == (count + BLOCK - 1) / BLOCK)
            require(start == HEADER + 4 * (blocks + 1) && start < size - 32)
            var previousOffset = -1
            for (block in 0..blocks) {
                val offset = bytes.getInt(HEADER + 4 * block)
                require(offset > previousOffset && offset <= size - 32 - start)
                if (block == 0) require(offset == 0)
                previousOffset = offset
            }
            require(previousOffset == size - 32 - start)
            var previous = ByteArray(MAX_KEY_BYTES)
            var current = ByteArray(MAX_KEY_BYTES)
            var previousLength = 0
            var visited = 0
            for (block in 0 until blocks) {
                check(!Thread.currentThread().isInterrupted)
                cursor = start + bytes.getInt(HEADER + 4 * block)
                val end = start + bytes.getInt(HEADER + 4 * (block + 1))
                repeat(minOf(BLOCK, count - visited)) { record ->
                    require(cursor + 4 <= end)
                    val prefix = bytes.get(cursor).toInt() and 255
                    val suffix = bytes.get(cursor + 1).toInt() and 255
                    val payloadSize = bytes.getShort(cursor + 2).toInt() and 65535
                    val length = prefix + suffix
                    require(prefix <= previousLength && suffix > 0 && length <= MAX_KEY_BYTES)
                    require(record != 0 || prefix == 0)
                    require(payloadSize in 1..1024 && cursor + 4 + suffix + payloadSize <= end)
                    previous.copyInto(current, 0, 0, prefix)
                    for (index in 0 until suffix) current[prefix + index] = bytes.get(cursor + 4 + index)
                    if (visited > 0) require(compare(previousLength, length) { index, left ->
                        (if (left) previous[index] else current[index]).toInt() and 255
                    } < 0)
                    require(validPayload(bytes, cursor + 4 + suffix, payloadSize))
                    val swap = previous; previous = current; current = swap
                    previousLength = length; visited++; cursor += 4 + suffix + payloadSize
                }
                require(cursor == end)
            }
            require(visited == count)
            PackedContextIndex(bytes, count, blocks, start)
        } catch (_: RuntimeException) { null }

        private inline fun compare(left: Int, right: Int, byte: (Int, Boolean) -> Int): Int {
            for (index in 0 until minOf(left, right)) {
                val comparison = byte(index, true) - byte(index, false)
                if (comparison != 0) return comparison
            }
            return left - right
        }
    }
}
