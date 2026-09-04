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
