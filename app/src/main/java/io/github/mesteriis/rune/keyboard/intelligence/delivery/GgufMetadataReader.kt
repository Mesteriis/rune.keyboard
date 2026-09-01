package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.EOFException
import java.io.InputStream
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets

class GgufValidationException(message: String, cause: Throwable? = null) : IllegalArgumentException(message, cause)

data class GgufMetadata(val version: Int, val architecture: String, val fileType: Int)

object GgufMetadataReader {
    private const val MAX_METADATA_ENTRIES = 100_000L
    private const val MAX_STRING_BYTES = 16L * 1024 * 1024

    fun read(input: InputStream): GgufMetadata = try {
        val reader = LittleEndianReader(input)
        if (!reader.bytes(4).contentEquals(byteArrayOf('G'.code.toByte(), 'G'.code.toByte(), 'U'.code.toByte(), 'F'.code.toByte()))) {
            invalid("invalid GGUF magic")
        }
        val version = reader.u32().toInt()
        if (version != 3) invalid("GGUF version must be 3")
        reader.u64() // tensor count
        val metadataCount = reader.u64()
        if (metadataCount > MAX_METADATA_ENTRIES) invalid("metadata entry count is unreasonable")
        var architecture: String? = null
        var fileType: Int? = null
        repeat(metadataCount.toInt()) {
            val key = reader.string()
            when (val type = reader.u32().toInt()) {
                8 -> {
                    val value = reader.string()
                    if (key == "general.architecture") architecture = value
                }
                4 -> {
                    val value = reader.u32().toInt()
                    if (key == "general.file_type") fileType = value
                }
                else -> reader.skipValue(type)
            }
        }
        if (architecture != "qwen3") invalid("general.architecture must be qwen3")
        if (fileType != 15) invalid("general.file_type must be 15 (Q4_K_M)")
        GgufMetadata(version, architecture!!, fileType!!)
    } catch (error: GgufValidationException) {
        throw error
    } catch (error: Exception) {
        throw GgufValidationException("malformed GGUF metadata", error)
    }

    private fun invalid(message: String): Nothing = throw GgufValidationException(message)

    private class LittleEndianReader(private val input: InputStream) {
        fun bytes(count: Int): ByteArray = ByteArray(count).also { target ->
            var offset = 0
            while (offset < count) {
                val read = input.read(target, offset, count - offset)
                if (read < 0) throw EOFException()
                offset += read
            }
        }

        fun u32(): Long = bytes(4).foldIndexed(0L) { index, value, byte ->
            value or ((byte.toLong() and 0xff) shl (index * 8))
        }

        fun u64(): Long {
            val raw = bytes(8)
            var value = 0L
            for (index in 7 downTo 0) value = (value shl 8) or (raw[index].toLong() and 0xff)
            if (value < 0) invalid("unsigned 64-bit value is too large")
            return value
        }

        fun string(): String {
            val length = u64()
            if (length > MAX_STRING_BYTES) invalid("GGUF string is too large")
            val decoder = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
            return decoder.decode(java.nio.ByteBuffer.wrap(bytes(length.toInt()))).toString()
        }

        fun skipValue(type: Int) {
            when (type) {
                0, 1, 7 -> bytes(1)
                2, 3 -> bytes(2)
                4, 5, 6 -> bytes(4)
                8 -> string()
                9 -> {
                    val elementType = u32().toInt()
                    val count = u64()
                    if (count > MAX_METADATA_ENTRIES) invalid("GGUF array is too large")
                    repeat(count.toInt()) { skipValue(elementType) }
                }
                10, 11, 12 -> bytes(8)
                else -> invalid("unknown GGUF value type $type")
            }
        }
    }
}
