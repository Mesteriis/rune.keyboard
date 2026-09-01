package io.github.mesteriis.rune.keyboard.ime.model

import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.settings.StartingLanguage
import org.junit.Assert.assertEquals
import org.junit.Test

class KeyboardSessionPolicyTest {
    private val settings = KeyboardSettings.DEFAULT

    @Test
    fun `restarting the same editor keeps caps lock, layer and language`() {
        val previous = KeyboardState(
            language = KeyboardLanguage.SPANISH,
            layer = KeyboardLayer.SYMBOLS_ALT,
            shiftMode = ShiftMode.LOCKED,
        )

        val state = KeyboardSessionPolicy.onStartInput(
            previous = previous,
            restarting = true,
            settings = settings,
            lastUsedLanguage = KeyboardLanguage.ENGLISH,
        )

        assertEquals(KeyboardLanguage.SPANISH, state.language)
        assertEquals(KeyboardLayer.SYMBOLS_ALT, state.layer)
        assertEquals(ShiftMode.LOCKED, state.shiftMode)
    }

    @Test
    fun `restarting still picks up changed settings`() {
        val previous = KeyboardState(language = KeyboardLanguage.SPANISH, shiftMode = ShiftMode.LOCKED)
        val narrowed = settings.copy(
            enabledLanguages = listOf(KeyboardLanguage.RUSSIAN),
            doubleSpacePeriod = false,
        )

        val state = KeyboardSessionPolicy.onStartInput(
            previous = previous,
            restarting = true,
            settings = narrowed,
            lastUsedLanguage = KeyboardLanguage.SPANISH,
        )

        assertEquals(KeyboardLanguage.RUSSIAN, state.language)
        assertEquals(false, state.doubleSpacePeriodEnabled)
    }

    @Test
    fun `a new editor resets shift and layer`() {
        val previous = KeyboardState(
            language = KeyboardLanguage.ENGLISH,
            layer = KeyboardLayer.SYMBOLS,
            shiftMode = ShiftMode.LOCKED,
        )

        val state = KeyboardSessionPolicy.onStartInput(
            previous = previous,
            restarting = false,
            settings = settings,
            lastUsedLanguage = KeyboardLanguage.ENGLISH,
        )

        assertEquals(KeyboardLayer.LETTERS, state.layer)
        assertEquals(ShiftMode.OFF, state.shiftMode)
    }

    @Test
    fun `last used is the default starting language`() {
        assertEquals(
            KeyboardLanguage.SPANISH,
            KeyboardSessionPolicy.resolveStartLanguage(settings, KeyboardLanguage.SPANISH),
        )
    }

    @Test
    fun `a fixed starting language wins over the last used one`() {
        val fixed = settings.copy(
            startingLanguage = StartingLanguage.Fixed(KeyboardLanguage.RUSSIAN),
        )

        assertEquals(
            KeyboardLanguage.RUSSIAN,
            KeyboardSessionPolicy.resolveStartLanguage(fixed, KeyboardLanguage.SPANISH),
        )
    }

    @Test
    fun `a disabled starting language falls back to the first enabled one`() {
        val fixedButDisabled = settings.copy(
            enabledLanguages = listOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.ENGLISH),
            startingLanguage = StartingLanguage.Fixed(KeyboardLanguage.SPANISH),
        )

        assertEquals(
            KeyboardLanguage.RUSSIAN,
            KeyboardSessionPolicy.resolveStartLanguage(fixedButDisabled, KeyboardLanguage.SPANISH),
        )
    }

    @Test
    fun `an unknown last used language falls back to the first enabled one`() {
        val narrowed = settings.copy(enabledLanguages = listOf(KeyboardLanguage.SPANISH))

        assertEquals(
            KeyboardLanguage.SPANISH,
            KeyboardSessionPolicy.resolveStartLanguage(narrowed, null),
        )
        assertEquals(
            KeyboardLanguage.SPANISH,
            KeyboardSessionPolicy.resolveStartLanguage(narrowed, KeyboardLanguage.ENGLISH),
        )
    }
}
