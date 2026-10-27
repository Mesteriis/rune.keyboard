package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedAssetDigest
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Immutable mapped public feature data. Validation runs on a worker before publication. */
internal class PackedContextIndex private constructor(
    private val bytes: ByteBuffer,
    private val count: Int,
    private val blocks: Int,
    private val dataOffset: Int,
    private val validPayload: (ByteBuffer, Int, Int) -> Boolean,
) {
    fun payload(key: String): ByteArray? = try {
        lookup(key)
    } catch (_: RuntimeException) { null }

    private fun lookup(key: String): ByteArray? {
        if (key.length !in 1..MAX_KEY_BYTES) return null
        val query = key.toByteArray(Charsets.UTF_8)
        if (query.size > MAX_KEY_BYTES) return null
        var low = 0
        var high = blocks - 1
        var selected = -1
        while (low <= high) {
            val middle = (low + high).ushr(1)
            val offset = dataOffset + bytes.getInt(HEADER + 4 * middle)
            val end = dataOffset + bytes.getInt(HEADER + 4 * (middle + 1))
            record(offset, end, 0)
            val length = unsigned(offset + 1)
            val comparison = compare(length, query.size) { index, left ->
                if (left) unsigned(offset + 4 + index) else query[index].toInt() and 255
            }
            if (comparison <= 0) { selected = middle; low = middle + 1 } else high = middle - 1
        }
        if (selected < 0) return null
        var offset = dataOffset + bytes.getInt(HEADER + 4 * selected)
        val end = dataOffset + bytes.getInt(HEADER + 4 * (selected + 1))
        val word = ByteArray(MAX_KEY_BYTES)
        var length = 0
        repeat(minOf(BLOCK, count - selected * BLOCK)) {
            val next = record(offset, end, length)
            val prefix = unsigned(offset)
            val suffix = unsigned(offset + 1)
            val payloadSize = bytes.getShort(offset + 2).toInt() and 65535
            for (index in 0 until suffix) word[prefix + index] = bytes.get(offset + 4 + index)
            length = prefix + suffix
            val comparison = compare(length, query.size) { index, left ->
                if (left) word[index].toInt() and 255 else query[index].toInt() and 255
            }
            if (comparison == 0) {
                val payload = ByteArray(payloadSize) { bytes.get(offset + 4 + suffix + it) }
                // Validate the bounded copy before exposing it to bit-field/numeric decoders.
                require(validPayload(ByteBuffer.wrap(payload).asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN), 0, payloadSize))
                return payload
            }
            if (comparison > 0) return null
            offset = next
        }
        require(offset == end)
        return null
    }

    private fun record(offset: Int, end: Int, previousLength: Int): Int {
        require(offset >= dataOffset && end <= bytes.limit() - 32 && offset + 4 < end)
        val prefix = unsigned(offset)
        val suffix = unsigned(offset + 1)
        val payloadSize = bytes.getShort(offset + 2).toInt() and 65535
        require(prefix <= previousLength && suffix > 0 && prefix + suffix <= MAX_KEY_BYTES)
        require(payloadSize in 1..1024 && offset + 4 + suffix + payloadSize <= end)
        return offset + 4 + suffix + payloadSize
    }

    private fun validateRecords() {
        var previous = ByteArray(MAX_KEY_BYTES)
        var current = ByteArray(MAX_KEY_BYTES)
        var previousLength = 0
        var visited = 0
        for (block in 0 until blocks) {
            check(!Thread.currentThread().isInterrupted)
            var cursor = dataOffset + bytes.getInt(HEADER + 4 * block)
            val end = dataOffset + bytes.getInt(HEADER + 4 * (block + 1))
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
    }

    private fun unsigned(offset: Int) = bytes.get(offset).toInt() and 255

    companion object {
        const val BLOCK = 32
        const val MAX_BYTES = 128 * 1024 * 1024
        private const val HEADER = 24
        private const val MAX_KEY_BYTES = 255

        /** Compatibility entry point; qualification and replay retain exhaustive validation. */
        fun open(source: ByteBuffer, magic: String, expectedSha256: String,
            validPayload: (ByteBuffer, Int, Int) -> Boolean): PackedContextIndex? =
            validate(source, magic, expectedSha256, validPayload)

        /** Caller retains immutable storage; payload validation must not retain or mutate the buffer. */
        fun validate(source: ByteBuffer, magic: String, expectedSha256: String,
            validPayload: (ByteBuffer, Int, Int) -> Boolean): PackedContextIndex? = try {
            val bytes = source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN)
            require(bytes.limit() in (HEADER + 42)..MAX_BYTES)
            PackedAssetDigest.verify(bytes, expectedSha256)
            headers(bytes, magic, validPayload).also { it.validateRecords() }
        } catch (_: RuntimeException) { null }

        /** Signed APK mappings only; full integrity and record validation stays in [validate]. */
        fun openPackaged(source: ByteBuffer, magic: String, expectedBytes: Long,
            validPayload: (ByteBuffer, Int, Int) -> Boolean): PackedContextIndex? = try {
            require(source.isReadOnly && source.position() == 0 && source.limit() == source.capacity())
            require(source.limit().toLong() == expectedBytes)
            headers(source.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN), magic, validPayload)
        } catch (_: RuntimeException) { null }

        private fun headers(bytes: ByteBuffer, magic: String,
            validPayload: (ByteBuffer, Int, Int) -> Boolean): PackedContextIndex {
            check(!Thread.currentThread().isInterrupted)
            val size = bytes.limit()
            require(magic.length == 8 && size in (HEADER + 42)..MAX_BYTES)
            require(magic.indices.all { bytes.get(it).toInt() == magic[it].code })
            val width = bytes.getInt(8)
            val count = bytes.getInt(12)
            val blocks = bytes.getInt(16)
            val start = bytes.getInt(20)
            require(width == BLOCK && count in 1..8_000_000 && blocks == (count + BLOCK - 1) / BLOCK)
            require(start == HEADER + 4 * (blocks + 1) && start < size - 32)
            var previousOffset = -1
            for (block in 0..blocks) {
                check(!Thread.currentThread().isInterrupted)
                val offset = bytes.getInt(HEADER + 4 * block)
                require(offset > previousOffset && offset <= size - 32 - start)
                if (block == 0) require(offset == 0)
                previousOffset = offset
            }
            require(previousOffset == size - 32 - start)
            val result = PackedContextIndex(bytes, count, blocks, start, validPayload)
            for (block in 0 until blocks) {
                check(!Thread.currentThread().isInterrupted)
                val offset = start + bytes.getInt(HEADER + 4 * block)
                val end = start + bytes.getInt(HEADER + 4 * (block + 1))
                result.record(offset, end, 0)
            }
            return result
        }

        private inline fun compare(left: Int, right: Int, byte: (Int, Boolean) -> Int): Int {
            for (index in 0 until minOf(left, right)) {
                val comparison = byte(index, true) - byte(index, false)
                if (comparison != 0) return comparison
            }
            return left - right
        }
    }
}
