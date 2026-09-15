package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature
import org.junit.Assert.*
import org.junit.Test

class TypingFeaturePolicyTest {
    private val owner = CandidateOwnerState(true, true, KeyboardLayer.LETTERS, KeyboardLanguage.RUSSIAN,
        false, deterministicAutoReplaceQualified = true, modelAutoReplaceQualified = true,
        contextualPunctuationEnabled = true, contextualModelReady = true)
    private fun effective(state: CandidateOwnerState = owner, dictionary: Boolean = true,
        abbreviations: Boolean = true, personal: Boolean = true, touch: Boolean = true, quality: Boolean = true,
        configured: Int = DiagnosticFeature.MASK) =
        TypingFeaturePolicy.effective(configured, state, dictionary, abbreviations, personal, touch, quality, learnedReady = true, contextReady = true, tapReady = true)
    private fun Int.has(feature: DiagnosticFeature) = this and feature.bit != 0

    @Test fun experimentsRespectReadinessLanguageVisibilityAndApplyDependency() {
        val learned = DiagnosticFeature.LEARNED_RANKING
        val compact = DiagnosticFeature.COMPACT_CONTEXT
        val dynamic = DiagnosticFeature.DYNAMIC_TOUCH
        val apply = DiagnosticFeature.DYNAMIC_TOUCH_APPLY
        val unloaded = TypingFeaturePolicy.effective(DiagnosticFeature.MASK, owner, true, true, true, true, true)
        for (f in listOf(learned, compact, dynamic, apply)) assertFalse(unloaded.has(f))
        for (f in listOf(learned, compact, dynamic, apply)) assertFalse(effective(owner.copy(language = KeyboardLanguage.ENGLISH)).has(f))
        assertFalse(effective(configured = apply.bit).has(apply))
        assertTrue(effective(configured = dynamic.bit).has(dynamic))
        assertFalse(effective(configured = dynamic.bit).has(apply))
        val hidden = effective(owner.copy(candidateStripEnabled = false))
        assertFalse(hidden.has(learned)); assertFalse(hidden.has(compact))
        assertTrue(hidden.has(dynamic)); assertTrue(hidden.has(apply))
    }

    @Test fun contextAndTapReadinessAreIndependentAndDefaultClosed() {
        fun flags(context: Boolean, tap: Boolean) = TypingFeaturePolicy.effective(
            DiagnosticFeature.MASK, owner, true, true, true, true, true,
            learnedReady = true, contextReady = context, tapReady = tap)
        val rankingOnly = flags(context = true, tap = false)
        assertTrue(rankingOnly.has(DiagnosticFeature.COMPACT_CONTEXT))
        assertFalse(rankingOnly.has(DiagnosticFeature.DYNAMIC_TOUCH))
        assertFalse(rankingOnly.has(DiagnosticFeature.DYNAMIC_TOUCH_APPLY))
        val tapOnly = flags(context = false, tap = true)
        assertFalse(tapOnly.has(DiagnosticFeature.COMPACT_CONTEXT))
        assertTrue(tapOnly.has(DiagnosticFeature.DYNAMIC_TOUCH))
        assertTrue(tapOnly.has(DiagnosticFeature.DYNAMIC_TOUCH_APPLY))
        val defaultTap = TypingFeaturePolicy.effective(DiagnosticFeature.MASK, owner,
            true, true, true, true, true, contextReady = true)
        assertFalse(defaultTap.has(DiagnosticFeature.DYNAMIC_TOUCH))
    }

    @Test fun runtimeAndReadinessGateContextualAndModelAutomaticFlags() {
        assertEquals(DiagnosticFeature.MASK, effective())
        for (state in listOf(owner.copy(contextualModelReady = false), owner.copy(modelRuntimeQualified = false))) {
            assertFalse(effective(state).has(DiagnosticFeature.CONTEXTUAL_PUNCTUATION))
            assertTrue(effective(state).has(DiagnosticFeature.AUTO_CORRECTION)) // Qualified local branch remains.
            assertFalse(effective(state.copy(deterministicAutoReplaceQualified = false)).has(DiagnosticFeature.AUTO_CORRECTION))
        }
        assertFalse(effective(owner.copy(deterministicAutoReplaceQualified = false,
            modelAutoReplaceQualified = false)).has(DiagnosticFeature.AUTO_CORRECTION))
    }

    @Test fun hiddenStripDisablesVisualToolsButAllowsQualifiedAutomaticAndMetrics() {
        val flags = effective(owner.copy(candidateStripEnabled = false))
        for (feature in listOf(DiagnosticFeature.CANDIDATE_STRIP, DiagnosticFeature.PHRASE_REVIEW,
            DiagnosticFeature.ABBREVIATIONS, DiagnosticFeature.VISIBLE_UNDO, DiagnosticFeature.CONTEXTUAL_PUNCTUATION))
            assertFalse(flags.has(feature))
        assertTrue(flags.has(DiagnosticFeature.AUTO_CORRECTION))
        assertTrue(flags.has(DiagnosticFeature.QUALITY_METRICS))
    }

    @Test fun sensitiveInactiveSelectionAndNonLetterFieldsDisableAll() {
        for (state in listOf(owner.copy(editorAllowsSmartTyping = false), owner.copy(inputViewActive = false),
            owner.copy(hasSelection = true), owner.copy(layer = KeyboardLayer.SYMBOLS)))
            assertEquals(0, effective(state))
    }

    @Test fun unavailableStoresAndUnsupportedLanguageAreReflected() {
        val flags = effective(dictionary = false, abbreviations = false, personal = false, touch = false, quality = false)
        for (feature in listOf(DiagnosticFeature.WORD_BOUNDARIES, DiagnosticFeature.ABBREVIATIONS,
            DiagnosticFeature.PERSONAL_LEARNING, DiagnosticFeature.PHRASE_SUGGESTIONS,
            DiagnosticFeature.TOUCH_PERSONALIZATION, DiagnosticFeature.QUALITY_METRICS, DiagnosticFeature.SHADOW_COMPARISON))
            assertFalse(flags.has(feature))
        val english = effective(owner.copy(language = KeyboardLanguage.ENGLISH))
        assertFalse(english.has(DiagnosticFeature.WORD_BOUNDARIES))
        assertFalse(english.has(DiagnosticFeature.PHRASE_REVIEW))
        assertTrue(english.has(DiagnosticFeature.ABBREVIATIONS))
    }

    @Test fun effectiveNeverEnablesAnUnconfiguredFlag() {
        for (feature in DiagnosticFeature.entries) assertEquals(
            if (feature == DiagnosticFeature.DYNAMIC_TOUCH_APPLY) 0 else feature.bit, effective(configured = feature.bit))
        assertEquals(0, effective(configured = 0))
    }
}
