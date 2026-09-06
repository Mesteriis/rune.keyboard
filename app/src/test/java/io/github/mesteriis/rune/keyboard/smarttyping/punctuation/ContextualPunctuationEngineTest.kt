package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test

class ContextualPunctuationEngineTest {
    @Test fun `ordinary context produces exact bounded variants and sentence capitalization`() {
        for ((language, prefix, words) in listOf(
            Triple(KeyboardLanguage.ENGLISH, "I think", "this" to "This"),
            Triple(KeyboardLanguage.RUSSIAN, "Я думаю", "это" to "Это"),
            Triple(KeyboardLanguage.SPANISH, "yo pienso", "mañana" to "Mañana"))) {
            val (word, capitalized) = words
            val variants = ContextualPunctuationEngine.variants(prefix, word, language)
            assertEquals(listOf(" ", ", ", ": ", "; ", ". ", "? ", "! "), variants.map { it.boundary })
            assertEquals((0..6).toList(), variants.map { it.id })
            assertEquals(". $capitalized", variants[4].continuation)
            assertFalse(variants.any { it.continuation.contains('¿') || it.continuation.contains('¡') })
        }
    }

    @Test fun `technical mixed and unknown boundaries are conservatively excluded`() {
        for (prefix in listOf("example.com", "mail@host", "/tmp/path", "x_y", "12:30", "word ", "")) {
            assertTrue(prefix, ContextualPunctuationEngine.variants(prefix, "next", KeyboardLanguage.ENGLISH).isEmpty())
        }
        for (word in listOf("two-words", "1word", "a_b", "РусскийLatin", "ALLCAPS")) {
            assertTrue(word, ContextualPunctuationEngine.variants("plain", word, KeyboardLanguage.ENGLISH).isEmpty())
        }
    }

    @Test fun `only the initial code point may change in sentence variants`() {
        val word = "e\u0301xample"
        val variants = ContextualPunctuationEngine.variants("safe", word, KeyboardLanguage.ENGLISH)
        assertEquals(". E\u0301xample", variants[4].continuation)
        assertEquals(word, variants[1].continuation.removePrefix(", "))
    }
}
