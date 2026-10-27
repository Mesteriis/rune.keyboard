package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import kotlin.math.ln
import org.junit.Assert.*
import org.junit.Test

/** Real packaged tables, independently decoded counts; synthetic fixtures cannot prove asset compatibility. */
class FrozenWordPairAssetsTest {
    private data class Asset(val name: String, val size: Long, val hash: String, val counts: List<IntArray>)
    private val assets = listOf(
        Asset("ru-wiki.ctx", FrozenContextualAssets.WIKI_BYTES, FrozenContextualAssets.WIKI_SHA256,
            listOf(intArrayOf(27743, 22548, 70379, 3595935), intArrayOf(435, 368, 711, 30742),
                intArrayOf(138, 134, 26947, 30742))),
        Asset("ru-conversation.ctx", FrozenContextualAssets.CONVERSATION_BYTES, FrozenContextualAssets.CONVERSATION_SHA256,
            listOf(intArrayOf(195, 192, 412, 4004), intArrayOf(46, 46, 107, 2803),
                intArrayOf(58, 58, 496, 2803))),
    )
    private val pairs = listOf("в" to "этом", "я" to "хочу", "я" to "уже")
    private fun bytes(asset: Asset) = File("src/main/assets/smarttyping/experiments", asset.name).readBytes()
    private fun hash(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it.toInt() and 255) }

    @Test fun frozenTablesRetainExactPayloadsAndFeatureValues() {
        for (asset in assets) {
            val bytes = bytes(asset)
            assertEquals(asset.size, bytes.size.toLong())
            assertEquals(asset.hash, hash(bytes))
            val index = PackedContextIndex.validate(ByteBuffer.wrap(bytes), "RUCNTX01", asset.hash) { _, _, n -> n == 16 }!!
            val strict = WordPairFeatures.validate(ByteBuffer.wrap(bytes), asset.hash)!!
            val features = WordPairFeatures.openPackaged(ByteBuffer.wrap(bytes).asReadOnlyBuffer(), asset.size)!!
            for ((i, pair) in pairs.withIndex()) {
                val counts = asset.counts[i]
                val payload = ByteBuffer.wrap(index.payload("${pair.first}\u0000${pair.second}")!!).order(ByteOrder.LITTLE_ENDIAN)
                assertArrayEquals(asset.name, counts, IntArray(4) { payload.int })
                val expected = doubleArrayOf(
                    (ln(1.0 + counts[0]) / ln(10001.0)).coerceAtMost(1.0),
                    (ln(1.0 + counts[1]) / ln(10001.0)).coerceAtMost(1.0),
                    counts[0].toDouble() / (1.0 + counts[2]),
                    counts[0].toDouble() / (1.0 + counts[3]), 0.0, 1.0,
                )
                assertArrayEquals(asset.name, expected, features.extract("${pair.first} ", pair.second, pair.second), 0.0)
                assertArrayEquals(asset.name, strict.extract("${pair.first} ", pair.second, pair.second),
                    features.extract("${pair.first} ", pair.second, pair.second), 0.0)
            }
            assertArrayEquals(DoubleArray(6), features.extract("я ", "несуществующееслово", "несуществующееслово"), 0.0)
        }
    }

    @Test fun realTablesRejectWrongIdentityAndCorruptedBodyOrTrailer() {
        for (asset in assets) {
            val bytes = bytes(asset)
            assertNull(WordPairFeatures.open(ByteBuffer.wrap(bytes), "0".repeat(64)))
            for (offset in listOf(0, bytes.size / 2, bytes.lastIndex)) {
                val changed = bytes.copyOf().apply { this[offset] = (this[offset].toInt() xor 1).toByte() }
                // A rebound full-file hash must not override the independent body trailer.
                assertNull(WordPairFeatures.open(ByteBuffer.wrap(changed), hash(changed)))
            }
        }
    }
}
