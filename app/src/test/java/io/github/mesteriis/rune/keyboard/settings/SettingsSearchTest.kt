package io.github.mesteriis.rune.keyboard.settings

import org.junit.Assert.*
import org.junit.Test

class SettingsSearchTest {
    @Test fun `search tolerates case accents and russian yo`() {
        assertTrue(SettingsSearch.matches("ОБЪЕМ", "Объём модели"))
        assertTrue(SettingsSearch.matches("vibracion", "Sonido y vibración"))
        assertTrue(SettingsSearch.matches("KEY HEIGHT", "Key height", "Compact"))
    }
    @Test fun `all words must match across title and summary`() {
        assertTrue(SettingsSearch.matches("height compact", "Key height", "Compact"))
        assertFalse(SettingsSearch.matches("height large", "Key height", "Compact"))
        assertTrue(SettingsSearch.matches("  ", "Any setting"))
    }
    @Test fun `unknown destination safely returns to directory`() {
        assertNull(SettingsPage.fromName("obsolete"))
        assertNull(SettingsPage.fromName(null))
    }
    @Test fun `saved app themes survive the new dark default`() {
        ThemePreference.entries.forEach { theme ->
            assertEquals(theme, SettingsCodec.decode(mapOf(SettingsCodec.KEY_THEME to theme.name)).theme)
        }
        assertEquals(ThemePreference.DARK, SettingsCodec.decode(emptyMap()).theme)
    }
}
