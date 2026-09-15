package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileInputStream
import java.nio.channels.FileChannel
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PackedMorphologyLexiconTest {
    private val russian = KeyboardLanguage.RUSSIAN

    private fun fixture(): ByteArray {
        val words = ((1..40).map { "слово" + "а".repeat(it % 25) + if (it > 25) "б" else "" } + "почтений").sorted()
        val body = ByteArrayOutputStream()
        val offsets = mutableListOf<Int>()
        var previous = byteArrayOf()
        for ((index, word) in words.withIndex()) {
            val encoded = word.toByteArray(Charsets.UTF_8)
            var prefix = 0
            if (index % 32 == 0) offsets += body.size()
            else while (prefix < minOf(previous.size, encoded.size) && previous[prefix] == encoded[prefix]) prefix++
            body.write(prefix)
            body.write(encoded.size - prefix)
            body.write(ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(if (word == "почтений") 0 else 12).array())
            body.write(encoded, prefix, encoded.size - prefix)
            previous = encoded
        }
        offsets += body.size()
        val header = ByteBuffer.allocate(24 + offsets.size * 4).order(ByteOrder.LITTLE_ENDIAN)
        header.put("RUNEMRF1".toByteArray()).putInt(32).putInt(words.size).putInt(offsets.size - 1).putInt(header.capacity())
        offsets.forEach { header.putInt(it) }
        val contents = header.array() + body.toByteArray()
        return contents + MessageDigest.getInstance("SHA-256").digest(contents)
    }

    @Test fun `exact membership across blocks folding and ambiguity`() {
        val lexicon = PackedMorphologyLexicon.open(ByteBuffer.wrap(fixture()))
        assertTrue(lexicon.lookup(russian, "Почтений").present)
        assertEquals(null, lexicon.lookup(russian, "почтений").lemmaId)
        for (i in 1..40) {
            val word = "слово" + "а".repeat(i % 25) + if (i > 25) "б" else ""
            assertEquals(12, lexicon.lookup(russian, word).lemmaId)
        }
        for (word in listOf("а", "почтения", "словоаабб", "яяяя")) {
            assertEquals(MorphologyMembership.ABSENT, lexicon.lookup(russian, word))
        }
        assertFalse(lexicon.lookup(KeyboardLanguage.ENGLISH, "hello").available)
    }

    @Test fun `truncation corruption and wrong trusted digest fail unavailable`() {
        val bytes = fixture()
        val truncated = bytes.copyOf(bytes.size - 1)
        val corrupt = bytes.copyOf().apply { this[30] = (this[30].toInt() xor 1).toByte() }
        for (invalid in listOf(byteArrayOf(), truncated, corrupt)) {
            assertFalse(PackedMorphologyLexicon.open(ByteBuffer.wrap(invalid)).lookup(russian, "почтений").available)
        }
        assertFalse(PackedMorphologyLexicon.open(ByteBuffer.wrap(bytes), "0".repeat(64)).lookup(russian, "почтений").available)
    }

    @Test fun `packaged real dictionary protects rare word and rejects typo`() {
        val file = File("src/main/assets/smarttyping/lexicon/ru.morph")
        val lexicon = FileInputStream(file).use {
            PackedMorphologyLexicon.open(it.channel.map(FileChannel.MapMode.READ_ONLY, 0, file.length()),
                AndroidMorphologyLexiconLoader.ASSET_SHA256)
        }
        assertTrue(lexicon.lookup(russian, "почтений").present)
        assertTrue(lexicon.lookup(russian, "Почтений").present)
        assertTrue(lexicon.lookup(russian, "нужен").present)
        assertEquals(MorphologyMembership.ABSENT, lexicon.lookup(russian, "нужнн"))
    }

    @Test fun `cancelled load fails unavailable and preserves interruption`() {
        Thread.currentThread().interrupt()
        try {
            assertFalse(PackedMorphologyLexicon.open(ByteBuffer.wrap(fixture())).lookup(russian, "почтений").available)
            assertTrue(Thread.currentThread().isInterrupted)
        } finally {
            Thread.interrupted()
        }
    }
}
