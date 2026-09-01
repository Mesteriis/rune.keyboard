package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SettingsCodecTest {
    @Test
    fun `an empty store decodes to the defaults`() {
        val settings = SettingsCodec.decode(emptyMap())

        assertEquals(KeyboardSettings.DEFAULT.enabledLanguages, settings.enabledLanguages)
        assertEquals(StartingLanguage.LastUsed, settings.startingLanguage)
        assertEquals(GapPreset.NORMAL, settings.keyGap)
        assertEquals(ThemePreference.SYSTEM, settings.theme)
        assertEquals(HapticMode.SYSTEM, settings.hapticMode)
        assertEquals(SoundMode.SYSTEM, settings.soundMode)
        assertFalse(settings.numberRow)
        assertTrue(settings.keyPreview)
        assertTrue(settings.doubleSpacePeriod)
        SizeBucket.entries.forEach { bucket ->
            assertEquals(HeightPreset.NORMAL, settings.heightPreset(bucket))
        }
    }

    @Test
    fun `every value round-trips`() {
        val raw = mapOf(
            SettingsCodec.KEY_LANGUAGES_ENABLED to "SPANISH,ENGLISH",
            SettingsCodec.KEY_LANGUAGE_STARTING to "SPANISH",
            SettingsCodec.heightKey(SizeBucket.COVER_PORTRAIT) to "COMPACT",
            SettingsCodec.heightKey(SizeBucket.INNER_LANDSCAPE) to "LARGE",
            SettingsCodec.KEY_KEY_GAP to "WIDE",
            SettingsCodec.KEY_NUMBER_ROW to true,
            SettingsCodec.KEY_THEME to "DARK",
            SettingsCodec.KEY_HAPTIC_MODE to "STRONG",
            SettingsCodec.KEY_SOUND_MODE to "QUIET",
            SettingsCodec.KEY_KEY_PREVIEW to false,
            SettingsCodec.KEY_DOUBLE_SPACE_PERIOD to false,
        )

        val settings = SettingsCodec.decode(raw)

        assertEquals(
            listOf(KeyboardLanguage.SPANISH, KeyboardLanguage.ENGLISH),
            settings.enabledLanguages,
        )
        assertEquals(StartingLanguage.Fixed(KeyboardLanguage.SPANISH), settings.startingLanguage)
        assertEquals(HeightPreset.COMPACT, settings.heightPreset(SizeBucket.COVER_PORTRAIT))
        assertEquals(HeightPreset.LARGE, settings.heightPreset(SizeBucket.INNER_LANDSCAPE))
        assertEquals(HeightPreset.NORMAL, settings.heightPreset(SizeBucket.COVER_LANDSCAPE))
        assertEquals(GapPreset.WIDE, settings.keyGap)
        assertTrue(settings.numberRow)
        assertEquals(ThemePreference.DARK, settings.theme)
        assertEquals(HapticMode.STRONG, settings.hapticMode)
        assertEquals(SoundMode.QUIET, settings.soundMode)
        assertFalse(settings.keyPreview)
        assertFalse(settings.doubleSpacePeriod)
    }

    @Test
    fun `unknown enum values fall back to the defaults`() {
        val raw = mapOf(
            SettingsCodec.KEY_KEY_GAP to "HUGE",
            SettingsCodec.KEY_THEME to "neon",
            SettingsCodec.KEY_HAPTIC_MODE to "",
            SettingsCodec.KEY_SOUND_MODE to "LOUD",
            SettingsCodec.heightKey(SizeBucket.INNER_PORTRAIT) to "GIGANTIC",
        )

        val settings = SettingsCodec.decode(raw)

        assertEquals(GapPreset.NORMAL, settings.keyGap)
        assertEquals(ThemePreference.SYSTEM, settings.theme)
        assertEquals(HapticMode.SYSTEM, settings.hapticMode)
        assertEquals(SoundMode.SYSTEM, settings.soundMode)
        assertEquals(HeightPreset.NORMAL, settings.heightPreset(SizeBucket.INNER_PORTRAIT))
    }

    @Test
    fun `a garbled language list falls back to every language`() {
        listOf("", ",", "KLINGON", "KLINGON,,").forEach { stored ->
            val settings = SettingsCodec.decode(mapOf(SettingsCodec.KEY_LANGUAGES_ENABLED to stored))

            assertEquals(stored, KeyboardSettings.DEFAULT.enabledLanguages, settings.enabledLanguages)
        }
    }

    @Test
    fun `known languages survive alongside unknown ones and duplicates`() {
        val settings = SettingsCodec.decode(
            mapOf(SettingsCodec.KEY_LANGUAGES_ENABLED to "RUSSIAN, KLINGON ,RUSSIAN,ENGLISH"),
        )

        assertEquals(
            listOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.ENGLISH),
            settings.enabledLanguages,
        )
    }

    @Test
    fun `a starting language outside the enabled list reverts to last used`() {
        val settings = SettingsCodec.decode(
            mapOf(
                SettingsCodec.KEY_LANGUAGES_ENABLED to "ENGLISH,RUSSIAN",
                SettingsCodec.KEY_LANGUAGE_STARTING to "SPANISH",
            ),
        )

        assertEquals(StartingLanguage.LastUsed, settings.startingLanguage)
    }

    @Test
    fun `the last used language is read separately and tolerates junk`() {
        assertEquals(
            KeyboardLanguage.RUSSIAN,
            SettingsCodec.decodeLastUsedLanguage(mapOf(SettingsCodec.KEY_LANGUAGE to "RUSSIAN")),
        )
        assertNull(SettingsCodec.decodeLastUsedLanguage(mapOf(SettingsCodec.KEY_LANGUAGE to "ELVISH")))
        assertNull(SettingsCodec.decodeLastUsedLanguage(emptyMap()))
    }

    @Test
    fun `languages encode as a stable ordered list`() {
        val languages = listOf(KeyboardLanguage.SPANISH, KeyboardLanguage.RUSSIAN)

        val encoded = SettingsCodec.encodeLanguages(languages)

        assertEquals("SPANISH,RUSSIAN", encoded)
        assertEquals(languages, SettingsCodec.decodeLanguages(encoded))
    }

    @Test
    fun `keyboard view relevant changes are detected`() {
        val base = KeyboardSettings.DEFAULT

        assertTrue(base.affectsKeyboardView(base.copy(theme = ThemePreference.DARK)))
        assertTrue(base.affectsKeyboardView(base.copy(numberRow = true)))
        assertTrue(base.affectsKeyboardView(base.copy(keyGap = GapPreset.WIDE)))
        assertTrue(base.affectsKeyboardView(base.copy(keyPreview = false)))
        assertTrue(
            base.affectsKeyboardView(
                base.copy(heightPresets = mapOf(SizeBucket.COVER_PORTRAIT to HeightPreset.LARGE)),
            ),
        )
        assertFalse(base.affectsKeyboardView(base.copy(hapticMode = HapticMode.STRONG)))
        assertFalse(base.affectsKeyboardView(base.copy(doubleSpacePeriod = false)))
    }
}
