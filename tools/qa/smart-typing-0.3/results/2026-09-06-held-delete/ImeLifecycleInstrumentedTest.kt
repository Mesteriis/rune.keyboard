package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ImeLifecycleInstrumentedTest : ImeTestBase() {
    @Test
    fun backspaceRepeatStopsAfterCancel() {
        driver.tapQaControl("qa_seed_canary")
        driver.awaitFieldText("qa_plain_text", CANARY)
        val deletions = driver.holdDeleteForActions { driver.cancelTouch(it) }
        assertTrue("Hold must delete repeatedly without emptying the fixture", deletions in 3 until CANARY.length)
        val afterCancel = CANARY.dropLast(deletions)
        driver.awaitFieldText("qa_plain_text", afterCancel)
        SystemClock.sleep(900)
        driver.awaitFieldText("qa_plain_text", afterCancel)
    }

    @Test
    fun backspaceRepeatStopsWhenImeViewDetaches() {
        driver.tapQaControl("qa_seed_canary")
        driver.awaitFieldText("qa_plain_text", CANARY)
        val deletions = driver.holdDeleteForActions { touch ->
            driver.shell("am start -W -n ${ImeTestDriver.PACKAGE_NAME}/.settings.SettingsActivity")
            driver.cancelTouch(touch)
        }
        assertTrue("Detach must follow real deletion without emptying the fixture", deletions in 3 until CANARY.length)
        val afterDetach = CANARY.dropLast(deletions)
        SystemClock.sleep(900)
        driver.device.pressBack()
        driver.focusField("qa_plain_text")
        driver.awaitFieldText("qa_plain_text", afterDetach)
        SystemClock.sleep(900)
        driver.awaitFieldText("qa_plain_text", afterDetach)
    }

    @Test
    fun ownedBackspaceRepeatsPreservePrefixAndStopOnReleaseOrCancel() {
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false,
            doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        for (release in listOf(false, true)) {
            driver.launchComposingQa()
            driver.tapKey("a")
            driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext
                .getString(R.string.key_space))
            val word = "abcdefghijklmno"
            word.forEach { driver.tapKey(it.toString()) }
            val initial = "a $word"
            driver.awaitFieldText(COMPOSING_FIELD, initial)
            awaitStats { it["start"] == 1 && it["end"] == initial.length &&
                it["selectionStart"] == initial.length && it["selectionEnd"] == initial.length }
            val before = stats()
            assertTrue(before.getValue("connections") > 0)
            assertTrue(before.getValue("compose") > 0)
            val deletions = driver.holdDeleteForActions {
                if (release) driver.releaseTouch(it) else driver.cancelTouch(it)
            }
            assertTrue("Hold must repeat and leave part of the owned word", deletions in 3 until word.length)
            val expected = initial.dropLast(deletions)
            driver.awaitFieldText(COMPOSING_FIELD, expected)
            awaitStats { it["compose"] == before.getValue("compose") + deletions &&
                it["start"] == 1 && it["end"] == expected.length &&
                it["selectionStart"] == expected.length && it["selectionEnd"] == expected.length }
            val after = stats()
            for (counter in listOf("connections", "region", "finish", "commit", "keyDown", "keyUp", "deleteKeyDown")) {
                assertEquals("Unexpected command during owned repeat: $counter", before.getValue(counter), after.getValue(counter))
            }
            noPayloadReads(after)
            SystemClock.sleep(900)
            driver.awaitFieldText(COMPOSING_FIELD, expected)
            val later = stats()
            for (counter in listOf("connections", "compose", "region", "finish", "commit", "keyDown", "keyUp",
                "deleteKeyDown", "start", "end", "selectionStart", "selectionEnd")) {
                assertEquals("Held Delete continued after its terminal event: $counter", after.getValue(counter), later.getValue(counter))
            }
            noPayloadReads(later)
        }
    }

    @Test
    fun focusLossCancelsAnArmedCharacterGesture() {
        driver.tapQaControl("qa_seed_cursor")
        val touch = driver.touchDown(driver.characterKey("a", "A"))
        driver.shell("am start -W -n ${ImeTestDriver.PACKAGE_NAME}/.settings.SettingsActivity")
        driver.cancelTouch(touch)
        driver.device.pressBack()
        SystemClock.sleep(900)
        driver.awaitFieldText("qa_plain_text", "leftright")
    }

    @Test
    fun settingsChangeAppliesToTheNextImeView() {
        driver.tapQaControl("qa_seed_cursor")
        driver.setNumberRowThroughSettings(enabled = true)
        driver.assertKeyVisible("1")
        driver.tapKey("a", "A")
        driver.revealFieldAndAwaitText("qa_email", "a")
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (key, value) = it.split('='); key to value.toInt()
    }

    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!predicate(stats()) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(25)
        assertTrue("Owned editor counters did not settle", predicate(stats()))
    }

    private fun noPayloadReads(observed: Map<String, Int>) {
        for (counter in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor payload read: $counter", 0, observed.getValue(counter))
        }
    }

    private companion object {
        const val CANARY = "RUNE_QA_CANARY_7429"
        const val COMPOSING_FIELD = "qa_composing_text"
    }
}
