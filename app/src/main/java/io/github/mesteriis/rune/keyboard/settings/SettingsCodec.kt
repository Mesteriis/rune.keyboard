package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/**
 * Translates the stored preference map into an immutable [KeyboardSettings] snapshot.
 * Every value falls back to its default when missing, malformed, or no longer valid, so a
 * corrupted preference file can never keep the keyboard from starting.
 */
object SettingsCodec {
    const val SCHEMA_VERSION = 2

    const val KEY_SCHEMA_VERSION = "schema_version"
    const val KEY_LANGUAGE = "language"
    const val KEY_LANGUAGES_ENABLED = "languages_enabled"
    const val KEY_LANGUAGE_STARTING = "language_starting"
    const val KEY_KEY_GAP = "key_gap"
    const val KEY_NUMBER_ROW = "number_row"
    const val KEY_THEME = "theme"
    const val KEY_HAPTIC_MODE = "haptic_mode"
    const val KEY_SOUND_MODE = "sound_mode"
    const val KEY_KEY_PREVIEW = "key_preview"
    const val KEY_DOUBLE_SPACE_PERIOD = "double_space_period"

    const val STARTING_LANGUAGE_LAST_USED = "LAST_USED"

    private const val LANGUAGE_SEPARATOR = ","

    fun heightKey(bucket: SizeBucket): String = when (bucket) {
        SizeBucket.COVER_PORTRAIT -> "height_cover_portrait"
        SizeBucket.COVER_LANDSCAPE -> "height_cover_landscape"
        SizeBucket.INNER_PORTRAIT -> "height_inner_portrait"
        SizeBucket.INNER_LANDSCAPE -> "height_inner_landscape"
    }

    fun encodeLanguages(languages: List<KeyboardLanguage>): String =
        languages.joinToString(LANGUAGE_SEPARATOR) { it.name }

    fun decodeLanguages(raw: String?): List<KeyboardLanguage> {
        val parsed = raw
            ?.split(LANGUAGE_SEPARATOR)
            ?.mapNotNull { name -> languageOrNull(name.trim()) }
            ?.distinct()
            .orEmpty()
        return parsed.ifEmpty { KeyboardSettings.DEFAULT.enabledLanguages }
    }

    fun decode(raw: Map<String, Any?>): KeyboardSettings {
        val defaults = KeyboardSettings.DEFAULT
        val enabledLanguages = decodeLanguages(raw[KEY_LANGUAGES_ENABLED] as? String)
        val heightPresets = SizeBucket.entries.associateWith { bucket ->
            enumOrDefault(raw[heightKey(bucket)] as? String, HeightPreset.NORMAL)
        }
        return KeyboardSettings(
            enabledLanguages = enabledLanguages,
            startingLanguage = decodeStartingLanguage(
                raw = raw[KEY_LANGUAGE_STARTING] as? String,
                enabledLanguages = enabledLanguages,
            ),
            heightPresets = heightPresets,
            keyGap = enumOrDefault(raw[KEY_KEY_GAP] as? String, defaults.keyGap),
            numberRow = raw[KEY_NUMBER_ROW] as? Boolean ?: defaults.numberRow,
            theme = enumOrDefault(raw[KEY_THEME] as? String, defaults.theme),
            hapticMode = enumOrDefault(raw[KEY_HAPTIC_MODE] as? String, defaults.hapticMode),
            soundMode = enumOrDefault(raw[KEY_SOUND_MODE] as? String, defaults.soundMode),
            keyPreview = raw[KEY_KEY_PREVIEW] as? Boolean ?: defaults.keyPreview,
            doubleSpacePeriod = raw[KEY_DOUBLE_SPACE_PERIOD] as? Boolean ?: defaults.doubleSpacePeriod,
        )
    }

    fun decodeLastUsedLanguage(raw: Map<String, Any?>): KeyboardLanguage? =
        languageOrNull((raw[KEY_LANGUAGE] as? String)?.trim())

    private fun decodeStartingLanguage(
        raw: String?,
        enabledLanguages: List<KeyboardLanguage>,
    ): StartingLanguage {
        if (raw == null || raw == STARTING_LANGUAGE_LAST_USED) return StartingLanguage.LastUsed
        val language = languageOrNull(raw.trim()) ?: return StartingLanguage.LastUsed
        return if (language in enabledLanguages) StartingLanguage.Fixed(language) else StartingLanguage.LastUsed
    }

    private fun languageOrNull(name: String?): KeyboardLanguage? {
        if (name.isNullOrEmpty()) return null
        return KeyboardLanguage.entries.firstOrNull { it.name == name }
    }

    private inline fun <reified T : Enum<T>> enumOrDefault(raw: String?, default: T): T {
        if (raw == null) return default
        return enumValues<T>().firstOrNull { it.name == raw } ?: default
    }
}
