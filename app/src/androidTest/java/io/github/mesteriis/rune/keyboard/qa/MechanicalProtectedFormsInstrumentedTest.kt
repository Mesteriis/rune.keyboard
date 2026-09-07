package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Rect
import android.os.Build
import android.os.SystemClock
import android.view.View
import android.view.ViewGroup
import android.view.inspector.WindowInspector
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.ime.ui.AlternatesRowView
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Actual Rune key/popup gestures retain owned context across URL, email and time punctuation. */
@RunWith(AndroidJUnit4::class)
class MechanicalProtectedFormsInstrumentedTest : ImeTestBase() {
    @Test
    fun urlEmailAndTimeKeepPunctuationAndOrdinaryDeleteAcrossBinder() {
        // Switching layers inside a token discards ownership and would make exclusions vacuous.
        driver.setNumberRowThroughSettings(enabled = true)
        for (token in listOf("https://example.com/path", "name@example", "12:30")) {
            driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
            driver.launchComposingQa()
            "hello".forEach { driver.tapKey(it.toString()) }
            driver.tapKey(","); driver.tapKey("w")
            driver.awaitFieldText(FIELD, "hello, w") // Enabled mechanical positive control.
            driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext
                .getString(io.github.mesteriis.rune.keyboard.R.string.key_space))
            val prefix = "hello, w "
            driver.awaitFieldText(FIELD, prefix)
            val initial = stats()
            val keys = keyboardSnapshot()
            var typed = prefix
            for (character in token) {
                when (character) {
                    ':' -> alternate(",", ":", typed)
                    '/', '@' -> alternate(".", character.toString(), typed)
                    else -> driver.tapKey(character.toString())
                }
                typed += character
                driver.awaitFieldText(FIELD, typed)
            }
            driver.tapKey(","); driver.awaitFieldText(FIELD, "$typed,")
            val beforeLetter = stats()
            driver.tapKey("w"); driver.awaitFieldText(FIELD, "$typed,w")
            val afterLetter = stats()
            assertEquals(beforeLetter.getValue("compose") + 1, afterLetter.getValue("compose"))
            assertEquals(beforeLetter.getValue("commit"), afterLetter.getValue("commit"))
            driver.tapDelete(); driver.awaitFieldText(FIELD, "$typed,")
            driver.tapDelete(); driver.awaitFieldText(FIELD, typed)
            assertEquals(initial.getValue("connections"), stats().getValue("connections"))
            assertSameKeys(keys, keyboardSnapshot())
            for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
                assertEquals("Unexpected editor payload read", 0, stats().getValue(name))
            }
        }
    }

    private fun alternate(key: String, symbol: String, unchanged: String) {
        // The standard AVD can reserve a bottom home-gesture area without drawing a nav bar.
        // Start inside the upper part of the actual key, as the language-swipe helper does.
        val keyBounds = driver.keyByText(key).visibleBounds
        val downBounds = Rect(keyBounds).apply { bottom = minOf(bottom, top + 8) }
        var touch = driver.touchDown(downBounds)
        var released = false
        try {
            val bounds = awaitAlternateBounds(symbol)
            driver.awaitFieldText(FIELD, unchanged) // No early fallback commit while the key is held.
            check(!bounds.isEmpty) { "Alternate has no visible bounds" }
            touch = driver.moveTouch(touch, bounds.exactCenterX(), bounds.exactCenterY())
            SystemClock.sleep(32)
            driver.releaseTouch(touch)
            released = true
        } finally {
            if (!released) driver.cancelTouch(touch)
        }
        driver.device.waitForIdle()
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
    }

    private fun awaitAlternateBounds(symbol: String): Rect {
        // Non-focusable/non-touchable PopupWindows need not appear in UiAutomator's window list.
        // Inspect only Rune's actual in-process alternate row; selection still uses real MOVE/UP.
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        do {
            var result: Result<Rect?>? = null
            instrumentation.runOnMainSync {
                result = runCatching {
                    val roots = if (Build.VERSION.SDK_INT >= 29) WindowInspector.getGlobalWindowViews() else {
                        val type = Class.forName("android.view.WindowManagerGlobal")
                        val owner = type.getDeclaredMethod("getInstance").invoke(null)
                        val field = type.getDeclaredField("mViews").apply { isAccessible = true }
                        (field.get(owner) as List<*>).filterIsInstance<View>()
                    }
                    fun find(view: View): Rect? {
                        if (view is AlternatesRowView && view.isShown) {
                            for (index in 0 until view.childCount) {
                                val cell = view.getChildAt(index)
                                if (cell.contentDescription == symbol) {
                                    val location = IntArray(2)
                                    cell.getLocationOnScreen(location)
                                    return Rect(location[0], location[1], location[0] + cell.width,
                                        location[1] + cell.height).takeUnless { it.isEmpty }
                                }
                            }
                        }
                        if (view is ViewGroup) for (index in 0 until view.childCount) {
                            find(view.getChildAt(index))?.let { return it }
                        }
                        return null
                    }
                    roots.firstNotNullOfOrNull(::find)
                }
            }
            checkNotNull(result).getOrThrow()?.let { return it }
            SystemClock.sleep(20)
        } while (SystemClock.uptimeMillis() < deadline)
        error("Required actual alternate row cell is unavailable")
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('='); name to value.toInt()
    }

    private companion object { const val FIELD = "qa_composing_text" }
}
