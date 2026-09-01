package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class GgufMetadataReaderTest {
    @Test
    fun readsRequiredQwen3Q4KmMetadata() {
        val metadata = GgufMetadataReader.read(ByteArrayInputStream(gguf("qwen3", 15)))

        assertEquals(3, metadata.version)
        assertEquals("qwen3", metadata.architecture)
        assertEquals(15, metadata.fileType)
    }

    @Test
    fun rejectsWrongVersionArchitectureFileTypeAndTruncation() {
        assertThrows(GgufValidationException::class.java) { GgufMetadataReader.read(ByteArrayInputStream(gguf("llama", 15))) }
        assertThrows(GgufValidationException::class.java) { GgufMetadataReader.read(ByteArrayInputStream(gguf("qwen3", 14))) }
        assertThrows(GgufValidationException::class.java) { GgufMetadataReader.read(ByteArrayInputStream(byteArrayOf(0x47, 0x47))) }
    }

    private fun gguf(architecture: String, fileType: Int): ByteArray {
        val out = ByteArrayOutputStream()
        out.write("GGUF".toByteArray())
        out.write(leInt(3))
        out.write(leLong(0))
        out.write(leLong(2))
        writeString(out, "general.architecture")
        out.write(leInt(8))
        writeString(out, architecture)
        writeString(out, "general.file_type")
        out.write(leInt(4))
        out.write(leInt(fileType))
        return out.toByteArray()
    }

    private fun writeString(out: ByteArrayOutputStream, value: String) {
        val bytes = value.toByteArray()
        out.write(leLong(bytes.size.toLong()))
        out.write(bytes)
    }

    private fun leInt(value: Int) = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array()
    private fun leLong(value: Long) = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putLong(value).array()
}
