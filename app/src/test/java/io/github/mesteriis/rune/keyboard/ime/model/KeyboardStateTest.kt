package io.github.mesteriis.rune.keyboard.ime.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertThrows
import org.junit.Test

class KeyboardStateTest {
    @Test
    fun `automatic shift is consumed after text`() {
        val state = KeyboardState.initial(
            language = KeyboardLanguage.ENGLISH,
            automaticCapitalization = true,
        )

        assertEquals(ShiftMode.AUTO, state.shiftMode)
        assertEquals(ShiftMode.OFF, state.afterTextCommitted().shiftMode)
    }

    @Test
    fun `double shift tap enables caps lock`() {
        val firstTap = KeyboardState(KeyboardLanguage.ENGLISH).onShiftPressed(nowMillis = 1_000)
        val secondTap = firstTap.onShiftPressed(nowMillis = 1_300)

        assertEquals(ShiftMode.ONCE, firstTap.shiftMode)
        assertEquals(ShiftMode.LOCKED, secondTap.shiftMode)
        assertEquals(ShiftMode.LOCKED, secondTap.afterTextCommitted().shiftMode)
    }

    @Test
    fun `slow second shift tap disables one-shot shift`() {
        val firstTap = KeyboardState(KeyboardLanguage.ENGLISH).onShiftPressed(nowMillis = 1_000)
        val secondTap = firstTap.onShiftPressed(nowMillis = 1_500)

        assertEquals(ShiftMode.OFF, secondTap.shiftMode)
    }

    @Test
    fun `cursor capitalization does not override manual shift`() {
        val manualShift = KeyboardState(KeyboardLanguage.ENGLISH).onShiftPressed(nowMillis = 100)

        assertEquals(ShiftMode.ONCE, manualShift.withAutomaticCapitalization(enabled = false).shiftMode)
    }

    @Test
    fun `double tap from automatic shift enables caps lock`() {
        val automaticShift = KeyboardState.initial(
            language = KeyboardLanguage.ENGLISH,
            automaticCapitalization = true,
        )

        val firstTap = automaticShift.onShiftPressed(nowMillis = 1_000)
        val secondTap = firstTap.onShiftPressed(nowMillis = 1_250)

        assertEquals(ShiftMode.OFF, firstTap.shiftMode)
        assertEquals(ShiftMode.LOCKED, secondTap.shiftMode)
    }

    @Test
    fun `language cycles forward through the enabled order`() {
        var state = KeyboardState(KeyboardLanguage.ENGLISH)

        state = state.switchLanguage(LanguageDirection.NEXT)
        assertEquals(KeyboardLanguage.RUSSIAN, state.language)

        state = state.switchLanguage(LanguageDirection.NEXT)
        assertEquals(KeyboardLanguage.SPANISH, state.language)

        state = state.switchLanguage(LanguageDirection.NEXT)
        assertEquals(KeyboardLanguage.ENGLISH, state.language)
    }

    @Test
    fun `language cycles backward through the enabled order`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH)

        assertEquals(
            KeyboardLanguage.SPANISH,
            state.switchLanguage(LanguageDirection.PREVIOUS).language,
        )
    }

    @Test
    fun `disabled languages never appear in the cycle`() {
        val state = KeyboardState(
            language = KeyboardLanguage.ENGLISH,
            enabledLanguages = listOf(KeyboardLanguage.ENGLISH, KeyboardLanguage.SPANISH),
        )

        val next = state.switchLanguage(LanguageDirection.NEXT)

        assertEquals(KeyboardLanguage.SPANISH, next.language)
        assertEquals(KeyboardLanguage.ENGLISH, next.switchLanguage(LanguageDirection.NEXT).language)
    }

    @Test
    fun `a swipe with a single enabled language changes nothing at all`() {
        val state = KeyboardState(
            language = KeyboardLanguage.RUSSIAN,
            enabledLanguages = listOf(KeyboardLanguage.RUSSIAN),
            layer = KeyboardLayer.SYMBOLS,
            shiftMode = ShiftMode.LOCKED,
        )

        assertEquals(state, state.switchLanguage(LanguageDirection.NEXT))
    }

    @Test
    fun `cycling from a language outside the enabled list falls back to the first`() {
        val state = KeyboardState(
            language = KeyboardLanguage.ENGLISH,
            enabledLanguages = listOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.SPANISH),
        )

        assertEquals(KeyboardLanguage.RUSSIAN, state.switchLanguage(LanguageDirection.NEXT).language)
    }

    @Test
    fun `language switch resets layer and shift`() {
        val state = KeyboardState(
            language = KeyboardLanguage.ENGLISH,
            layer = KeyboardLayer.SYMBOLS,
            shiftMode = ShiftMode.LOCKED,
        )

        val switched = state.switchLanguage(LanguageDirection.NEXT)

        assertEquals(KeyboardLanguage.RUSSIAN, switched.language)
        assertEquals(KeyboardLayer.LETTERS, switched.layer)
        assertEquals(ShiftMode.OFF, switched.shiftMode)
    }

    @Test
    fun `narrowing the enabled languages coerces the active language`() {
        val state = KeyboardState(
            language = KeyboardLanguage.SPANISH,
            layer = KeyboardLayer.SYMBOLS,
        )

        val updated = state.withEnabledLanguages(listOf(KeyboardLanguage.RUSSIAN))

        assertEquals(KeyboardLanguage.RUSSIAN, updated.language)
        assertEquals(KeyboardLayer.LETTERS, updated.layer)
    }

    @Test
    fun `keeping the active language keeps the current layer`() {
        val state = KeyboardState(
            language = KeyboardLanguage.RUSSIAN,
            layer = KeyboardLayer.SYMBOLS,
        )

        val updated = state.withEnabledLanguages(
            listOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.ENGLISH),
        )

        assertEquals(KeyboardLayer.SYMBOLS, updated.layer)
    }

    @Test
    fun `symbol pages toggle back and forth`() {
        val symbols = KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols()

        assertEquals(KeyboardLayer.SYMBOLS, symbols.layer)
        assertEquals(KeyboardLayer.SYMBOLS_ALT, symbols.toggleSymbolsPage().layer)
        assertEquals(KeyboardLayer.SYMBOLS, symbols.toggleSymbolsPage().toggleSymbolsPage().layer)
    }

    @Test
    fun `symbol page toggle does nothing on the letters layer`() {
        val letters = KeyboardState(KeyboardLanguage.ENGLISH)

        assertEquals(letters, letters.toggleSymbolsPage())
    }

    @Test
    fun `letters key returns from the second symbol page`() {
        val altPage = KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols().toggleSymbolsPage()

        assertEquals(KeyboardLayer.LETTERS, altPage.toggleSymbols().layer)
    }

    @Test
    fun `clearing an unset double space undo keeps the same instance`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH)

        assertSame(state, state.clearDoubleSpaceUndo())
    }

    @Test
    fun `an empty language list is rejected`() {
        assertThrows(IllegalArgumentException::class.java) {
            KeyboardState(language = KeyboardLanguage.ENGLISH, enabledLanguages = emptyList())
        }
    }
}
