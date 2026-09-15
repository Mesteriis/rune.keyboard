package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature

/** Coarse runtime availability; individual candidates still need the existing ownership/confidence checks. */
object TypingFeaturePolicy {
    fun effective(configured: Int, owner: CandidateOwnerState, dictionaryReady: Boolean,
        abbreviationReady: Boolean, personalReady: Boolean, touchReady: Boolean, qualityReady: Boolean, controlsReady: Boolean = true, learningReady: Boolean = true, learnedReady: Boolean = false, contextReady: Boolean = false, tapReady: Boolean = false): Int {
        if (!owner.baseEligible) return 0
        var result = configured and DiagnosticFeature.MASK
        fun exclude(feature: DiagnosticFeature) { result = result and feature.bit.inv() }
        if (!owner.showsCandidates) {
            listOf(DiagnosticFeature.SPELLING_SUGGESTIONS, DiagnosticFeature.CANDIDATE_STRIP,
                DiagnosticFeature.PHRASE_SUGGESTIONS, DiagnosticFeature.WORD_BOUNDARIES,
                DiagnosticFeature.ABBREVIATIONS, DiagnosticFeature.PHRASE_REVIEW,
                DiagnosticFeature.VISIBLE_UNDO, DiagnosticFeature.LEARNED_RANKING,
                DiagnosticFeature.COMPACT_CONTEXT).forEach(::exclude)
        }
        if (!owner.canExpandManualCandidates) exclude(DiagnosticFeature.MANUAL_CANDIDATE_EXPANSION)
        if (!owner.canRequestContextual) exclude(DiagnosticFeature.CONTEXTUAL_PUNCTUATION)
        if (!owner.deterministicAutoReplaceQualified &&
            !(owner.modelAutoReplaceQualified && owner.modelRuntimeQualified && owner.contextualModelReady)) {
            exclude(DiagnosticFeature.AUTO_CORRECTION)
        }
        if (owner.language != KeyboardLanguage.RUSSIAN) {
            exclude(DiagnosticFeature.WORD_BOUNDARIES); exclude(DiagnosticFeature.PHRASE_REVIEW)
        }
        if (!dictionaryReady) exclude(DiagnosticFeature.WORD_BOUNDARIES)
        if (!abbreviationReady) exclude(DiagnosticFeature.ABBREVIATIONS)
        if (!personalReady) {
            exclude(DiagnosticFeature.PERSONAL_LEARNING); exclude(DiagnosticFeature.PHRASE_SUGGESTIONS)
        }
        if (!touchReady) exclude(DiagnosticFeature.TOUCH_PERSONALIZATION)
        if (!qualityReady) { exclude(DiagnosticFeature.QUALITY_METRICS); exclude(DiagnosticFeature.SHADOW_COMPARISON) }
        if (!controlsReady) {
            exclude(DiagnosticFeature.PROTECTED_WORDS); exclude(DiagnosticFeature.APP_PROFILES)
            if (configured and DiagnosticFeature.PROTECTED_WORDS.bit != 0) exclude(DiagnosticFeature.AUTO_CORRECTION)
        }
        if (!learningReady) { exclude(DiagnosticFeature.COLLECT_EXAMPLES); exclude(DiagnosticFeature.TYPO_PATTERNS) }
        if (!learnedReady || owner.language != KeyboardLanguage.RUSSIAN) exclude(DiagnosticFeature.LEARNED_RANKING)
        if (!contextReady || owner.language != KeyboardLanguage.RUSSIAN) {
            exclude(DiagnosticFeature.COMPACT_CONTEXT)
        }
        if (!tapReady || owner.language != KeyboardLanguage.RUSSIAN) {
            exclude(DiagnosticFeature.DYNAMIC_TOUCH)
            exclude(DiagnosticFeature.DYNAMIC_TOUCH_APPLY)
        }
        if (result and DiagnosticFeature.DYNAMIC_TOUCH.bit == 0) exclude(DiagnosticFeature.DYNAMIC_TOUCH_APPLY)
        return result
    }
}
