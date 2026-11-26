package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import android.os.Build
import android.graphics.Rect
import android.view.View
import android.view.ViewGroup
import android.view.ViewConfiguration
import android.view.inspector.WindowInspector
import io.github.mesteriis.rune.keyboard.ime.ui.AlternatesRowView
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Run only on a disposable emulator with an enabled voice subtype. */
class VoiceInputInstrumentedTest : ImeTestBase() {
    @Test fun unavailableVoiceSubtypeIsNotOffered() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("voice_test_mode") == "unavailable")
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val manager = context.getSystemService(android.view.inputmethod.InputMethodManager::class.java)
        assertTrue("This test requires no enabled voice subtype", manager.enabledInputMethodList.none { method ->
            manager.getEnabledInputMethodSubtypeList(method, true).any { it.mode.equals("voice", true) }
        })
        val mode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            val node = mode.createAccessibilityNodeInfo()
            try { assertFalse(node.actionList.any { it.id == R.id.action_voice_input }) }
            finally { node.recycle() }
        }
    }

    @Test fun enabledVoiceSubtypeIsOfferedAndActuallySelected() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("voice_test_mode") == "enabled")
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        InstrumentationRegistry.getArguments().getString("voice_ime")?.let { expected ->
            val manager = context.getSystemService(android.view.inputmethod.InputMethodManager::class.java)
            val method = manager.enabledInputMethodList.singleOrNull { it.id == expected }
            assertNotNull("Fixture IME is not visible in Rune's enabled list", method)
            assertTrue("Fixture voice subtype is not enabled", manager.getEnabledInputMethodSubtypeList(method!!, true)
                .any { it.mode.equals("voice", true) })
        }
        val mode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            val node = mode.createAccessibilityNodeInfo()
            try {
                assertTrue("No voice action for the enabled voice IME", node.actionList.any { it.id == R.id.action_voice_input })
                assertTrue(mode.performAccessibilityAction(R.id.action_voice_input, null))
            } finally { node.recycle() }
        }
        val deadline = SystemClock.uptimeMillis() + 5_000
        var current: String
        do {
            current = driver.shell("settings get secure default_input_method")
            if (isExpectedVoice(current)) break
            SystemClock.sleep(100)
        } while (SystemClock.uptimeMillis() < deadline)
        assertTrue("Voice IME was not selected", isExpectedVoice(current))
    }
    @Test fun nextKeyboardPopupOpensSystemPickerOnApi26() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("voice_test_mode") == "next_picker")
        require(Build.VERSION.SDK_INT == 26)
        val touch = driver.touchDown(driver.keyByText("?123"))
        var currentTouch = touch
        var released = false
        try {
            SystemClock.sleep(ViewConfiguration.getLongPressTimeout().toLong() + 300)
            val target = awaitAlternateBounds("Next keyboard")
            currentTouch = driver.moveTouch(currentTouch, target.exactCenterX(), target.exactCenterY())
            SystemClock.sleep(50)
            driver.releaseTouch(currentTouch)
            released = true
            assertTrue("Rune entry missing from system chooser", driver.device.wait(
                Until.hasObject(By.text("Rune Keyboard")), 5_000))
            assertNotNull("Other IME entry missing from system chooser", driver.device.findObject(By.text("Gboard")))
        } finally {
            if (!released) driver.cancelTouch(currentTouch)
            driver.device.pressBack()
        }
    }

    @Test fun nextKeyboardPopupSwitchesOrShowsPicker() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("voice_test_mode") == "next_switch")
        require(Build.VERSION.SDK_INT >= 28)
        val original = driver.shell("settings get secure default_input_method")
        val touch = driver.touchDown(driver.keyByText("?123"))
        var currentTouch = touch
        var released = false
        try {
            SystemClock.sleep(ViewConfiguration.getLongPressTimeout().toLong() + 300)
            val target = awaitAlternateBounds("Next keyboard")
            currentTouch = driver.moveTouch(currentTouch, target.exactCenterX(), target.exactCenterY())
            SystemClock.sleep(50)
            driver.releaseTouch(currentTouch)
            released = true
            val deadline = SystemClock.uptimeMillis() + 5_000
            var switched = false
            var picker = false
            do {
                val current = driver.shell("settings get secure default_input_method")
                switched = current.isNotBlank() && current != original
                picker = driver.device.findObject(By.text("Rune Keyboard")) != null &&
                    driver.device.findObject(By.text("Gboard")) != null
                if (switched || picker) break
                SystemClock.sleep(100)
            } while (SystemClock.uptimeMillis() < deadline)
            assertTrue("Next-keyboard popup neither switched IME nor showed the picker", switched || picker)
            println("U15_NEXT_RESULT=" + if (switched) "SWITCHED" else "PICKER")
            if (picker) driver.device.pressBack()
        } finally { if (!released) driver.cancelTouch(currentTouch) }
    }

    @Test fun voicePopupGestureSwitchesTheIme() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("voice_test_mode") == "gesture")
        val touch = driver.touchDown(driver.keyByText("?123"))
        var currentTouch = touch
        var released = false
        try {
            SystemClock.sleep(ViewConfiguration.getLongPressTimeout().toLong() + 300)
            val target = awaitAlternateBounds("Voice input")
            currentTouch = driver.moveTouch(currentTouch, target.exactCenterX(), target.exactCenterY())
            SystemClock.sleep(50)
            driver.releaseTouch(currentTouch)
            released = true
        } finally { if (!released) driver.cancelTouch(currentTouch) }
        val deadline = SystemClock.uptimeMillis() + 5_000
        var current: String
        do {
            current = driver.shell("settings get secure default_input_method")
            if (isExpectedVoice(current)) break
            SystemClock.sleep(100)
        } while (SystemClock.uptimeMillis() < deadline)
        assertTrue("Voice popup gesture did not switch the IME", isExpectedVoice(current))
    }

    @Test fun voiceDisabledAfterKeyboardShownFallsBackToPicker() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("voice_test_mode") == "stale")
        val component = checkNotNull(InstrumentationRegistry.getArguments().getString("voice_ime"))
        require(component.matches(Regex("[A-Za-z0-9_.]+/[A-Za-z0-9_.]+")))
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val mode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            val node = mode.createAccessibilityNodeInfo()
            try { assertTrue(node.actionList.any { it.id == R.id.action_voice_input }) }
            finally { node.recycle() }
        }
        try {
            assertTrue(driver.shell("ime disable $component").contains("disabled"))
            instrumentation.runOnMainSync { assertTrue(mode.performAccessibilityAction(R.id.action_voice_input, null)) }
            assertTrue("Rune entry missing from system chooser", driver.device.wait(
                Until.hasObject(By.text("Rune Keyboard")), 5_000))
            assertNotNull("Other IME entry missing from system chooser", driver.device.findObject(By.text("Gboard")))
        } finally {
            driver.device.pressBack()
            driver.shell("ime enable $component")
        }
    }

    private fun isExpectedVoice(component: String): Boolean {
        val expected = InstrumentationRegistry.getArguments().getString("voice_ime")
        return if (expected == null) component.contains("VoiceInputMethodService") else component.trim() == expected
    }

    private fun awaitAlternateBounds(description: String): Rect {
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
                                if (cell.contentDescription == description) {
                                    val location = IntArray(2)
                                    cell.getLocationOnScreen(location)
                                    return Rect(location[0], location[1], location[0] + cell.width, location[1] + cell.height)
                                }
                            }
                        }
                        if (view is ViewGroup) for (index in 0 until view.childCount) find(view.getChildAt(index))?.let { return it }
                        return null
                    }
                    roots.firstNotNullOfOrNull(::find)
                }
            }
            checkNotNull(result).getOrThrow()?.let { return it }
            SystemClock.sleep(20)
        } while (SystemClock.uptimeMillis() < deadline)
        error("Voice alternate is not visible")
    }

}
