package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings

/** Fixed, content-free schema6 vocabulary. Bit assignments are append-only. */
enum class DiagnosticFeature(val field: String) {
    SPELLING_SUGGESTIONS("spellingSuggestions"), AUTO_CORRECTION("autoCorrection"),
    MECHANICAL_PUNCTUATION("mechanicalPunctuation"), CONTEXTUAL_PUNCTUATION("contextualPunctuation"),
    CANDIDATE_STRIP("candidateStrip"), PERSONAL_LEARNING("personalLearning"),
    TOUCH_PERSONALIZATION("touchPersonalization"), PHRASE_SUGGESTIONS("phraseSuggestions"),
    QUALITY_METRICS("qualityMetrics"), SHADOW_COMPARISON("shadowComparison"),
    WORD_BOUNDARIES("wordBoundarySuggestions"), ABBREVIATIONS("abbreviations"),
    PHRASE_REVIEW("phraseReview"), VISIBLE_UNDO("visibleUndo"),
    PROTECTED_WORDS("protectedWords"), APP_PROFILES("appProfiles"),
    COLLECT_EXAMPLES("collectExamples"), TYPO_PATTERNS("typoPatterns"),
    LEARNED_RANKING("learnedRanking"), COMPACT_CONTEXT("compactContext"), DYNAMIC_TOUCH("dynamicTouch"), DYNAMIC_TOUCH_APPLY("dynamicTouchApply");

    val bit: Int get() = 1 shl ordinal
    companion object { val MASK: Int = (1 shl entries.size) - 1 }
}

object DiagnosticFeatures {
    fun configured(settings: KeyboardSettings): Int {
        val enabled = listOf(settings.autocorrectionMode != AutocorrectionMode.OFF,
            settings.autocorrectionMode == AutocorrectionMode.HIGH_CONFIDENCE,
            settings.mechanicalPunctuation, settings.contextualPunctuationMode != ContextualPunctuationMode.OFF,
            settings.candidateStrip, settings.personalLearning, settings.touchPersonalization, settings.phraseSuggestions,
            settings.qualityMetrics, settings.shadowComparison, settings.wordBoundarySuggestions,
            settings.abbreviations, settings.phraseReview, settings.visibleUndo, settings.protectedWords,
            settings.appProfiles, settings.collectExamples, settings.typoPatterns,
            settings.learnedRanking, settings.compactContext, settings.dynamicTouch, settings.dynamicTouchApply)
        return enabled.withIndex().fold(0) { mask, (index, value) -> if (value) mask or (1 shl index) else mask }
    }
}
