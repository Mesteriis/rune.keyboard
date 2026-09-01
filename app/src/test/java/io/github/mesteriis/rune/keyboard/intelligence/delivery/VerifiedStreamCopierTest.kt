package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InterruptedIOException
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
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

    @Test
    fun stopsBeforeReadingWhenWorkerIsInterrupted() {
        val failure = AtomicReference<Throwable>()
        val worker = Thread {
            Thread.currentThread().interrupt()
            runCatching {
                VerifiedStreamCopier.copy(
                    ByteArrayInputStream(byteArrayOf(1)),
                    ByteArrayOutputStream(),
                    1,
                )
            }.exceptionOrNull()?.let(failure::set)
        }

        worker.start()
        worker.join()

        assertTrue(failure.get() is InterruptedIOException)
    }

    @Test
    fun stopsBetweenChunksWhenWorkerIsInterrupted() {
        val firstChunkWritten = CountDownLatch(1)
        val releaseWriter = AtomicBoolean(false)
        val failure = AtomicReference<Throwable>()
        val output = object : ByteArrayOutputStream() {
            private var first = true

            override fun write(bytes: ByteArray, offset: Int, length: Int) {
                super.write(bytes, offset, length)
                if (first) {
                    first = false
                    firstChunkWritten.countDown()
                    while (!releaseWriter.get()) Thread.yield()
                }
            }
        }
        val worker = Thread {
            runCatching {
                VerifiedStreamCopier.copy(
                    ByteArrayInputStream(ByteArray(DEFAULT_BUFFER_SIZE * 2)),
                    output,
                    (DEFAULT_BUFFER_SIZE * 2).toLong(),
                )
            }.exceptionOrNull()?.let(failure::set)
        }

        worker.start()
        assertTrue(firstChunkWritten.await(5, TimeUnit.SECONDS))
        worker.interrupt()
        releaseWriter.set(true)
        worker.join()

        assertTrue(failure.get() is InterruptedIOException)
        assertEquals(DEFAULT_BUFFER_SIZE, output.size())
    }

    private fun ByteArray.toHex() = joinToString("") { "%02x".format(it) }
}
