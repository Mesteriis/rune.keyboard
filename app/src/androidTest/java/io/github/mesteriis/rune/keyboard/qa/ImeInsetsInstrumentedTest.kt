package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Rect
import android.os.Build
import android.os.SystemClock
import android.view.View
import android.view.Surface
import android.view.WindowInsets
import android.view.WindowManager
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import org.junit.Assert.*
import org.junit.Test

class ImeInsetsInstrumentedTest : ImeTestBase() {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()

    @Test
    fun bottomRowStaysAboveNavigationAndClickableAfterReopenAndRotation() {
        driver.tapQaControl("qa_seed_cursor")
        var text = assertBottomRowSafeAndTapSpace("leftright")
        driver.device.pressBack()
        assertTrue(driver.device.wait(Until.gone(By.desc(
            instrumentation.targetContext.getString(R.string.key_delete))), ImeTestDriver.WAIT_MILLIS))
        // Directly reopen the same editor; no driver fallback may rebind the service here.
        checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_plain_text"))).click()
        awaitKeyboard()
        text = assertBottomRowSafeAndTapSpace(text)
        val beforeRotation = keyboardSnapshot().keyboard
        val startingRotation = driver.device.displayRotation
        val targetRotation = if (startingRotation == Surface.ROTATION_0 ||
            startingRotation == Surface.ROTATION_180) Surface.ROTATION_90 else Surface.ROTATION_0
        try {
            // Change orientation even if this test starts on an already-rotated emulator.
            if (targetRotation == Surface.ROTATION_90) driver.device.setOrientationLeft()
            else driver.device.setOrientationNatural()
            awaitKeyboard()
            assertEquals("Display must reach the different target rotation", targetRotation,
                driver.device.displayRotation)
            awaitTransition(beforeRotation)
            assertBottomRowSafeAndTapSpace(text)
        } finally {
            driver.device.setOrientationNatural()
            driver.device.unfreezeRotation()
        }
    }

    private fun awaitKeyboard() {
        assertTrue("Keyboard must return without refocus/rebind", driver.device.wait(Until.hasObject(
            By.desc(instrumentation.targetContext.getString(R.string.key_delete))), ImeTestDriver.WAIT_MILLIS))
        driver.device.waitForIdle()
        instrumentation.waitForIdleSync()
    }

    private fun awaitTransition(previous: View) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (keyboardSnapshot().keyboard === previous && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(25)
        }
        assertTrue("Configuration must recreate the input view", keyboardSnapshot().keyboard !== previous)
    }

    @Suppress("DEPRECATION")
    private fun assertBottomRowSafeAndTapSpace(before: String): String {
        val snapshot = keyboardSnapshot()
        val spaceDescription = instrumentation.targetContext.getString(R.string.key_space)
        var spaceKey: View? = null
        val bottomKeys = mutableListOf<View>()
        onMain {
            val root = snapshot.keyboard
            val insets = checkNotNull(root.rootWindowInsets)
            val safe = if (Build.VERSION.SDK_INT >= 30) {
                val value = insets.getInsetsIgnoringVisibility(
                    WindowInsets.Type.navigationBars() or WindowInsets.Type.displayCutout() or
                        WindowInsets.Type.captionBar())
                Rect(value.left, 0, value.right, value.bottom)
            } else {
                Rect(maxOf(insets.stableInsetLeft, insets.systemWindowInsetLeft), 0,
                    maxOf(insets.stableInsetRight, insets.systemWindowInsetRight),
                    maxOf(insets.stableInsetBottom, insets.systemWindowInsetBottom))
            }
            val base = root.resources.getDimensionPixelSize(R.dimen.keyboard_padding)
            val display = android.graphics.Point()
            root.display.getRealSize(display)
            if (Build.VERSION.SDK_INT >= 30) {
                // Window metrics retain system exclusions consumed by a framework parent before
                // rootWindowInsets is delivered. Merge overlapping sources per edge, not by sum.
                val metrics = root.context.getSystemService(WindowManager::class.java).currentWindowMetrics
                val windowSafe = metrics.windowInsets.getInsetsIgnoringVisibility(
                    WindowInsets.Type.navigationBars() or WindowInsets.Type.displayCutout() or
                        WindowInsets.Type.captionBar())
                safe.left = maxOf(safe.left, windowSafe.left)
                safe.right = maxOf(safe.right, windowSafe.right)
                safe.bottom = maxOf(safe.bottom, windowSafe.bottom)
            }
            if (Build.VERSION.SDK_INT >= 29) {
                // A framework parent may already exclude a landscape display cutout as well.
                root.display.cutout?.let { cutout ->
                    safe.left = maxOf(safe.left, cutout.safeInsetLeft)
                    safe.right = maxOf(safe.right, cutout.safeInsetRight)
                    safe.bottom = maxOf(safe.bottom, cutout.safeInsetBottom)
                }
            }
            if (Build.VERSION.SDK_INT < 30) {
                // Legacy landscape IME windows can be sized to the usable display and report
                // zero root insets. Display's usable area independently excludes that side bar.
                val usable = android.graphics.Point()
                root.display.getSize(usable)
                safe.bottom = maxOf(safe.bottom, display.y - usable.y)
                if (root.display.rotation == Surface.ROTATION_270) {
                    safe.left = maxOf(safe.left, display.x - usable.x)
                } else {
                    safe.right = maxOf(safe.right, display.x - usable.x)
                }
            }
            assertTrue("Fixture must have a navigation exclusion",
                safe.bottom > 0 || safe.left > 0 || safe.right > 0)
            val rootPosition = IntArray(2)
            root.getLocationOnScreen(rootPosition)
            // The framework parent can consume the bar before dispatching to Rune. Measure
            // total exclusion on screen so both missing clearance and double padding fail.
            assertEquals(base + safe.bottom,
                display.y - rootPosition[1] - root.height + root.paddingBottom)
            assertEquals(base + safe.left, rootPosition[0] + root.paddingLeft)
            assertEquals(base + safe.right,
                display.x - rootPosition[0] - root.width + root.paddingRight)
            val keys = snapshot.keys.filter { it.visibility == View.VISIBLE }.map { key ->
                val position = IntArray(2)
                key.getLocationOnScreen(position)
                key to Rect(position[0], position[1], position[0] + key.width, position[1] + key.height)
            }
            val bottom = keys.maxOf { it.second.bottom }
            for ((key, bounds) in keys.filter { it.second.bottom == bottom }) {
                bottomKeys.add(key)
                assertTrue("Bottom key overlaps navigation area", bounds.bottom <= display.y - safe.bottom)
                assertTrue("Bottom key overlaps left exclusion", bounds.left >= safe.left)
                assertTrue("Bottom key overlaps right exclusion", bounds.right <= display.x - safe.right)
                val visible = Rect()
                assertTrue("Bottom key must be fully visible", key.getGlobalVisibleRect(visible))
                assertEquals(bounds.width(), visible.width())
                assertEquals(bounds.height(), visible.height())
                if (key.contentDescription == spaceDescription) spaceKey = key
            }
        }
        // Observe the real view's public action boundary for every bottom key. Restore the
        // service listener before the final Space, whose edit is checked in the remote editor.
        val listener = snapshot.keyboard.javaClass.getDeclaredField("actionListener").apply { isAccessible = true }
        var original: ((KeyboardAction) -> Unit)? = null
        val actions = mutableListOf<KeyboardAction>()
        onMain {
            @Suppress("UNCHECKED_CAST")
            original = listener.get(snapshot.keyboard) as (KeyboardAction) -> Unit
            snapshot.keyboard.setOnActionListener(actions::add)
        }
        try {
            for (key in bottomKeys) {
                val bounds = screenBounds(key)
                assertTrue(driver.device.click(bounds.centerX(), bounds.bottom - 2))
                driver.device.waitForIdle()
            }
            onMain {
                assertEquals(listOf(KeyboardAction.ToggleSymbols, KeyboardAction.CommitText(","),
                    KeyboardAction.Space, KeyboardAction.CommitText("."), KeyboardAction.Enter), actions)
            }
        } finally {
            onMain { snapshot.keyboard.setOnActionListener(checkNotNull(original)) }
        }
        // Reopening with a real editor tap places the caret according to its current text
        // geometry. Read that selection without refocusing, rebinding, or changing the editor.
        val editor = checkNotNull(driver.device.findObject(
            By.res(ImeTestDriver.PACKAGE_NAME, "qa_plain_text"))).accessibilityNodeInfo
        assertTrue("The original editor must still own focus", editor.isFocused)
        assertEquals("Bottom-row observation must not change editor text", before, editor.text.toString())
        val start = editor.textSelectionStart
        val end = editor.textSelectionEnd
        assertTrue("Editor must expose its actual selection", start in 0..before.length && end in 0..before.length)
        val expected = before.replaceRange(minOf(start, end), maxOf(start, end), " ")
        val bounds = screenBounds(checkNotNull(spaceKey))
        // Exercise the lowest touchable pixels, where a navigation overlay used to steal input.
        assertTrue(driver.device.click(bounds.centerX(), bounds.bottom - 2))
        driver.awaitFieldText("qa_plain_text", expected)
        return expected
    }

    private fun screenBounds(key: View): Rect {
        val bounds = Rect()
        onMain {
            assertTrue("Key must remain attached and visible", key.isShown && key.isAttachedToWindow)
            val position = IntArray(2)
            key.getLocationOnScreen(position)
            bounds.set(position[0], position[1], position[0] + key.width, position[1] + key.height)
        }
        return bounds
    }

    private fun onMain(block: () -> Unit) {
        var result: Result<Unit>? = null
        instrumentation.runOnMainSync { result = runCatching(block) }
        checkNotNull(result).getOrThrow()
    }
}
