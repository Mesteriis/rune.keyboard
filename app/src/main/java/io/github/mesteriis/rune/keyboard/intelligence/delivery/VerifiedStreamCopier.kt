package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.InputStream
import java.io.OutputStream
import java.security.MessageDigest

class StreamSizeException(message: String) : IllegalArgumentException(message)

data class VerifiedCopyResult(val bytesCopied: Long, val sha256: String)

object VerifiedStreamCopier {
    fun copy(input: InputStream, output: OutputStream, expectedSize: Long): VerifiedCopyResult {
        require(expectedSize > 0) { "expectedSize must be positive" }
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        var copied = 0L
        while (copied < expectedSize) {
            val allowed = minOf(buffer.size.toLong(), expectedSize - copied).toInt()
            val count = input.read(buffer, 0, allowed)
            if (count < 0) throw StreamSizeException("stream ended at $copied of $expectedSize bytes")
            if (count == 0) continue
            output.write(buffer, 0, count)
            digest.update(buffer, 0, count)
            copied += count
        }
        if (input.read() != -1) throw StreamSizeException("stream exceeds $expectedSize bytes")
        return VerifiedCopyResult(copied, digest.digest().joinToString("") { "%02x".format(it) })
    }
}
