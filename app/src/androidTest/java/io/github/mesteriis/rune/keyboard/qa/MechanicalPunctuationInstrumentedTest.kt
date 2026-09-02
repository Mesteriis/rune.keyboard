package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.os.SystemClock
import android.view.View
import android.view.ViewGroup
import android.view.inspector.WindowInspector
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.ui.CancelableKey
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Public fixtures over the real :qa_editor Binder connection; no model or lexicon readiness. */
@RunWith(AndroidJUnit4::class)
class MechanicalPunctuationInstrumentedTest : ImeTestBase() {
    @Test fun commaPopupPunctuationCapsAndImmediateUndoNeverReplayOldWord() {
        prepare()
        word("hello"); space()
        driver.selectFirstAlternate(",") {
            // A failed popup would use performLongClick and commit early. Require release ownership.
            assertEquals("hello ", driver.fieldText(FIELD))
        }
        driver.awaitFieldText(FIELD, "hello?")
        val before = stats()
        driver.tapKey("w")
        driver.awaitFieldText(FIELD, "hello? W")
        awaitStats { it.getValue("compose") == before.getValue("compose") + 1 }
        assertEquals(before.getValue("compose") + 1, stats().getValue("compose"))
        assertEquals(before.getValue("commit"), stats().getValue("commit"))
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello?w")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello?")
        noReadback()
    }

    @Test fun pairOfDotsWaitsForWhitespaceAndNewWordThenUndoesCapsTogether() {
        prepare()
        word("hello"); driver.tapKey("."); driver.tapKey(".")
        driver.awaitFieldText(FIELD, "hello..")
        space(); space(); driver.awaitFieldText(FIELD, "hello..  ")
        driver.tapKey("w")
        driver.awaitFieldText(FIELD, "hello. W")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello..  w")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello..  ")
        driver.tapKey("."); driver.awaitFieldText(FIELD, "hello..  .")
        noReadback()
    }

    @Test fun cachedMechanicalTogglePreservesHeldKeyInstancesAndNextInputUndo() {
        prepare(mechanical = false)
        word("hello"); space(); driver.tapKey(",")
        driver.awaitFieldText(FIELD, "hello ,")
        val key = driver.keyByText("w")
        val before = keyboardSnapshot()
        val touch = driver.touchDown(key)
        var released = false
        try {
            driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
            assertEquals("hello ,", driver.fieldText(FIELD))
            assertSameKeys(before, keyboardSnapshot())
            driver.releaseTouch(touch)
            released = true
        } finally {
            if (!released) driver.cancelTouch(touch)
        }
        driver.awaitFieldText(FIELD, "hello, w")
        // Drain ACTION_UP's deferred key render and posted caps refresh before comparing again.
        driver.device.waitForIdle()
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        assertSameKeys(before, keyboardSnapshot())
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello ,w")
        noReadback()
    }

    /** Test-local references only; inspect our in-process IME tree, never external windows/text. */
    private fun keyboardSnapshot(): KeyboardSnapshot {
        var result: Result<KeyboardSnapshot>? = null
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            // Propagate inspection/assertion failures on the test thread, not the app main thread.
            result = runCatching {
                val roots = if (Build.VERSION.SDK_INT >= 29) {
                    WindowInspector.getGlobalWindowViews()
                } else {
                    // Legacy test-only inspection; public WindowInspector is available from API29.
                    val type = Class.forName("android.view.WindowManagerGlobal")
                    val owner = type.getDeclaredMethod("getInstance").invoke(null)
                    val field = type.getDeclaredField("mViews").apply { isAccessible = true }
                    (field.get(owner) as List<*>).map { it as View }
                }
                val keyboards = mutableListOf<RuneKeyboardView>()
                fun findKeyboard(view: View) {
                    if (view is RuneKeyboardView) {
                        if (view.isShown) keyboards.add(view)
                    } else if (view is ViewGroup) {
                        for (index in 0 until view.childCount) findKeyboard(view.getChildAt(index))
                    }
                }
                roots.forEach(::findKeyboard)
                assertEquals("Expected one visible in-process Rune keyboard", 1, keyboards.size)
                val keyboard = keyboards.single()
                val keys = mutableListOf<View>()
                fun collectKeys(view: View) {
                    if (view is CancelableKey) keys.add(view)
                    if (view is ViewGroup) {
                        for (index in 0 until view.childCount) collectKeys(view.getChildAt(index))
                    }
                }
                collectKeys(keyboard)
                assertTrue("Expected actual Rune key instances", keys.isNotEmpty())
                KeyboardSnapshot(keyboard, keys)
            }
        }
        return checkNotNull(result) { "Keyboard inspection did not complete" }.getOrThrow()
    }

    private fun assertSameKeys(expected: KeyboardSnapshot, actual: KeyboardSnapshot) {
        // assertSame would format View.toString on failure; report no view/text payloads.
        assertTrue("Keyboard instance changed", expected.keyboard === actual.keyboard)
        assertEquals("Key instance count changed", expected.keys.size, actual.keys.size)
        expected.keys.indices.forEach { index ->
            assertTrue("Key instance changed at index $index", expected.keys[index] === actual.keys[index])
        }
    }

    private class KeyboardSnapshot(val keyboard: RuneKeyboardView, val keys: List<View>)

    private fun prepare(mechanical: Boolean = true) {
        driver.configureMechanicalPunctuation(mechanical, doubleSpace = false)
        driver.launchComposingQa()
    }

    private fun word(value: String) { value.forEach { driver.tapKey(it.toString()) } }
    private fun space() = driver.tapKeyByDescription(
        InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (key, value) = it.split('='); key to value.toInt()
    }
    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!predicate(stats()) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(25)
        assertTrue("Editor command counters did not settle", predicate(stats()))
    }
    private fun noReadback() {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor readback counter", 0, stats().getValue(key))
        }
    }
    private companion object { const val FIELD = "qa_composing_text" }
}
