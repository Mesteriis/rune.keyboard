package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Public fixture only; observations cross the existing :qa_editor Binder connection. */
@RunWith(AndroidJUnit4::class)
class LiveCandidatesInstrumentedTest : ImeTestBase() {
    @Test fun shortRussianCorrectionPreviewAndUndoPreserveTheNextWord() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, android.content.Context.MODE_PRIVATE)
            .edit().putBoolean(io.github.mesteriis.rune.keyboard.settings.SettingsCodec.KEY_VISIBLE_UNDO, true).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        "зочу".forEach { driver.tapKey(it.toString()) }
        val preview = awaitCandidate(R.string.candidate_correction, "хочу")
        assertEquals(InstrumentationRegistry.getInstrumentation().targetContext
            .getString(R.string.candidate_auto_preview_label, "хочу"), preview.text)
        space()
        driver.awaitFieldText(FIELD, "хочу ")
        "до".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "хочу до")
        awaitCandidate(R.string.candidate_undo, "зочу").click()
        driver.awaitFieldText(FIELD, "зочу до")
        noReadback()
    }

    @Test fun jointShortWordCorrectionPreviewAndUndoPreserveTheNextWord() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, android.content.Context.MODE_PRIVATE)
            .edit().putBoolean(io.github.mesteriis.rune.keyboard.settings.SettingsCodec.KEY_VISIBLE_UNDO, true).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        "ссын".forEach { driver.tapKey(it.toString()) }
        val preview = awaitCandidate(R.string.candidate_correction, "сын")
        assertEquals(InstrumentationRegistry.getInstrumentation().targetContext
            .getString(R.string.candidate_auto_preview_label, "сын"), preview.text)
        space()
        driver.awaitFieldText(FIELD, "сын ")
        "до".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "сын до")
        awaitCandidate(R.string.candidate_undo, "ссын").click()
        driver.awaitFieldText(FIELD, "ссын до")
        noReadback()
    }

    @Test fun reportedRussianMisspellingsCorrectOnSpaceWhileAmbiguousFragmentStaysUntouched() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)

        fun type(word: String) {
            word.forEach { driver.tapKey(it.toString()) }
            space()
        }

        type("смотруть")
        driver.awaitFieldText(FIELD, "смотреть ")
        type("ощющениям")
        driver.awaitFieldText(FIELD, "смотреть ощущениям ")
        type("заберай")
        driver.awaitFieldText(FIELD, "смотреть ощущениям забирай ")
        type("пвременить")
        driver.awaitFieldText(FIELD, "смотреть ощущениям забирай повременить ")
        type("ерминатор")
        driver.awaitFieldText(FIELD, "смотреть ощущениям забирай повременить терминатор ")
        type("спаателей")
        driver.awaitFieldText(FIELD,
            "смотреть ощущениям забирай повременить терминатор спасателей ")
        type("ность")
        driver.awaitFieldText(FIELD,
            "смотреть ощущениям забирай повременить терминатор спасателей ность ")
        noReadback()
    }

    @Test fun canonicalCaseAutoReplacesOnBoundaryAndBackspaceRestoresOriginal() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        driver.switchToRussian()
        driver.tapKey("Я", "я")
        space()
        for (key in listOf("м", "о", "с", "к", "в")) driver.tapKey(key)
        val deadline = SystemClock.uptimeMillis() + 120_000L
        var canonical: UiObject2? = null
        do {
            driver.tapKey("а")
            driver.awaitFieldText(FIELD, "я москва")
            canonical = driver.device.wait(Until.findObject(By.desc(
                description(R.string.candidate_correction, "Москва"))), 2_000L)
            if (canonical == null) {
                driver.tapDelete()
                driver.awaitFieldText(FIELD, "я москв")
            }
        } while (canonical == null && SystemClock.uptimeMillis() < deadline)
        assertTrue("Canonical case candidate unavailable", checkNotNull(canonical).isSelected)

        space()
        driver.awaitFieldText(FIELD, "я Москва ")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "я москва")
        assertTrue(awaitCandidate(R.string.candidate_original, "москва").isSelected)
        val restored = stats()
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "я москв")
        awaitStats { it.getValue("compose") == restored.getValue("compose") + 1 }
        val deleted = stats()
        for (counter in listOf("commit", "region", "finish")) {
            assertEquals(restored.getValue(counter), deleted.getValue(counter))
        }
        assertEquals(restored.getValue("start"), deleted.getValue("start"))
        assertEquals(7, deleted.getValue("end"))
        assertEquals(7, deleted.getValue("selectionStart"))
        assertEquals(7, deleted.getValue("selectionEnd"))
        noReadback()
    }

    @Test fun russianSentencePeriodCorrectsReadyWordAndBackspaceRestoresExactSource() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        for (key in listOf("с", "м", "о", "т", "р", "у", "т", "ь")) driver.tapKey(key)

        val deadline = SystemClock.uptimeMillis() + 120_000L
        var correction: UiObject2? = null
        do {
            correction = driver.device.wait(Until.findObject(By.desc(
                description(R.string.candidate_correction, "смотреть"))), 2_000L)
            if (correction == null) {
                driver.tapDelete()
                driver.awaitFieldText(FIELD, "смотрут")
                driver.tapKey("ь")
                driver.awaitFieldText(FIELD, "смотруть")
            }
        } while (correction == null && SystemClock.uptimeMillis() < deadline)
        assertTrue("Russian correction unavailable", correction != null)

        driver.tapKey(".")
        driver.awaitFieldText(FIELD, "смотреть.")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "смотруть")
        assertTrue(awaitCandidate(R.string.candidate_original, "смотруть").isSelected)
        noReadback()
    }

    @Test fun correctionAndOriginalTapsReplaceOnlyOwnedWordWithNoReadback() {
        val correction = prepareCorrection()
        val before = stats()
        correction.click()
        driver.awaitFieldText(FIELD, "a hello")
        awaitStats { it.getValue("compose") == before.getValue("compose") + 1 }
        assertEquals(before.getValue("commit"), stats().getValue("commit"))
        val original = awaitCandidate(R.string.candidate_original, "helllo")
        val corrected = stats()
        original.click()
        driver.awaitFieldText(FIELD, "a helllo")
        awaitStats { it.getValue("compose") == corrected.getValue("compose") + 1 }
        assertTrue(awaitCandidate(R.string.candidate_original, "helllo").isSelected)
        assertEquals(corrected.getValue("commit"), stats().getValue("commit"))
        noReadback()
    }

    @Test fun boundaryKeepsTypedOriginalAndDropsPreviousSuggestions() {
        prepareCorrection()
        space()
        driver.awaitFieldText(FIELD, "a helllo ")
        driver.device.waitForIdle()
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_correction, "hello"))))
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_original, "helllo"))))
        noReadback()
    }

    @Test fun sensitiveEditorTransitionClearsLoadedSuggestionsAndPreservesPlainTyping() {
        prepareCorrection()
        driver.launchComposingQa("private")
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_correction, "hello"))))
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_original, "helllo"))))
        driver.tapKey("a")
        driver.awaitFieldText(FIELD, "a")
        assertEquals(0, stats().getValue("compose"))
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_original, "a"))))
        noReadback()
    }

    private fun prepareCorrection(): UiObject2 = driver.prepareLiveCorrection()

    private fun noReadback() {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor readback counter", 0, stats().getValue(key))
        }
    }

    private fun space() = driver.tapKeyByDescription(
        InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space),
    )

    private fun description(resource: Int, word: String): String =
        InstrumentationRegistry.getInstrumentation().targetContext.getString(resource, word)

    private fun awaitCandidate(resource: Int, word: String): UiObject2 = checkNotNull(
        driver.device.wait(Until.findObject(By.desc(description(resource, word))), ImeTestDriver.WAIT_MILLIS),
    ) { "Expected current candidate unavailable" }

    private fun stats(): Map<String, Int> = checkNotNull(
        driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats")),
    ).text.orEmpty().split(' ').associate { value ->
        val (key, number) = value.split('=')
        key to number.toInt()
    }

    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!predicate(stats()) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(25)
        assertTrue("Editor command counters did not settle", predicate(stats()))
    }

    private companion object {
        const val FIELD = "qa_composing_text"
    }
}
