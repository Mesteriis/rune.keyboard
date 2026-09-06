package io.github.mesteriis.rune.keyboard.settings

import android.content.Context
import android.content.SharedPreferences
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/**
 * The only persistence surface. Reads happen at session start (and when a change arrives), never
 * on the key press path.
 */
class KeyboardPreferences internal constructor(private val preferences: SharedPreferences) {

    constructor(context: Context) : this(
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE),
    )

    fun readSettings(): KeyboardSettings = SettingsCodec.decode(preferences.all)

    fun readLanguage(): KeyboardLanguage? = SettingsCodec.decodeLastUsedLanguage(preferences.all)

    fun writeLanguage(language: KeyboardLanguage) {
        edit { putString(SettingsCodec.KEY_LANGUAGE, language.name) }
    }

    fun writeEnabledLanguages(languages: List<KeyboardLanguage>) {
        require(languages.isNotEmpty()) { "At least one language must stay enabled" }
        edit {
            putString(SettingsCodec.KEY_LANGUAGES_ENABLED, SettingsCodec.encodeLanguages(languages))
        }
    }

    fun writeStartingLanguage(startingLanguage: StartingLanguage) {
        val stored = when (startingLanguage) {
            StartingLanguage.LastUsed -> SettingsCodec.STARTING_LANGUAGE_LAST_USED
            is StartingLanguage.Fixed -> startingLanguage.language.name
        }
        edit { putString(SettingsCodec.KEY_LANGUAGE_STARTING, stored) }
    }

    fun writeHeightPreset(bucket: SizeBucket, preset: HeightPreset) {
        edit { putString(SettingsCodec.heightKey(bucket), preset.name) }
    }

    fun writeKeyGap(preset: GapPreset) {
        edit { putString(SettingsCodec.KEY_KEY_GAP, preset.name) }
    }

    fun writeNumberRow(enabled: Boolean) {
        edit { putBoolean(SettingsCodec.KEY_NUMBER_ROW, enabled) }
    }

    fun writeTheme(theme: ThemePreference) {
        edit { putString(SettingsCodec.KEY_THEME, theme.name) }
    }

    fun writeHapticMode(mode: HapticMode) {
        edit { putString(SettingsCodec.KEY_HAPTIC_MODE, mode.name) }
    }

    fun writeSoundMode(mode: SoundMode) {
        edit { putString(SettingsCodec.KEY_SOUND_MODE, mode.name) }
    }

    fun writeKeyPreview(enabled: Boolean) {
        edit { putBoolean(SettingsCodec.KEY_KEY_PREVIEW, enabled) }
    }

    fun writeDoubleSpacePeriod(enabled: Boolean) {
        edit { putBoolean(SettingsCodec.KEY_DOUBLE_SPACE_PERIOD, enabled) }
    }

    fun writeAutocorrectionMode(mode: AutocorrectionMode) {
        edit { putString(SettingsCodec.KEY_AUTOCORRECTION_MODE, mode.name) }
    }

    fun writeMechanicalPunctuation(enabled: Boolean) {
        edit { putBoolean(SettingsCodec.KEY_MECHANICAL_PUNCTUATION, enabled) }
    }

    fun writeContextualPunctuationMode(mode: ContextualPunctuationMode) {
        edit { putString(SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE, mode.name) }
    }

    fun writeCandidateStrip(enabled: Boolean) {
        edit { putBoolean(SettingsCodec.KEY_CANDIDATE_STRIP, enabled) }
    }

    /**
     * Callers must hold a strong reference to [listener] for as long as they want updates —
     * SharedPreferences keeps registered listeners weakly.
     */
    fun registerListener(listener: SharedPreferences.OnSharedPreferenceChangeListener) {
        preferences.registerOnSharedPreferenceChangeListener(listener)
    }

    fun unregisterListener(listener: SharedPreferences.OnSharedPreferenceChangeListener) {
        preferences.unregisterOnSharedPreferenceChangeListener(listener)
    }

    /** Serialize snapshot + migration across facades sharing the same preferences instance. */
    private fun edit(block: SharedPreferences.Editor.() -> Unit) = synchronized(preferences) {
        val raw = preferences.all
        val editor = preferences.edit()
        if (!SettingsCodec.isFutureSchema(raw)) {
            // Normalize known values before stamping 3 in the same transaction. In particular,
            // an unrelated writer must not turn a malformed/absent schema-3 value into a default.
            val settings = SettingsCodec.decode(raw)
            editor.putString(SettingsCodec.KEY_AUTOCORRECTION_MODE, settings.autocorrectionMode.name)
                .putBoolean(SettingsCodec.KEY_MECHANICAL_PUNCTUATION, settings.mechanicalPunctuation)
                .putString(SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE, settings.contextualPunctuationMode.name)
                .putBoolean(SettingsCodec.KEY_CANDIDATE_STRIP, settings.candidateStrip)
                .putBoolean(SettingsCodec.KEY_DOUBLE_SPACE_PERIOD, settings.doubleSpacePeriod)
                .putInt(SettingsCodec.KEY_SCHEMA_VERSION, SettingsCodec.SCHEMA_VERSION)
        }
        // Explicit choice wins over migration. For a future schema, persist just this key while
        // retaining its version/unknown data; effective Smart Typing stays off until supported.
        editor.apply(block).apply()
    }

    private companion object {
        const val PREFERENCES_NAME = "keyboard_preferences"
    }
}
