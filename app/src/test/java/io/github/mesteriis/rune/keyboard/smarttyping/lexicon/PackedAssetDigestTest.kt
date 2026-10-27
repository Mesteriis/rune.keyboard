package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.security.MessageDigestSpi
import java.security.Provider
import java.security.Security
import java.util.UUID
import java.util.concurrent.atomic.AtomicLong
import org.junit.Assert.*
import org.junit.Test

class PackedAssetDigestTest {
    private val realProvider = MessageDigest.getInstance("SHA-256").provider
    private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-256", realProvider).digest(bytes)
    private fun hash(bytes: ByteArray) = digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
    private val body = ByteArray(40_000) { (it * 17).toByte() }
    private fun sealed(bytes: ByteArray) = bytes + digest(bytes)

    private open class CountingSpi(
        protected val delegate: MessageDigest,
        protected val count: AtomicLong,
    ) : MessageDigestSpi() {
        override fun engineUpdate(value: Byte) { count.incrementAndGet(); delegate.update(value) }
        override fun engineUpdate(input: ByteArray, offset: Int, len: Int) {
            count.addAndGet(len.toLong()); delegate.update(input, offset, len)
        }
        override fun engineDigest(): ByteArray = delegate.digest()
        override fun engineReset() = delegate.reset()
        override fun engineGetDigestLength() = delegate.digestLength
    }

    private class CloningSpi(delegate: MessageDigest, count: AtomicLong) : CountingSpi(delegate, count), Cloneable {
        public override fun clone(): Any = CloningSpi(delegate.clone() as MessageDigest, count)
    }

    /** Scoped real-SHA provider: count actual updates and exercise both JCA clone contracts. */
    private fun withProvider(cloneable: Boolean, test: (AtomicLong) -> Unit) {
        val count = AtomicLong()
        val provider = object : Provider("RuneDigestTest" + UUID.randomUUID(), 1.0, "Scoped SHA-256 clone fixture") {
            init {
                putService(object : Service(this, "MessageDigest", "SHA-256", CountingSpi::class.java.name,
                    emptyList(), emptyMap()) {
                    override fun newInstance(parameter: Any?): Any {
                        val delegate = MessageDigest.getInstance("SHA-256", realProvider)
                        return if (cloneable) CloningSpi(delegate, count) else CountingSpi(delegate, count)
                    }
                })
            }
        }
        try {
            assertEquals(1, Security.insertProviderAt(provider, 1))
            test(count)
        } finally {
            Security.removeProvider(provider.name)
        }
    }

    @Test fun cloningProviderHashesEveryByteExactlyOnceAndKeepsBothChecks() {
        val bytes = sealed(body); val expected = hash(bytes)
        withProvider(true) { count ->
            PackedAssetDigest.verify(ByteBuffer.wrap(bytes), expected)
            assertEquals(bytes.size.toLong(), count.get())
        }
    }

    @Test fun nonCloningProviderRetainsIntegrityWithABoundedSecondPass() {
        val bytes = sealed(body); val expected = hash(bytes)
        withProvider(false) { count ->
            PackedAssetDigest.verify(ByteBuffer.wrap(bytes), expected)
            assertEquals((body.size + bytes.size).toLong(), count.get())
        }
    }

    @Test fun noExternalIdentityStillChecksTheBodyTrailerWithoutASecondHash() {
        val bytes = sealed(body)
        withProvider(false) { count ->
            PackedAssetDigest.verify(ByteBuffer.wrap(bytes), null)
            assertEquals(body.size.toLong(), count.get())
        }
    }

    @Test fun corruptBodyTrailerAndReboundFullHashCannotBypassEitherIdentity() {
        val bytes = sealed(body)
        for (offset in listOf(0, body.lastIndex, bytes.lastIndex)) {
            val changed = bytes.copyOf().apply { this[offset] = (this[offset].toInt() xor 1).toByte() }
            for (cloneable in listOf(false, true)) withProvider(cloneable) {
                assertThrows(IllegalArgumentException::class.java) {
                    PackedAssetDigest.verify(ByteBuffer.wrap(changed), hash(changed))
                }
            }
        }
        val resealed = sealed(body.copyOf().apply { this[0] = (this[0].toInt() xor 1).toByte() })
        assertThrows(IllegalArgumentException::class.java) {
            PackedAssetDigest.verify(ByteBuffer.wrap(resealed), hash(bytes))
        }
    }

    @Test fun cancellationIsPreservedAndInputsDoNotNeedAZeroPosition() {
        val bytes = sealed(body)
        PackedAssetDigest.verify(ByteBuffer.wrap(bytes).apply { position(19) }, hash(bytes))
        Thread.currentThread().interrupt()
        try {
            assertThrows(IllegalStateException::class.java) { PackedAssetDigest.verify(ByteBuffer.wrap(bytes), hash(bytes)) }
            assertTrue(Thread.currentThread().isInterrupted)
        } finally { Thread.interrupted() }
    }
}
