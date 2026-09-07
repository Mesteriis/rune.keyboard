package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Rect
import android.os.Build
import android.os.SystemClock
import android.view.View
import android.view.Surface
import android.view.WindowInsets
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
        assertBottomRowSafeAndTapSpace("left right")
        driver.device.pressBack()
        assertTrue(driver.device.wait(Until.gone(By.desc(
            instrumentation.targetContext.getString(R.string.key_delete))), ImeTestDriver.WAIT_MILLIS))
        // Directly reopen the same editor; no driver fallback may rebind the service here.
        checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_plain_text"))).click()
        awaitKeyboard()
        // Clicking the editor to reopen also places its caret at the tapped text position.
        assertBottomRowSafeAndTapSpace("left right ")
        val beforeRotation = keyboardSnapshot().keyboard
        try {
            driver.device.setOrientationLeft()
            awaitKeyboard()
            awaitTransition(beforeRotation)
            assertBottomRowSafeAndTapSpace("left right  ")
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
    private fun assertBottomRowSafeAndTapSpace(expected: String) {
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
            // API26's framework parent can consume the bar before dispatching to Rune. Measure
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
        val bounds = screenBounds(checkNotNull(spaceKey))
        // Exercise the lowest touchable pixels, where a navigation overlay used to steal input.
        assertTrue(driver.device.click(bounds.centerX(), bounds.bottom - 2))
        driver.awaitFieldText("qa_plain_text", expected)
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
