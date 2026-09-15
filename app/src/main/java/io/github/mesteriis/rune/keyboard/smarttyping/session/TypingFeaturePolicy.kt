package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature

/** Coarse runtime availability; individual candidates still need the existing ownership/confidence checks. */
object TypingFeaturePolicy {
    fun effective(configured: Int, owner: CandidateOwnerState, dictionaryReady: Boolean,
        abbreviationReady: Boolean, personalReady: Boolean, touchReady: Boolean, qualityReady: Boolean): Int {
        if (!owner.baseEligible) return 0
        var result = configured and DiagnosticFeature.MASK
        fun exclude(feature: DiagnosticFeature) { result = result and feature.bit.inv() }
        if (!owner.showsCandidates) {
            listOf(DiagnosticFeature.SPELLING_SUGGESTIONS, DiagnosticFeature.CANDIDATE_STRIP,
                DiagnosticFeature.PHRASE_SUGGESTIONS, DiagnosticFeature.WORD_BOUNDARIES,
                DiagnosticFeature.ABBREVIATIONS, DiagnosticFeature.PHRASE_REVIEW,
                DiagnosticFeature.VISIBLE_UNDO).forEach(::exclude)
        }
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
        return result
    }
}
