package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.R
import kotlin.reflect.KProperty1
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** One persisted optional switch and its settings destination. Keys and schema stay unchanged. */
data class AdditionalFeature(
    val key: String,
    val title: Int,
    val summary: Int,
    val page: SettingsPage,
    val value: KProperty1<KeyboardSettings, Boolean>,
    val requiresCandidateStrip: Boolean = false,
    val requiresDynamicTouch: Boolean = false,
) {
    val russianOnly: Boolean get() = page == SettingsPage.EXPERIMENTS

    /** Settings dependencies only; a live editor/resource may impose additional runtime limits. */
    fun unavailableReason(settings: KeyboardSettings): Int? = when {
        russianOnly && KeyboardLanguage.RUSSIAN !in settings.enabledLanguages -> R.string.feature_requires_russian
        requiresCandidateStrip && !settings.candidateStrip -> R.string.feature_requires_candidate_strip
        requiresDynamicTouch && !settings.dynamicTouch -> R.string.feature_requires_dynamic_touch
        else -> null
    }
}

/** Shared by row construction, search destinations and the atomic disable-all transaction. */
object AdditionalFeatures {
    val entries: List<AdditionalFeature> = listOf(
        AdditionalFeature(SettingsCodec.KEY_PERSONAL_LEARNING, R.string.settings_personal_learning,
            R.string.settings_personal_learning_summary, SettingsPage.DICTIONARY, KeyboardSettings::personalLearning),
        AdditionalFeature(SettingsCodec.KEY_TOUCH_PERSONALIZATION, R.string.settings_touch_personalization,
            R.string.settings_touch_personalization_summary, SettingsPage.DICTIONARY, KeyboardSettings::touchPersonalization),
        AdditionalFeature(SettingsCodec.KEY_PHRASE_SUGGESTIONS, R.string.settings_phrase_suggestions,
            R.string.settings_phrase_suggestions_summary, SettingsPage.DICTIONARY, KeyboardSettings::phraseSuggestions, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_QUALITY_METRICS, R.string.settings_quality_metrics,
            R.string.settings_quality_metrics_summary, SettingsPage.ADVANCED, KeyboardSettings::qualityMetrics),
        AdditionalFeature(SettingsCodec.KEY_SHADOW_COMPARISON, R.string.settings_shadow_comparison,
            R.string.settings_shadow_comparison_summary, SettingsPage.ADVANCED, KeyboardSettings::shadowComparison),
        AdditionalFeature(SettingsCodec.KEY_WORD_BOUNDARY_SUGGESTIONS, R.string.settings_word_boundaries,
            R.string.settings_word_boundaries_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::wordBoundarySuggestions, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_ABBREVIATIONS, R.string.settings_abbreviations,
            R.string.settings_abbreviations_summary, SettingsPage.DICTIONARY, KeyboardSettings::abbreviations, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_PHRASE_REVIEW, R.string.settings_phrase_review,
            R.string.settings_phrase_review_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::phraseReview, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_VISIBLE_UNDO, R.string.settings_visible_undo,
            R.string.settings_visible_undo_summary, SettingsPage.TYPING, KeyboardSettings::visibleUndo, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_PROTECTED_WORDS, R.string.settings_protected_words,
            R.string.settings_protected_words_summary, SettingsPage.DICTIONARY, KeyboardSettings::protectedWords),
        AdditionalFeature(SettingsCodec.KEY_APP_PROFILES, R.string.settings_app_profiles,
            R.string.settings_app_profiles_summary, SettingsPage.ADVANCED, KeyboardSettings::appProfiles),
        AdditionalFeature(SettingsCodec.KEY_COLLECT_EXAMPLES, R.string.settings_collect_examples,
            R.string.settings_collect_examples_summary, SettingsPage.DICTIONARY, KeyboardSettings::collectExamples),
        AdditionalFeature(SettingsCodec.KEY_TYPO_PATTERNS, R.string.settings_typo_patterns,
            R.string.settings_typo_patterns_summary, SettingsPage.DICTIONARY, KeyboardSettings::typoPatterns),
        AdditionalFeature(SettingsCodec.KEY_LEARNED_RANKING, R.string.settings_learned_ranking,
            R.string.settings_learned_ranking_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::learnedRanking, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_COMPACT_CONTEXT, R.string.settings_compact_context,
            R.string.settings_compact_context_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::compactContext, requiresCandidateStrip = true),
        AdditionalFeature(SettingsCodec.KEY_DYNAMIC_TOUCH, R.string.settings_dynamic_touch,
            R.string.settings_dynamic_touch_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::dynamicTouch),
        AdditionalFeature(SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, R.string.settings_dynamic_touch_apply,
            R.string.settings_dynamic_touch_apply_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::dynamicTouchApply, requiresDynamicTouch = true),
        AdditionalFeature(SettingsCodec.KEY_MANUAL_CANDIDATE_EXPANSION, R.string.settings_manual_candidate_expansion,
            R.string.settings_manual_candidate_expansion_summary, SettingsPage.EXPERIMENTS, KeyboardSettings::manualCandidateExpansion, requiresCandidateStrip = true),
    )

    fun forKey(key: String): AdditionalFeature = entries.single { it.key == key }
    fun forTitle(title: Int): AdditionalFeature? = entries.firstOrNull { it.title == title }
}
