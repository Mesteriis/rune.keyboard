package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.OutputStream
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ModelFileExporterTest {
    @Test
    fun copiesCompleteModel() {
        val bytes = ByteArray(32_769) { (it % 251).toByte() }
        val output = ByteArrayOutputStream()

        ModelFileExporter.copy(ByteArrayInputStream(bytes), output)

        assertArrayEquals(bytes, output.toByteArray())
    }

    @Test
    fun invokesPartialCleanupWhenDestinationFails() {
        var cleanupCalls = 0
        val broken = object : OutputStream() {
            override fun write(value: Int) = throw IOException("full")
            override fun write(bytes: ByteArray, offset: Int, length: Int) = throw IOException("full")
        }

        assertThrows(IOException::class.java) {
            ModelFileExporter.copy(ByteArrayInputStream(byteArrayOf(1, 2, 3)), broken) { cleanupCalls++ }
        }
        assertEquals(1, cleanupCalls)
    }
}
