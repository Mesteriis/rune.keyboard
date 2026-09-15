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

    fun writeQualityMetrics(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_QUALITY_METRICS, enabled) } }
    fun writeShadowComparison(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_SHADOW_COMPARISON, enabled) } }
    fun writeWordBoundarySuggestions(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_WORD_BOUNDARY_SUGGESTIONS, enabled) } }
    fun writeAbbreviations(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_ABBREVIATIONS, enabled) } }
    fun writePhraseReview(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_PHRASE_REVIEW, enabled) } }
    fun writeVisibleUndo(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_VISIBLE_UNDO, enabled) } }

    /** One preference transaction: observers never see a partially disabled feature set. */
    fun disableAdditionalTyping() {
        edit {
            listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
                SettingsCodec.KEY_PHRASE_SUGGESTIONS, SettingsCodec.KEY_QUALITY_METRICS,
                SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_WORD_BOUNDARY_SUGGESTIONS,
                SettingsCodec.KEY_ABBREVIATIONS, SettingsCodec.KEY_PHRASE_REVIEW, SettingsCodec.KEY_VISIBLE_UNDO,
                SettingsCodec.KEY_PROTECTED_WORDS, SettingsCodec.KEY_APP_PROFILES,
                SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS,
                SettingsCodec.KEY_LEARNED_RANKING, SettingsCodec.KEY_COMPACT_CONTEXT, SettingsCodec.KEY_DYNAMIC_TOUCH, SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY).forEach { putBoolean(it, false) }
        }
    }

    fun writeProtectedWords(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_PROTECTED_WORDS, enabled) } }
    fun writeAppProfiles(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_APP_PROFILES, enabled) } }
    fun writeCollectExamples(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_COLLECT_EXAMPLES, enabled) } }
    fun writeTypoPatterns(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_TYPO_PATTERNS, enabled) } }
    fun writeLearnedRanking(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_LEARNED_RANKING, enabled) } }
    fun writeCompactContext(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_COMPACT_CONTEXT, enabled) } }
    fun writeDynamicTouch(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_DYNAMIC_TOUCH, enabled) } }
    fun writeDynamicTouchApply(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, enabled) } }
    fun notifyTypingControlsChanged() { edit { putLong("typing_controls_revision", System.nanoTime()) } }

    fun writePersonalLearning(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_PERSONAL_LEARNING, enabled) } }
    fun writeTouchPersonalization(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_TOUCH_PERSONALIZATION, enabled) } }
    fun writePhraseSuggestions(enabled: Boolean) { edit { putBoolean(SettingsCodec.KEY_PHRASE_SUGGESTIONS, enabled) } }
    fun notifyPersonalProfileChanged() { edit { putLong("personal_profile_revision", System.nanoTime()) } }

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
