package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import android.view.ViewConfiguration
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Assertions observe the real :qa_editor InputConnection, never controller internals. */
@RunWith(AndroidJUnit4::class)
class SmartTypingComposingInstrumentedTest : ImeTestBase() {
    @Test
    fun currentOriginalStripTapDoesNotWriteEditorAndUpdatesWithTheWord() {
        driver.launchComposingQa()
        type("a", "b")
        driver.awaitFieldText(FIELD, "ab")
        val resources = InstrumentationRegistry.getInstrumentation().targetContext
        val original = awaitOriginal("ab")
        val before = stats()
        original.click()
        driver.device.waitForIdle()
        driver.awaitFieldText(FIELD, "ab")
        assertTrue(awaitOriginal("ab").isSelected)
        assertEquals(before.getValue("compose"), stats().getValue("compose"))
        assertEquals(before.getValue("commit"), stats().getValue("commit"))
        type("c")
        driver.awaitFieldText(FIELD, "abc")
        assertTrue(driver.device.hasObject(By.desc(resources.getString(R.string.candidate_original, "abc"))))
    }

    @Test
    fun changingToSensitiveEditorRemovesThePreviousOriginalFromTheStrip() {
        driver.launchComposingQa()
        type("a", "b")
        driver.awaitFieldText(FIELD, "ab")
        val resources = InstrumentationRegistry.getInstrumentation().targetContext
        val description = resources.getString(R.string.candidate_original, "ab")
        awaitOriginal("ab")
        driver.launchComposingQa("private")
        assertTrue(!driver.device.hasObject(By.desc(description)))
        type("c")
        driver.awaitFieldText(FIELD, "c")
        assertEquals(0, stats().getValue("compose"))
        assertTrue(!driver.device.hasObject(By.desc(resources.getString(R.string.candidate_original, "c"))))
    }

    @Test
    fun wordAndLeadingBoundaryComposeAndDeleteWithoutReplayingCommittedText() {
        driver.launchComposingQa()
        type("a", "b")
        driver.awaitFieldText(FIELD, "ab")
        awaitStats { it["compose"] == 2 && it["start"] == 0 && it["end"] == 2 }

        space()
        driver.awaitFieldText(FIELD, "ab ")
        awaitStats { it.getValue("finish") >= 1 && it["start"] == 2 && it["end"] == 3 }
        type("c")
        driver.awaitFieldText(FIELD, "ab c")
        awaitStats { it["start"] == 2 && it["end"] == 4 }

        driver.tapDelete()
        driver.awaitFieldText(FIELD, "ab ")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "ab")
        // Deleting Rune's own space reopens the whole previous word without editor readback.
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        type("d")
        driver.awaitFieldText(FIELD, "abd")
        awaitStats { it["start"] == 0 && it["end"] == 3 }
        awaitOriginal("abd")
    }

    @Test
    fun editorRewriteInvalidatesOwnedTextWithoutReplay() {
        driver.launchComposingQa()
        type("a", "b")
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        val composingCalls = stats().getValue("compose")
        val connections = stats().getValue("connections")
        driver.tapQaControl("qa_composing_rewrite")
        driver.awaitFieldText(FIELD, "editor")
        assertEquals("Rewrite must stay on the same InputConnection", connections, stats().getValue("connections"))
        type("c")
        driver.awaitFieldText(FIELD, "editorc")
        assertEquals(composingCalls, stats().getValue("compose"))
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "editor")
    }

    @Test
    fun cursorMovementAndSelectionFinishTheOldSpan() {
        driver.launchComposingQa()
        type("a", "b")
        driver.tapQaControl("qa_composing_cursor")
        awaitStats { it["selectionStart"] == 0 && it["start"] == -1 }
        type("x")
        driver.awaitFieldText(FIELD, "xab")
        driver.tapQaControl("qa_composing_select")
        awaitStats { it["selectionStart"] == 0 && it["selectionEnd"] == 3 && it["start"] == -1 }
        type("c")
        driver.awaitFieldText(FIELD, "c")
    }

    @Test
    fun droppedOwnedSpanWithCallbackDisablesCompositionForTheSession() {
        driver.launchComposingQa()
        type("a", "b")
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        val composingCalls = stats().getValue("compose")
        driver.tapQaControl("qa_composing_drop")
        awaitStats { it["callbacks"] == 1 && it["start"] == -1 }
        type("c", "d")
        driver.awaitFieldText(FIELD, "abcd")
        assertEquals(composingCalls, stats().getValue("compose"))
    }

    @Test
    fun rejectedSpanWithExplicitCallbackContinuesAsPlainText() = unsupportedSpan("reject")

    @Test
    fun droppedSpanWithExplicitCallbackContinuesAsPlainText() = unsupportedSpan("drop")

    private fun unsupportedSpan(mode: String) {
        driver.launchComposingQa(mode)
        type("a")
        driver.awaitFieldText(FIELD, "a")
        awaitStats { it["compose"] == 1 && it.getValue("callbacks") >= 1 && it["start"] == -1 }
        // The remote false result alone is not observable through Android's one-way Binder.
        // Give the explicit missing-span callback the same settle window as editor controls.
        SystemClock.sleep(ImeTestDriver.INPUT_CONNECTION_SETTLE_MILLIS)
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        type("b", "c")
        driver.awaitFieldText(FIELD, "abc")
        assertEquals(1, stats().getValue("compose"))
        assertTrue(stats().getValue("commit") >= 2)
    }

    @Test
    fun languageSwitchPreservesTextAndFinishesComposition() {
        driver.launchComposingQa()
        type("a", "b")
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        driver.switchToRussian()
        driver.awaitFieldText(FIELD, "ab")
        awaitStats { it["start"] == -1 && it["end"] == -1 }
        type("я")
        driver.awaitFieldText(FIELD, "abя")
    }

    @Test
    fun stationarySpaceHoldFinishesCompositionBeforeAnyCursorStep() {
        driver.launchComposingQa()
        type("a", "b")
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        val finishCalls = stats().getValue("finish")
        val description = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space)
        val key = checkNotNull(driver.device.findObject(By.desc(description)))
        val touch = driver.touchDown(key)
        try {
            SystemClock.sleep(ViewConfiguration.getLongPressTimeout().toLong() + 150)
            // No ACTION_MOVE has been injected. Cursor mode entry itself must release the span.
            awaitStats {
                it["start"] == -1 && it["end"] == -1 &&
                    it.getValue("finish") > finishCalls &&
                    it["selectionStart"] == 2 && it["selectionEnd"] == 2
            }
            driver.awaitFieldText(FIELD, "ab")
        } finally {
            driver.releaseTouch(touch)
        }
        driver.device.waitForIdle()
        driver.awaitFieldText(FIELD, "ab")
    }

    @Test
    fun restartInputDoesNotReplaceOrDuplicateThePriorComposition() {
        driver.launchComposingQa()
        type("a", "b")
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        val connections = stats().getValue("connections")
        driver.tapQaControl("qa_composing_restart")
        awaitStats { it.getValue("connections") > connections }
        driver.awaitFieldText(FIELD, "ab")
        type("c")
        driver.awaitFieldText(FIELD, "abc")
    }

    @Test
    fun inputViewDetachDoesNotReplayThePriorComposition() {
        driver.launchComposingQa()
        type("a", "b")
        awaitStats { it["start"] == 0 && it["end"] == 2 }
        driver.shell("am start -W -n ${ImeTestDriver.PACKAGE_NAME}/.settings.SettingsActivity")
        driver.device.pressBack()
        driver.focusField(FIELD)
        driver.awaitFieldText(FIELD, "ab")
        type("c")
        driver.awaitFieldText(FIELD, "abc")
    }

    @Test
    fun doubleSpaceUndoSurvivesBinderSelectionAcknowledgement() {
        driver.configureMechanicalPunctuation(mechanical = false, doubleSpace = true)
        driver.launchComposingQa()
        type("a")
        doubleTapSpace()
        driver.awaitFieldText(FIELD, "a. ")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "a ")
        type("b")
        driver.awaitFieldText(FIELD, "a b")
        assertEquals(0, stats().getValue("before"))
    }

    @Test
    fun doubleSpaceWithoutOwnedWordKeepsBothSpacesAndDoesNotReadEditor() {
        driver.configureMechanicalPunctuation(mechanical = false, doubleSpace = true)
        driver.launchComposingQa()
        doubleTapSpace()
        driver.awaitFieldText(FIELD, "  ")
        type("a")
        driver.awaitFieldText(FIELD, "  a")
        assertEquals(0, stats().getValue("before"))
    }

    @Test
    fun noPersonalizedLearningNeverReadsEditorTextOrSetsComposition() {
        driver.launchComposingQa("private")
        type("a", "b")
        space()
        type("c")
        driver.awaitFieldText(FIELD, "ab c")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "ab ")
        driver.tapQaControl("qa_composing_cursor")
        type("x")
        driver.awaitFieldText(FIELD, "xab ")
        val observed = stats()
        assertTrue("Connection wrapper did not observe plain commits", observed.getValue("commit") >= 5)
        listOf(
            "before", "after", "selected", "extracted", "caps", "surrounding", "snapshot",
            "compose", "region",
        ).forEach { counter ->
            assertEquals("Sensitive editor unexpectedly called $counter", 0, observed.getValue(counter))
        }
    }

    private fun doubleTapSpace() {
        val description = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space)
        val key = checkNotNull(driver.device.findObject(By.desc(description)))
        val releaseIntervalMillis = driver.doubleTap(key)
        assertTrue(
            "Double-space gesture injection stalled: release interval ${releaseIntervalMillis}ms " +
                "exceeds ${DOUBLE_SPACE_TAP_WINDOW_MILLIS}ms",
            releaseIntervalMillis in 0..DOUBLE_SPACE_TAP_WINDOW_MILLIS,
        )
        driver.device.waitForIdle()
    }

    private fun awaitOriginal(word: String): UiObject2 {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val description = context.getString(R.string.candidate_original, word)
        return checkNotNull(driver.device.wait(Until.findObject(By.desc(description)), 5_000)) {
            "Original candidate did not appear after acknowledged typing"
        }
    }

    private fun type(vararg keys: String) = keys.forEach { driver.tapKey(it) }

    private fun space() = driver.tapKeyByDescription(
        InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space),
    )

    private fun stats(): Map<String, Int> {
        val node = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))) {
            "Composing stats must remain visible; reading them must not hide the IME"
        }
        return node.text.orEmpty().split(' ').associate { value ->
            val (key, number) = value.split('=')
            key to number.toInt()
        }
    }

    private fun awaitStats(condition: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        do {
            val observed = stats()
            if (condition(observed)) return
            SystemClock.sleep(50)
        } while (SystemClock.uptimeMillis() < deadline)
        assertTrue("Editor stats did not reach expected state: ${stats()}", condition(stats()))
    }

    private companion object {
        const val FIELD = "qa_composing_text"
        // Matches the production SpaceKeyView gesture window; never widen it for slow test hosts.
        const val DOUBLE_SPACE_TAP_WINDOW_MILLIS = 400L
    }
}
