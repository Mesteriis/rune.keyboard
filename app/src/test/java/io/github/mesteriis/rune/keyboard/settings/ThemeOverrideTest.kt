package io.github.mesteriis.rune.keyboard.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ThemeOverrideTest {
    @Test
    fun `following the system means no override`() {
        assertNull(ThemeOverride.nightOverride(ThemePreference.SYSTEM))
    }

    @Test
    fun `explicit themes force a night mode`() {
        assertEquals(false, ThemeOverride.nightOverride(ThemePreference.LIGHT))
        assertEquals(true, ThemeOverride.nightOverride(ThemePreference.DARK))
    }
}
