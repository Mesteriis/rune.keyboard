package io.github.mesteriis.rune.keyboard.smarttyping.abbreviations

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream

class AbbreviationCodecTest {
    private val ru = KeyboardLanguage.RUSSIAN

    @Test fun `private snapshots round trip empty and Unicode punctuation entries`() {
        assertEquals(emptyList<Abbreviation>(), AbbreviationCodec.decode(AbbreviationCodec.encode(emptyList())))
        val entries = listOf(Abbreviation(ru, "щб", "Щас буду — подожди!"),
            Abbreviation(KeyboardLanguage.SPANISH, "mañ", "Mañana, a las 8."))
        assertEquals(entries, AbbreviationCodec.decode(AbbreviationCodec.encode(entries)))
    }

    @Test fun `rejects malformed headers counts languages duplicate keys and unsafe content`() {
        fun raw(count: Int = 1, language: String = "RUSSIAN", key: String = "щб", expansion: String = "щас буду"): ByteArray {
            val output = ByteArrayOutputStream()
            DataOutputStream(output).use { data ->
                data.writeInt(0x52414231)
                data.writeInt(count)
                repeat(count.coerceIn(0, 129)) { data.writeUTF(language); data.writeUTF(key); data.writeUTF(expansion) }
            }
            return output.toByteArray()
        }
        listOf(raw(-1), raw(129), raw(language = "UNKNOWN"), raw(2), raw(key = "ЩБ"),
            raw(key = "a b"), raw(expansion = "line\nbreak"), raw(expansion = "a\u202Eb"),
            raw(expansion = "x".repeat(129)), raw().apply { this[0] = 0 }).forEach { invalid { AbbreviationCodec.decode(it) } }
    }

    @Test fun `truncated trailing oversized and unrelated profile bytes are rejected`() {
        val bytes = AbbreviationCodec.encode(listOf(Abbreviation(ru, "щб", "щас буду")))
        for (size in bytes.indices) invalid { AbbreviationCodec.decode(bytes.copyOf(size)) }
        invalid { AbbreviationCodec.decode(bytes + byteArrayOf(0)) }
        invalid { AbbreviationCodec.decode(ByteArray(AbbreviationCodec.MAX_FILE_BYTES + 1)) }
        invalid { AbbreviationCodec.decode("RUNE_PERSONAL_PHRASES_V1\nRUSSIAN\tщб\tщас буду\t3".toByteArray()) }
        invalid { AbbreviationCodec.readBounded(ByteArrayInputStream(ByteArray(AbbreviationCodec.MAX_FILE_BYTES + 1))) }
        assertArrayEquals(bytes, AbbreviationCodec.readBounded(ByteArrayInputStream(bytes)))
    }

    @Test fun `maximum astral Unicode entries fit bounded file and preserve values`() {
        val letter = String(Character.toChars(0x10428))
        val entries = List(AbbreviationModel.MAX_ENTRIES) { index ->
            Abbreviation(ru, letter.repeat(30) + ('a' + index / 26) + ('a' + index % 26), letter.repeat(128))
        }
        val bytes = AbbreviationCodec.encode(entries)
        assertTrue(bytes.size <= AbbreviationCodec.MAX_FILE_BYTES)
        assertEquals(entries, AbbreviationCodec.decode(bytes))
    }

    private fun invalid(block: () -> Unit) {
        try { block(); fail("Expected invalid data rejection") }
        catch (_: IllegalArgumentException) { }
        catch (_: java.io.IOException) { }
    }
}
