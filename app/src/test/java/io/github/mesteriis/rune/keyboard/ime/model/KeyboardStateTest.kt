package io.github.mesteriis.rune.keyboard.ime.model

import org.junit.Assert.assertEquals
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
    fun `language switch resets layer and shift`() {
        val state = KeyboardState(
            language = KeyboardLanguage.ENGLISH,
            layer = KeyboardLayer.SYMBOLS,
            shiftMode = ShiftMode.LOCKED,
        )

        val switched = state.toggleLanguage()

        assertEquals(KeyboardLanguage.RUSSIAN, switched.language)
        assertEquals(KeyboardLayer.LETTERS, switched.layer)
        assertEquals(ShiftMode.OFF, switched.shiftMode)
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
}
