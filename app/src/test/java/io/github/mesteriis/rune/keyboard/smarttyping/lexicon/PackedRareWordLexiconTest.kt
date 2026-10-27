package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import java.io.File
import java.io.FileInputStream
import java.nio.channels.FileChannel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PackedRareWordLexiconTest {
    @Test fun `packaged public supplement has exact ranked membership`() {
        val file = File("src/main/assets/${FrozenRareWordLexicon.ASSET_PATH}")
        assertEquals(FrozenRareWordLexicon.ASSET_BYTES, file.length())
        val lexicon = FileInputStream(file).use {
            PackedRareWordLexicon.open(it.channel.map(FileChannel.MapMode.READ_ONLY, 0, file.length()),
                FrozenRareWordLexicon.ASSET_SHA256)
        }
        assertTrue(lexicon.lookup("кармен").present)
        assertTrue(lexicon.lookup("мигеля").present)
        assertTrue(lexicon.lookup("Сесил").present)
        assertEquals(RareWordMembership.ABSENT, lexicon.lookup("совсемнеслово"))
    }

    @Test fun `wrong trusted digest fails unavailable`() {
        val file = File("src/main/assets/${FrozenRareWordLexicon.ASSET_PATH}")
        val lexicon = FileInputStream(file).use {
            PackedRareWordLexicon.open(it.channel.map(FileChannel.MapMode.READ_ONLY, 0, file.length()),
                "0".repeat(64))
        }
        assertFalse(lexicon.lookup("кармен").available)
    }

    @Test fun `real packaged lookup matches fully validated membership`() {
        val file = File("src/main/assets/${FrozenRareWordLexicon.ASSET_PATH}")
        FileInputStream(file).use {
            val mapping = it.channel.map(FileChannel.MapMode.READ_ONLY, 0, file.length())
            val strict = PackedRareWordLexicon.validate(mapping, FrozenRareWordLexicon.ASSET_SHA256)
            val packaged = PackedRareWordLexicon.openPackaged(mapping, FrozenRareWordLexicon.ASSET_BYTES)
            for (key in listOf("кармен", "мигеля", "Сесил", "совсемнеслово")) {
                assertTrue(strict.lookup(key).available)
                assertEquals(key, strict.lookup(key), packaged.lookup(key))
            }
        }
    }
}
