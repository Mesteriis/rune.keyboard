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
        assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, settings.autocorrectionMode)
        assertTrue(settings.mechanicalPunctuation)
        assertEquals(ContextualPunctuationMode.OFF, settings.contextualPunctuationMode)
        assertTrue(settings.candidateStrip)
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
        assertFalse(base.affectsKeyboardView(base.copy(autocorrectionMode = AutocorrectionMode.OFF)))
        assertFalse(base.affectsKeyboardView(base.copy(mechanicalPunctuation = false)))
        assertFalse(base.affectsKeyboardView(base.copy(contextualPunctuationMode = ContextualPunctuationMode.OFF)))
        assertFalse(base.affectsKeyboardView(base.copy(candidateStrip = false)))
    }

    @Test
    fun `schema one two and absent legacy maps preserve existing settings and default new fields`() {
        for (schema in listOf(null, 1, 2)) {
            val raw = mutableMapOf<String, Any?>(SettingsCodec.KEY_THEME to "DARK",
                SettingsCodec.KEY_LANGUAGES_ENABLED to "SPANISH", SettingsCodec.KEY_DOUBLE_SPACE_PERIOD to false)
            if (schema != null) raw[SettingsCodec.KEY_SCHEMA_VERSION] = schema
            val result = SettingsCodec.decode(raw)
            assertEquals(ThemePreference.DARK, result.theme)
            assertEquals(listOf(KeyboardLanguage.SPANISH), result.enabledLanguages)
            assertFalse(result.doubleSpacePeriod)
            assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, result.autocorrectionMode)
            assertTrue(result.mechanicalPunctuation)
            assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
            assertTrue(result.candidateStrip)
        }
    }

    @Test
    fun `schema three missing fields fail closed individually`() {
        for (key in smartKeys) {
            val result = SettingsCodec.decode(validSmartValues - key)
            assertEquals(if (key == SettingsCodec.KEY_AUTOCORRECTION_MODE) AutocorrectionMode.OFF else AutocorrectionMode.HIGH_CONFIDENCE,
                result.autocorrectionMode)
            assertEquals(key != SettingsCodec.KEY_MECHANICAL_PUNCTUATION, result.mechanicalPunctuation)
            assertEquals(if (key == SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE) ContextualPunctuationMode.OFF else ContextualPunctuationMode.SUGGESTIONS,
                result.contextualPunctuationMode)
            assertEquals(key != SettingsCodec.KEY_CANDIDATE_STRIP, result.candidateStrip)
            assertEquals(key != SettingsCodec.KEY_DOUBLE_SPACE_PERIOD, result.doubleSpacePeriod)
        }
        assertOff(SettingsCodec.decode(mapOf(SettingsCodec.KEY_SCHEMA_VERSION to 3)))
    }

    @Test
    fun `malformed present enum values including null fail closed without changing valid neighbors`() {
        for (schema in listOf(null, 2, 3)) for (value in listOf(null, "", "future", "suggestions", 1, true, listOf("OFF"))) {
            val raw = validSmartValues.toMutableMap()
            if (schema == null) raw.remove(SettingsCodec.KEY_SCHEMA_VERSION) else raw[SettingsCodec.KEY_SCHEMA_VERSION] = schema
            raw[SettingsCodec.KEY_AUTOCORRECTION_MODE] = value
            var result = SettingsCodec.decode(raw)
            assertEquals(AutocorrectionMode.OFF, result.autocorrectionMode)
            assertTrue(result.mechanicalPunctuation && result.candidateStrip && result.doubleSpacePeriod)
            assertEquals(ContextualPunctuationMode.SUGGESTIONS, result.contextualPunctuationMode)
            raw[SettingsCodec.KEY_AUTOCORRECTION_MODE] = "SUGGESTIONS"
            raw[SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE] = value
            result = SettingsCodec.decode(raw)
            assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
            assertEquals(AutocorrectionMode.SUGGESTIONS, result.autocorrectionMode)
            assertTrue(result.mechanicalPunctuation && result.candidateStrip && result.doubleSpacePeriod)
        }
    }

    @Test
    fun `malformed present booleans fail false including existing double space`() {
        for (schema in listOf(null, 2, 3)) for (key in listOf(SettingsCodec.KEY_MECHANICAL_PUNCTUATION,
            SettingsCodec.KEY_CANDIDATE_STRIP, SettingsCodec.KEY_DOUBLE_SPACE_PERIOD)) {
            for (value in listOf(null, "true", "false", 1, 0L, emptySet<String>())) {
                val raw = validSmartValues.toMutableMap()
                if (schema == null) raw.remove(SettingsCodec.KEY_SCHEMA_VERSION) else raw[SettingsCodec.KEY_SCHEMA_VERSION] = schema
                raw[key] = value
                val result = SettingsCodec.decode(raw)
                assertEquals(key != SettingsCodec.KEY_MECHANICAL_PUNCTUATION, result.mechanicalPunctuation)
                assertEquals(key != SettingsCodec.KEY_CANDIDATE_STRIP, result.candidateStrip)
                assertEquals(key != SettingsCodec.KEY_DOUBLE_SPACE_PERIOD, result.doubleSpacePeriod)
                assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, result.autocorrectionMode)
                assertEquals(ContextualPunctuationMode.SUGGESTIONS, result.contextualPunctuationMode)
            }
        }
    }

    @Test
    fun `unsupported or malformed schema cannot enable smart typing but preserves ordinary settings`() {
        for (schema in listOf(null, "3", 3L, true, 0, -1, 4, Int.MAX_VALUE)) {
            val result = SettingsCodec.decode(validSmartValues + mapOf(SettingsCodec.KEY_SCHEMA_VERSION to schema,
                SettingsCodec.KEY_THEME to "DARK", SettingsCodec.KEY_NUMBER_ROW to true))
            assertOff(result)
            assertEquals(ThemePreference.DARK, result.theme)
            assertTrue(result.numberRow)
        }
    }

    @Test
    fun `autocorrection and punctuation preferences are independent and never availability derived`() {
        for (mode in AutocorrectionMode.entries) for (punctuation in ContextualPunctuationMode.entries) {
            val result = SettingsCodec.decode(validSmartValues + mapOf(
                SettingsCodec.KEY_AUTOCORRECTION_MODE to mode.name,
                SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE to punctuation.name))
            assertEquals(mode, result.autocorrectionMode)
            assertEquals(punctuation, result.contextualPunctuationMode)
            assertTrue(result.mechanicalPunctuation && result.candidateStrip && result.doubleSpacePeriod)
        }
    }

    @Test
    fun `old constructor callers retain new preference defaults`() {
        val settings = KeyboardSettings(listOf(KeyboardLanguage.ENGLISH), StartingLanguage.LastUsed,
            emptyMap(), GapPreset.NORMAL, false, ThemePreference.SYSTEM, HapticMode.OFF, SoundMode.OFF, true, false)
        assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, settings.autocorrectionMode)
        assertTrue(settings.mechanicalPunctuation && settings.candidateStrip)
        assertEquals(ContextualPunctuationMode.OFF, settings.contextualPunctuationMode)
        assertFalse(settings.doubleSpacePeriod)
    }

    private val smartKeys = listOf(SettingsCodec.KEY_AUTOCORRECTION_MODE, SettingsCodec.KEY_MECHANICAL_PUNCTUATION,
        SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE, SettingsCodec.KEY_CANDIDATE_STRIP, SettingsCodec.KEY_DOUBLE_SPACE_PERIOD)
    private val validSmartValues = mapOf<String, Any?>(SettingsCodec.KEY_SCHEMA_VERSION to 3,
        SettingsCodec.KEY_AUTOCORRECTION_MODE to "HIGH_CONFIDENCE", SettingsCodec.KEY_MECHANICAL_PUNCTUATION to true,
        SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE to "SUGGESTIONS", SettingsCodec.KEY_CANDIDATE_STRIP to true,
        SettingsCodec.KEY_DOUBLE_SPACE_PERIOD to true)

    private fun assertOff(settings: KeyboardSettings) {
        assertEquals(AutocorrectionMode.OFF, settings.autocorrectionMode)
        assertFalse(settings.mechanicalPunctuation)
        assertEquals(ContextualPunctuationMode.OFF, settings.contextualPunctuationMode)
        assertFalse(settings.candidateStrip)
        assertFalse(settings.doubleSpacePeriod)
    }

}
