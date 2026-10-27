package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import java.nio.ByteBuffer
import java.security.MessageDigest

/** Strict sealed-asset integrity check; one body digest state, bounded worker-only scratch. */
internal object PackedAssetDigest {
    fun verify(bytes: ByteBuffer, expectedSha256: String?) {
        check(!Thread.currentThread().isInterrupted)
        val size = bytes.limit()
        require(size >= 32)
        val digest = MessageDigest.getInstance("SHA-256")
        val scratch = ByteArray(16 * 1024)
        fun update(end: Int) {
            var cursor = 0
            while (cursor < end) {
                check(!Thread.currentThread().isInterrupted)
                val width = minOf(scratch.size, end - cursor)
                bytes.position(cursor)
                bytes.get(scratch, 0, width)
                digest.update(scratch, 0, width)
                cursor += width
            }
        }
        update(size - 32)
        val entire = if (expectedSha256 == null) null else try {
            digest.clone() as MessageDigest
        } catch (_: CloneNotSupportedException) {
            null
        }
        val trailer = ByteArray(32)
        bytes.position(size - 32)
        bytes.get(trailer)
        require(MessageDigest.isEqual(trailer, digest.digest()))
        if (expectedSha256 != null) {
            val actual = if (entire != null) {
                entire.update(trailer)
                entire.digest()
            } else {
                // A provider without clone support keeps both checks. Reuse the reset
                // digest for a second pass rather than weakening integrity or refusing RU.
                update(size)
                digest.digest()
            }
            require(actual.joinToString("") { "%02x".format(it.toInt() and 255) } == expectedSha256)
        }
    }
}
