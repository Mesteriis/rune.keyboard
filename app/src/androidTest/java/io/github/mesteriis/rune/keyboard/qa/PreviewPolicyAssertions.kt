package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Bundle
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.Assert.*
import java.util.regex.Pattern

/** Test-local policy/spec inspection; exceptions return to the test thread, never app main. */
internal fun assertPreviewFixture(bounds: Rect, enabled: Boolean, policy: InputPolicy) {
    val instrumentation = InstrumentationRegistry.getInstrumentation()
    val snapshot = keyboardSnapshot()
    var result: Result<Unit>? = null
    instrumentation.runOnMainSync {
        result = runCatching {
            fun field(owner: Any, name: String): Any? = owner.javaClass.getDeclaredField(name)
                .apply { isAccessible = true }.get(owner)
            val raw = instrumentation.targetContext.getSharedPreferences(
                ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).all
            assertEquals(enabled, SettingsCodec.decode(raw).keyPreview)
            assertEquals(enabled, field(snapshot.keyboard, "previewEnabled"))
            assertEquals(policy, field(snapshot.keyboard, "inputPolicy"))
            val matched = snapshot.keys.filter { key ->
                val location = IntArray(2); key.getLocationOnScreen(location)
                Rect(location[0], location[1], location[0] + key.width, location[1] + key.height) == bounds
            }
            assertEquals("Expected one actual key at the frozen screen bounds", 1, matched.size)
            val spec = field(matched.single(), "spec") as KeySpec
            assertEquals(KeyStyle.CHARACTER, spec.style)
            assertTrue("Preview fixture must have no alternate-key timer", spec.longPressAlternates.isEmpty())
        }
    }
    checkNotNull(result).getOrThrow()
}

/** Eventual visual policy, not a frame-latency or continuous-absence measurement. */
internal fun observePreview(
    driver: ImeTestDriver,
    phase: Int,
    enabled: Boolean,
    policy: InputPolicy,
    expectedVisible: Boolean,
    retainDiagnostics: Boolean = true,
) {
    driver.device.waitForIdle()
    // A preference change can replace the input view after accessibility first reports
    // its Delete key, and can restore either enabled letter layout. Await a no-alternate
    // character in both EN and RU before freezing touch geometry.
    val key = checkNotNull(driver.device.wait(
        Until.findObject(By.text(Pattern.compile("[bBвВ]"))), ImeTestDriver.WAIT_MILLIS,
    )) { "Preview phase $phase character target did not become visible" }
    val bounds = Rect(key.visibleBounds)
    assertPreviewFixture(bounds, enabled, policy)
    val crop = Rect(bounds.left, (bounds.top - bounds.height() * 2).coerceAtLeast(0), bounds.right, bounds.top)
    fun captureCrop(): Bitmap {
        val screen = driver.captureScreen()
        return try {
            Bitmap.createBitmap(screen, crop.left, crop.top, crop.width(), crop.height())
        } finally {
            screen.recycle()
        }
    }

    // Each mode gets its own settled baseline. Never query accessibility during the touch:
    // doing so can wait past a key's alternate timer and alter the state being observed.
    var baseline = captureCrop()
    var stable = false
    val settleDeadline = SystemClock.uptimeMillis() + 1_000
    while (SystemClock.uptimeMillis() < settleDeadline) {
        SystemClock.sleep(50)
        val next = captureCrop()
        stable = driver.changedPixels(baseline, next) <= 40
        baseline.recycle()
        baseline = next
        if (stable) break
    }
    if (!stable) {
        baseline.recycle()
        error("Preview phase $phase did not reach a stable baseline")
    }
    var maxChanged = -1
    var samples = 0
    var firstVisibleMs = -1L
    var peak: Bitmap? = null
    try {
        val touch = driver.touchDown(bounds)
        try {
            val deadline = touch.downTime + 1_000
            // All three phases sample the complete bounded window, including negative controls.
            do {
                val sample = captureCrop()
                val elapsed = SystemClock.uptimeMillis() - touch.downTime
                val changed = driver.changedPixels(baseline, sample)
                samples++
                if (changed > 40 && firstVisibleMs < 0) firstVisibleMs = elapsed
                if (changed > maxChanged) {
                    peak?.recycle()
                    peak = sample
                    maxChanged = changed
                } else sample.recycle()
                val remaining = deadline - SystemClock.uptimeMillis()
                if (remaining > 0) SystemClock.sleep(minOf(50, remaining))
            } while (SystemClock.uptimeMillis() < deadline)
        } finally {
            driver.cancelTouch(touch)
            if (retainDiagnostics) InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
                putInt("preview_phase", phase)
                putInt("preview_samples", samples)
                putInt("preview_max_changed_pixels", maxChanged)
                putLong("preview_first_visible_sample_ms", firstVisibleMs)
                putLong("preview_observed_ms", SystemClock.uptimeMillis() - touch.downTime)
            })
        }
        val matches = if (expectedVisible) maxChanged > 40 else maxChanged in 0..40
        if (!matches && retainDiagnostics) {
            driver.saveFailureBitmap("popup-$phase-before.png", baseline)
            peak?.let { driver.saveFailureBitmap("popup-$phase-peak.png", it) }
        }
        assertTrue("Preview phase $phase: $maxChanged changed pixels across $samples samples", matches)
    } finally {
        baseline.recycle()
        peak?.recycle()
    }
}
