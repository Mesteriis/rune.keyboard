package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class VerifiedStreamCopierTest {
    @Test
    fun copiesExactlyExpectedBytesAndComputesDigestInOnePass() {
        val bytes = "verified model".toByteArray()
        val output = ByteArrayOutputStream()
        val result = VerifiedStreamCopier.copy(
            input = ByteArrayInputStream(bytes),
            output = output,
            expectedSize = bytes.size.toLong(),
        )

        assertArrayEquals(bytes, output.toByteArray())
        assertEquals(bytes.size.toLong(), result.bytesCopied)
        assertEquals(MessageDigest.getInstance("SHA-256").digest(bytes).toHex(), result.sha256)
    }

    @Test
    fun rejectsShortAndOversizedStreams() {
        assertThrows(StreamSizeException::class.java) {
            VerifiedStreamCopier.copy(ByteArrayInputStream(byteArrayOf(1)), ByteArrayOutputStream(), 2)
        }
        assertThrows(StreamSizeException::class.java) {
            VerifiedStreamCopier.copy(ByteArrayInputStream(byteArrayOf(1, 2)), ByteArrayOutputStream(), 1)
        }
    }

    private fun ByteArray.toHex() = joinToString("") { "%02x".format(it) }
}
