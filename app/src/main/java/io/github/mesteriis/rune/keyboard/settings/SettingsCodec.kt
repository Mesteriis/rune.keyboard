package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/**
 * Translates the stored preference map into an immutable [KeyboardSettings] snapshot.
 * Ordinary display settings retain their historical defaults. Smart Typing values fail closed
 * when malformed; absent legacy values migrate to defaults, absent schema-3 values fail closed.
 * Unsupported schemas cannot enable Smart Typing. Decoding never persists or reads model state.
 */
object SettingsCodec {
    const val SCHEMA_VERSION = 3

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
    const val KEY_AUTOCORRECTION_MODE = "autocorrection_mode"
    const val KEY_MECHANICAL_PUNCTUATION = "mechanical_punctuation"
    const val KEY_CONTEXTUAL_PUNCTUATION_MODE = "contextual_punctuation_mode"
    const val KEY_CANDIDATE_STRIP = "candidate_strip"
    const val KEY_PERSONAL_LEARNING = "personal_learning"
    const val KEY_TOUCH_PERSONALIZATION = "touch_personalization"
    const val KEY_PHRASE_SUGGESTIONS = "phrase_suggestions"
    const val KEY_QUALITY_METRICS = "quality_metrics"
    const val KEY_SHADOW_COMPARISON = "shadow_comparison"
    const val KEY_WORD_BOUNDARY_SUGGESTIONS = "word_boundary_suggestions"
    const val KEY_ABBREVIATIONS = "abbreviations"
    const val KEY_PHRASE_REVIEW = "phrase_review"
    const val KEY_VISIBLE_UNDO = "visible_undo"
    const val KEY_PROTECTED_WORDS = "protected_words"
    const val KEY_APP_PROFILES = "app_profiles"
    const val KEY_COLLECT_EXAMPLES = "collect_examples"
    const val KEY_TYPO_PATTERNS = "typo_patterns"


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
        val schema = raw[KEY_SCHEMA_VERSION] as? Int
        val legacy = !raw.containsKey(KEY_SCHEMA_VERSION) || schema == 1 || schema == 2
        val supported = legacy || schema == SCHEMA_VERSION
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
            doubleSpacePeriod = supported && strictBoolean(raw, KEY_DOUBLE_SPACE_PERIOD, legacy && defaults.doubleSpacePeriod),
            autocorrectionMode = if (supported) strictEnum(raw, KEY_AUTOCORRECTION_MODE,
                if (legacy) defaults.autocorrectionMode else AutocorrectionMode.OFF, AutocorrectionMode.OFF)
                else AutocorrectionMode.OFF,
            mechanicalPunctuation = supported && strictBoolean(raw, KEY_MECHANICAL_PUNCTUATION,
                legacy && defaults.mechanicalPunctuation),
            contextualPunctuationMode = if (supported) strictEnum(raw, KEY_CONTEXTUAL_PUNCTUATION_MODE,
                if (legacy) defaults.contextualPunctuationMode else ContextualPunctuationMode.OFF, ContextualPunctuationMode.OFF)
                else ContextualPunctuationMode.OFF,
            candidateStrip = supported && strictBoolean(raw, KEY_CANDIDATE_STRIP, legacy && defaults.candidateStrip),
            personalLearning = supported && strictBoolean(raw, KEY_PERSONAL_LEARNING, false),
            touchPersonalization = supported && strictBoolean(raw, KEY_TOUCH_PERSONALIZATION, false),
            phraseSuggestions = supported && strictBoolean(raw, KEY_PHRASE_SUGGESTIONS, false),
            qualityMetrics = supported && strictBoolean(raw, KEY_QUALITY_METRICS, false),
            shadowComparison = supported && strictBoolean(raw, KEY_SHADOW_COMPARISON, false),
            wordBoundarySuggestions = supported && strictBoolean(raw, KEY_WORD_BOUNDARY_SUGGESTIONS, false),
            abbreviations = supported && strictBoolean(raw, KEY_ABBREVIATIONS, false),
            phraseReview = supported && strictBoolean(raw, KEY_PHRASE_REVIEW, false),
            visibleUndo = supported && strictBoolean(raw, KEY_VISIBLE_UNDO, false),
            protectedWords = supported && strictBoolean(raw, KEY_PROTECTED_WORDS, false),
            appProfiles = supported && strictBoolean(raw, KEY_APP_PROFILES, false),
            collectExamples = supported && strictBoolean(raw, KEY_COLLECT_EXAMPLES, false),
            typoPatterns = supported && strictBoolean(raw, KEY_TYPO_PATTERNS, false),

        )
    }

    /** A downgraded app must not overwrite a valid future schema marker on an unrelated write. */
    internal fun isFutureSchema(raw: Map<String, Any?>): Boolean =
        (raw[KEY_SCHEMA_VERSION] as? Int)?.let { it > SCHEMA_VERSION } == true

    private fun strictBoolean(raw: Map<String, Any?>, key: String, absent: Boolean): Boolean =
        if (!raw.containsKey(key)) absent else raw[key] as? Boolean ?: false

    private inline fun <reified T : Enum<T>> strictEnum(raw: Map<String, Any?>, key: String, absent: T, invalid: T): T =
        if (!raw.containsKey(key)) absent else enumOrDefault(raw[key] as? String, invalid)

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
