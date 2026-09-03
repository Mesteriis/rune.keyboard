package io.github.mesteriis.rune.keyboard.qa

import android.content.res.Configuration
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import java.util.Locale
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Real settings controls, real IME key touches and the existing public Binder editor fixture. */
@RunWith(AndroidJUnit4::class)
class SmartTypingSettingsInstrumentedTest : ImeTestBase() {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val preferences get() = KeyboardPreferences(context)

    @Test fun controlsPersistIndependentlyAndExplainUnavailableCapabilities() {
        driver.configureSmartTyping(AutocorrectionMode.SUGGESTIONS, true)
        driver.launchSettings()
        for ((mode, label) in listOf(AutocorrectionMode.OFF to R.string.smart_typing_off,
            AutocorrectionMode.SUGGESTIONS to R.string.smart_typing_suggestions,
            AutocorrectionMode.HIGH_CONFIDENCE to R.string.smart_typing_high_confidence)) {
            driver.chooseSetting(R.string.settings_autocorrection, label)
            assertEquals(mode, preferences.readSettings().autocorrectionMode)
            assertTrue(preferences.readSettings().mechanicalPunctuation)
            assertTrue(preferences.readSettings().doubleSpacePeriod)
        }
        assertSummary(R.string.settings_autocorrection, R.string.settings_autocorrection_high_confidence_summary)
        driver.chooseSetting(R.string.settings_contextual_punctuation, R.string.smart_typing_off)
        assertEquals(ContextualPunctuationMode.OFF, preferences.readSettings().contextualPunctuationMode)
        driver.chooseSetting(R.string.settings_contextual_punctuation, R.string.smart_typing_suggestions)
        assertSummary(R.string.settings_contextual_punctuation, R.string.settings_contextual_unavailable)
        driver.settingsRow(R.string.settings_candidate_strip).click(); settle()
        assertFalse(preferences.readSettings().candidateStrip)
        assertSummary(R.string.settings_autocorrection, R.string.settings_suggestions_hidden)
        driver.settingsRow(R.string.settings_mechanical_punctuation).click(); settle()
        assertFalse(preferences.readSettings().mechanicalPunctuation)
        assertTrue(preferences.readSettings().doubleSpacePeriod)
        driver.settingsRow(R.string.settings_double_space).click(); settle()
        assertFalse(preferences.readSettings().doubleSpacePeriod)
        assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, preferences.readSettings().autocorrectionMode)
        assertEquals(ContextualPunctuationMode.SUGGESTIONS, preferences.readSettings().contextualPunctuationMode)
        driver.device.pressBack(); driver.launchSettings()
        assertSummary(R.string.settings_autocorrection, R.string.settings_autocorrection_high_confidence_summary)
        assertSummary(R.string.settings_contextual_punctuation, R.string.settings_contextual_unavailable)
        assertFalse(preferences.readSettings().candidateStrip)
        for ((language, automatic, unavailable) in listOf(
            Triple("en", "Automatic replacement is not available in this version.", "Available when the local model is Ready."),
            Triple("ru", "Автоматическая замена в этой версии недоступна.", "Доступно, когда локальная модель готова."))) {
            val config = Configuration(context.resources.configuration).apply { setLocale(Locale.forLanguageTag(language)) }
            val localized = context.createConfigurationContext(config)
            assertTrue(localized.getString(R.string.settings_autocorrection_high_confidence_summary).contains(automatic))
            assertTrue(localized.getString(R.string.settings_contextual_unavailable).contains(unavailable))
        }
    }

    @Test fun liveOffDropsCorrectionsAndEnableWaitsForExplicitEdit() {
        driver.prepareLiveCorrection()
        preferences.writeAutocorrectionMode(AutocorrectionMode.OFF); settle()
        assertCandidateMissing(R.string.candidate_correction, "hello")
        awaitCandidate(R.string.candidate_original, "helllo")
        driver.awaitFieldText(FIELD, "a helllo")
        preferences.writeAutocorrectionMode(AutocorrectionMode.SUGGESTIONS); settle()
        assertCandidateMissing(R.string.candidate_correction, "hello")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "a helll")
        driver.tapKey("o"); driver.awaitFieldText(FIELD, "a helllo")
        awaitCandidate(R.string.candidate_correction, "hello")
        space(); driver.awaitFieldText(FIELD, "a helllo ")
        noReadback()
    }

    @Test fun disablingSpellingCancelsHeldCorrectionWithoutEditorMutation() {
        val correction = driver.prepareLiveCorrection()
        val before = stats()
        val touch = driver.touchDown(correction)
        var released = false
        try {
            preferences.writeAutocorrectionMode(AutocorrectionMode.OFF); settle()
            driver.awaitFieldText(FIELD, "a helllo")
            driver.releaseTouch(touch); released = true
        } finally { if (!released) driver.cancelTouch(touch) }
        settle(); driver.awaitFieldText(FIELD, "a helllo")
        assertCandidateMissing(R.string.candidate_correction, "hello")
        assertEquals(before.getValue("compose"), stats().getValue("compose"))
        assertEquals(before.getValue("commit"), stats().getValue("commit"))
        noReadback()
    }

    @Test fun stripBothDirectionsAndRepeatedTogglesPreserveHeldKeyAndSingleRelease() {
        for (visibility in listOf(listOf(true, false), listOf(false, true), listOf(true, false, true))) {
            driver.configureSmartTyping(AutocorrectionMode.OFF, visibility.first(), mechanical = false, doubleSpace = false)
            driver.launchComposingQa(); driver.tapKey("a"); driver.awaitFieldText(FIELD, "a")
            val key = driver.keyByText("w"); val before = keyboardSnapshot()
            val touch = driver.touchDown(key); var released = false
            try {
                for (show in visibility.drop(1)) {
                    preferences.writeCandidateStrip(show); settle()
                    assertEquals("a", driver.fieldText(FIELD))
                    assertSameKeys(before, keyboardSnapshot())
                }
                driver.releaseTouch(touch); released = true
            } finally { if (!released) driver.cancelTouch(touch) }
            driver.awaitFieldText(FIELD, "aw"); settle()
            assertSameKeys(before, keyboardSnapshot())
            noReadback()
        }
    }

    @Test fun stripToggleCancelAndPrivateTransitionCannotResurrectOldCandidateContent() {
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
        driver.launchComposingQa(); driver.tapKey("a"); driver.awaitFieldText(FIELD, "a")
        val before = keyboardSnapshot(); val touch = driver.touchDown(driver.keyByText("w"))
        try {
            for (show in listOf(false, true, false)) { preferences.writeCandidateStrip(show); settle() }
            assertEquals("a", driver.fieldText(FIELD)); assertSameKeys(before, keyboardSnapshot())
        } finally { driver.cancelTouch(touch) }
        settle(); driver.awaitFieldText(FIELD, "a"); assertSameKeys(before, keyboardSnapshot())
        assertCandidateMissing(R.string.candidate_original, "a")
        preferences.writeCandidateStrip(true); settle()
        awaitCandidate(R.string.candidate_original, "a")
        val privateTouch = driver.touchDown(driver.keyByText("w"))
        try {
            preferences.writeCandidateStrip(false); settle()
            driver.launchComposingQa("private")
        } finally { driver.cancelTouch(privateTouch) }
        preferences.writeCandidateStrip(true); settle()
        assertCandidateMissing(R.string.candidate_original, "a")
        // Accessibility text may be the hint; this stat is the actual Editable length.
        assertEquals("Private editor retained text", 0, stats().getValue("length"))
        driver.tapKey("w"); driver.awaitFieldText(FIELD, "w")
        assertCandidateMissing(R.string.candidate_original, "w")
        assertEquals(0, stats().getValue("compose")); noReadback()
    }

    @Test fun spellingAndStripChangesPreserveMechanicalUndoAndIndependentDoubleSpace() {
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = true, doubleSpace = false,
            contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa()
        for (key in listOf("h", "e", "l", "l", "o")) driver.tapKey(key)
        space(); driver.tapKey(","); driver.tapKey("w"); driver.awaitFieldText(FIELD, "hello, w")
        preferences.writeAutocorrectionMode(AutocorrectionMode.HIGH_CONFIDENCE)
        preferences.writeCandidateStrip(false); settle()
        driver.awaitFieldText(FIELD, "hello, w")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello,w")
        noReadback()
        driver.configureSmartTyping(AutocorrectionMode.OFF, false, mechanical = false, doubleSpace = true,
            contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa()
        for (key in listOf("h", "e", "l", "l", "o")) driver.tapKey(key)
        driver.doubleTap(checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))))
        driver.awaitFieldText(FIELD, "hello. ")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello ")
        noReadback()
    }

    private fun settle() { instrumentation.waitForIdleSync(); driver.device.waitForIdle() }
    private fun assertSummary(title: Int, summary: Int) {
        val actual = checkNotNull(driver.settingsRow(title).findObject(By.res(ImeTestDriver.PACKAGE_NAME, "row_summary"))).text
        assertTrue("Effective settings summary missing", actual.contains(context.getString(summary)))
    }
    private fun awaitCandidate(kind: Int, text: String) = checkNotNull(driver.device.wait(
        Until.findObject(By.desc(context.getString(kind, text))), ImeTestDriver.WAIT_MILLIS)) {
        "Current public candidate unavailable"
    }
    private fun assertCandidateMissing(kind: Int, text: String) {
        assertFalse("Unexpected public candidate", driver.device.hasObject(By.desc(context.getString(kind, text))))
    }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (key, value) = it.split('='); key to value.toInt()
    }
    private fun noReadback() {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor readback counter", 0, stats().getValue(key))
    }
    private companion object { const val FIELD = "qa_composing_text" }
}
