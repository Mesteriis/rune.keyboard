package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

class PackedLexicalValidationTest {
    private val keys = (0..64).map { "слово%03d".format(it) }
    private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
    private fun hash(bytes: ByteArray) = digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
    private fun sealed(body: ByteArray) = body + digest(body)
    private fun buffer(bytes: ByteArray) = ByteBuffer.wrap(bytes).asReadOnlyBuffer()
    private data class Membership(val available: Boolean, val present: Boolean, val value: Int?)
    private fun reader(bytes: ByteArray, rare: Boolean, packaged: Boolean, expectedBytes: Long = bytes.size.toLong(),
        source: ByteBuffer = buffer(bytes)): (String) -> Membership = if (rare) {
        val index = if (packaged) PackedRareWordLexicon.openPackaged(source, expectedBytes)
            else PackedRareWordLexicon.validate(source, hash(bytes));
        { key -> index.lookup(key).let { Membership(it.available, it.present, it.rank) } }
    } else {
        val index = if (packaged) PackedMorphologyLexicon.openPackaged(source, expectedBytes)
            else PackedMorphologyLexicon.validate(source, hash(bytes));
        { key -> index.lookup(KeyboardLanguage.RUSSIAN, key).let { Membership(it.available, it.present, it.lemmaId) } }
    }

    private data class Fixture(val bytes: ByteArray, val offsets: List<Int>)
    private fun fixture(rare: Boolean, words: List<String> = keys): Fixture {
        val output = ByteArrayOutputStream()
        val blocks = mutableListOf<Int>()
        val offsets = mutableListOf<Int>()
        var previous = byteArrayOf()
        words.forEachIndexed { i, key ->
            val word = key.toByteArray(Charsets.UTF_8)
            var prefix = 0
            if (i % 32 == 0) blocks.add(output.size())
            else while (prefix < minOf(previous.size, word.size) && previous[prefix] == word[prefix]) prefix++
            offsets.add(output.size())
            output.write(prefix); output.write(word.size - prefix)
            output.write(ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(if (rare) i + 1 else 12).array())
            output.write(word, prefix, word.size - prefix)
            previous = word
        }
        blocks.add(output.size())
        val header = ByteBuffer.allocate(24 + 4 * blocks.size).order(ByteOrder.LITTLE_ENDIAN)
        header.put((if (rare) "RUNERAR1" else "RUNEMRF1").toByteArray())
            .putInt(32).putInt(words.size).putInt(blocks.size - 1).putInt(header.capacity())
        blocks.forEach { header.putInt(it) }
        return Fixture(sealed(header.array() + output.toByteArray()), offsets.map { it + header.capacity() })
    }

    @Test fun strictAndPackagedLookupsAgreeAcrossBlocksAndMissingKeys() {
        for (rare in listOf(false, true)) {
            val bytes = fixture(rare).bytes
            val strict = reader(bytes, rare, false)
            val packaged = reader(bytes, rare, true)
            keys.forEachIndexed { i, key ->
                assertEquals(Membership(true, true, if (rare) i + 1 else 12), packaged(key))
                assertEquals(strict(key), packaged(key))
            }
            for (key in listOf("а", "слово032х", "слово999", "яяя")) {
                assertEquals(Membership(true, false, null), packaged(key))
                assertEquals(strict(key), packaged(key))
            }
        }
    }

    @Test fun fullValidationRejectsResealedInnerRecordPayloadAndOrderingDamage() {
        for (rare in listOf(false, true)) {
            val fixture = fixture(rare); val bytes = fixture.bytes
            val inner = fixture.offsets[1]
            val mutations: List<(ByteArray) -> Unit> = listOf(
                { it[inner] = 127 }, { it[inner + 1] = 0 }, { it[inner + 1] = -1 },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(inner + 2, -1) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(12, keys.size - 1) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(28, 1) },
            )
            for ((i, edit) in mutations.withIndex()) {
                val body = bytes.copyOf(bytes.size - 32).also(edit)
                val invalid = sealed(body)
                assertFalse("rare=$rare mutation=$i", reader(invalid, rare, false)(keys[0]).available)
            }
            if (rare) {
                val body = bytes.copyOf(bytes.size - 32)
                ByteBuffer.wrap(body).order(ByteOrder.LITTLE_ENDIAN).putInt(inner + 2, keys.size + 1)
                assertFalse(reader(sealed(body), true, false)(keys[0]).available)
            }
            val reversed = fixture(rare, keys.reversed()).bytes
            assertFalse(reader(reversed, rare, false)(keys[0]).available)
            val duplicate = fixture(rare, listOf("слово", "слово")).bytes
            assertFalse(reader(duplicate, rare, false)("слово").available)
        }
    }

    @Test fun packagedMappingRejectsBadHeadersSizesViewsAndAnchors() {
        for (rare in listOf(false, true)) {
            val fixture = fixture(rare); val bytes = fixture.bytes
            val edits: List<(ByteArray) -> Unit> = listOf(
                { it[0] = 0 },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(8, 31) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(12, Int.MAX_VALUE) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(16, 0) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(20, Int.MAX_VALUE) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(24, -1) },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(28, Int.MAX_VALUE) },
                { it[fixture.offsets[32]] = 1 },
                { it[fixture.offsets[32] + 1] = -1 },
            )
            for ((i, edit) in edits.withIndex()) {
                val invalid = bytes.copyOf().also(edit)
                assertFalse("rare=$rare mutation=$i", reader(invalid, rare, true)(keys[0]).available)
            }
            assertFalse(reader(bytes, rare, true, bytes.size.toLong() + 1)(keys[0]).available)
            assertFalse(reader(bytes, rare, true, source = ByteBuffer.wrap(bytes))(keys[0]).available)
            assertFalse(reader(bytes, rare, true, source = buffer(bytes).apply { position(1) })(keys[0]).available)
            assertFalse(reader(bytes, rare, true, source = buffer(bytes).apply { limit(bytes.size - 1) })(keys[0]).available)
        }
    }

    @Test fun packagedLookupRefusesMalformedInnerRecordsWithoutCrossingBlocks() {
        for (rare in listOf(false, true)) {
            val fixture = fixture(rare)
            val inner = fixture.offsets[1]
            val edits: List<(ByteArray) -> Unit> = listOf(
                { it[inner] = 127 }, { it[inner + 1] = 0 }, { it[inner + 1] = -1 },
                { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(inner + 2, -1) },
            )
            for (edit in edits) {
                val bytes = fixture.bytes.copyOf().also(edit)
                val index = reader(bytes, rare, true)
                assertTrue(index(keys[0]).present)
                assertFalse(index(keys[1]).available)
            }
        }
    }

    @Test fun packagedPathDoesNotPretendToAuthenticateBodyOrTrailer() {
        for (rare in listOf(false, true)) {
            val fixture = fixture(rare)
            for (offset in listOf(fixture.offsets[1] + 2, fixture.bytes.lastIndex)) {
                val bytes = fixture.bytes.copyOf().apply { this[offset] = (this[offset].toInt() xor 1).toByte() }
                assertTrue(reader(bytes, rare, true)(keys[0]).present)
                assertFalse(reader(bytes, rare, false)(keys[0]).available)
            }
        }
    }
}
