package io.github.mesteriis.rune.keyboard.ime.layout

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LongPressAlternatesTest {
    @Test
    fun `spanish vowels expose their accents`() {
        assertEquals(
            listOf("á", "à", "â", "ä"),
            LongPressAlternates.forLetter("a", KeyboardLanguage.SPANISH),
        )
        assertEquals("é", LongPressAlternates.forLetter("e", KeyboardLanguage.SPANISH).first())
        assertEquals("ú", LongPressAlternates.forLetter("u", KeyboardLanguage.SPANISH).first())
        assertTrue("ü" in LongPressAlternates.forLetter("u", KeyboardLanguage.SPANISH))
    }

    @Test
    fun `english exposes n-tilde and c-cedilla`() {
        assertEquals(listOf("ñ"), LongPressAlternates.forLetter("n", KeyboardLanguage.ENGLISH))
        assertEquals(listOf("ç"), LongPressAlternates.forLetter("c", KeyboardLanguage.ENGLISH))
    }

    @Test
    fun `spanish does not need n-tilde on the n key`() {
        assertTrue(LongPressAlternates.forLetter("n", KeyboardLanguage.SPANISH).isEmpty())
    }

    @Test
    fun `russian exposes yo and hard sign`() {
        assertEquals(listOf("ё"), LongPressAlternates.forLetter("е", KeyboardLanguage.RUSSIAN))
        assertEquals(listOf("ъ"), LongPressAlternates.forLetter("ь", KeyboardLanguage.RUSSIAN))
    }

    @Test
    fun `latin accents are not offered on the russian layout`() {
        assertTrue(LongPressAlternates.forLetter("a", KeyboardLanguage.RUSSIAN).isEmpty())
    }

    @Test
    fun `unknown letters have no alternates`() {
        assertTrue(LongPressAlternates.forLetter("z", KeyboardLanguage.ENGLISH).isEmpty())
        assertTrue(LongPressAlternates.forLetter("щ", KeyboardLanguage.RUSSIAN).isEmpty())
    }

    @Test
    fun `russian quotes lead with guillemets`() {
        val russian = LongPressAlternates.forSymbol("\"", KeyboardLanguage.RUSSIAN)
        val english = LongPressAlternates.forSymbol("\"", KeyboardLanguage.ENGLISH)

        assertEquals(listOf("«", "»"), russian.take(2))
        assertEquals(listOf("“", "”"), english.take(2))
    }

    @Test
    fun `dashes and inverted punctuation are reachable`() {
        assertEquals(listOf("–", "—", "·"), LongPressAlternates.forSymbol("-", KeyboardLanguage.ENGLISH))
        assertEquals(listOf("¡"), LongPressAlternates.forSymbol("!", KeyboardLanguage.SPANISH))
        assertEquals(listOf("¿"), LongPressAlternates.forSymbol("?", KeyboardLanguage.SPANISH))
    }

    @Test
    fun `the period key carries the fast-access punctuation set`() {
        val latin = LongPressAlternates.forSymbol(".", KeyboardLanguage.ENGLISH)

        assertEquals("…", latin.first())
        assertTrue(listOf("'", "\"", "-", "_", "@", "/").all { it in latin })
    }

    @Test
    fun `currency base follows the language and the rest stay reachable`() {
        assertEquals("$", LongPressAlternates.currencyBase(KeyboardLanguage.ENGLISH))
        assertEquals("₽", LongPressAlternates.currencyBase(KeyboardLanguage.RUSSIAN))
        assertEquals("€", LongPressAlternates.currencyBase(KeyboardLanguage.SPANISH))

        KeyboardLanguage.entries.forEach { language ->
            val base = LongPressAlternates.currencyBase(language)
            val alternates = LongPressAlternates.currencyAlternates(language)

            assertTrue(base !in alternates)
            assertEquals(LongPressAlternates.CURRENCIES.size - 1, alternates.size)
            assertEquals(
                LongPressAlternates.CURRENCIES.toSet(),
                (alternates + base).toSet(),
            )
        }
    }
}
