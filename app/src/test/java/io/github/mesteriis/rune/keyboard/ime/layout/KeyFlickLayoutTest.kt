package io.github.mesteriis.rune.keyboard.ime.layout

import android.text.InputType
import io.github.mesteriis.rune.keyboard.ime.model.*
import org.junit.Assert.*
import org.junit.Test

class KeyFlickLayoutTest {
    private val provider = KeyboardLayoutProvider()
    private val editor = EditorContext.from(InputType.TYPE_CLASS_TEXT, 0)

    @Test fun `all three alphabets have stable secondary symbols in every shift mode`() {
        for (language in KeyboardLanguage.entries) {
            val plain = provider.layoutFor(KeyboardState(language), editor).rows.flatten()
            val letters = plain.filter { it.action is KeyboardAction.CommitLetter }
            assertTrue(letters.isNotEmpty())
            assertTrue(letters.all { it.flickDown?.action is KeyboardAction.CommitText })
            assertEquals(('1'..'9').map(Char::toString) + "0", letters.take(10).map { it.flickDown!!.label })
            for (shift in ShiftMode.entries) {
                val shifted = provider.layoutFor(KeyboardState(language, shiftMode = shift), editor).rows.flatten()
                assertEquals(plain.map { it.flickDown }, shifted.map { it.flickDown })
            }
        }
    }
    @Test fun `punctuation and locale specific symbols are directly available`() {
        fun key(language: KeyboardLanguage, label: String) = provider.layoutFor(KeyboardState(language), editor).rows.flatten().first { it.label == label }
        assertEquals("@", key(KeyboardLanguage.ENGLISH, "a").flickDown!!.label)
        assertEquals("&", key(KeyboardLanguage.ENGLISH, "f").flickDown!!.label)
        assertEquals("!", key(KeyboardLanguage.ENGLISH, ",").flickDown!!.label)
        assertEquals("?", key(KeyboardLanguage.ENGLISH, ".").flickDown!!.label)
        assertEquals("₽", key(KeyboardLanguage.RUSSIAN, "в").flickDown!!.label)
        assertEquals("€", key(KeyboardLanguage.SPANISH, "d").flickDown!!.label)
        assertEquals("¿", key(KeyboardLanguage.SPANISH, "ñ").flickDown!!.label)
        assertEquals("ё", key(KeyboardLanguage.RUSSIAN, "е").longPressAlternates.first().label)
        assertEquals("á", key(KeyboardLanguage.SPANISH, "a").longPressAlternates.first().label)
    }
    @Test fun `disabled flicks remove all hints without changing normal keys or long presses`() {
        for (language in KeyboardLanguage.entries) {
            val state = KeyboardState(language)
            val on = provider.layoutFor(state, editor).rows.flatten()
            val off = provider.layoutFor(state, editor, LayoutOptions(keyFlicks = false)).rows.flatten()
            assertTrue(off.all { it.flickDown == null })
            assertEquals(on.map { it.copy(flickDown = null) }, off)
        }
    }
    @Test fun `space actions numeric editors and symbol layers retain their existing gestures`() {
        for (language in KeyboardLanguage.entries) {
            val state = KeyboardState(language)
            val keys = provider.layoutFor(state, editor).rows.flatten()
            assertTrue(keys.filter { it.style != KeyStyle.CHARACTER }.all { it.flickDown == null })
            for (layer in listOf(KeyboardLayer.SYMBOLS, KeyboardLayer.SYMBOLS_ALT)) {
                assertTrue(provider.layoutFor(state.copy(layer = layer), editor).rows.flatten().all { it.flickDown == null })
            }
            assertTrue(provider.layoutFor(state, EditorContext.from(InputType.TYPE_CLASS_NUMBER, 0)).rows.flatten().all { it.flickDown == null })
        }
    }
}
