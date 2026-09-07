package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Bundle
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.regex.Pattern

@RunWith(AndroidJUnit4::class)
class ImePrivacyInstrumentedTest : ImeTestBase() {
    @Test
    fun passwordFieldSuppressesPopupWithNormalFieldPositiveControl() {
        driver.setKeyPreviewForTest(true)
        driver.tapQaControl("qa_seed_cursor")
        observePreview(phase = 0, enabled = true, policy = InputPolicy.NORMAL, expectedVisible = true)
        driver.setKeyPreviewForTest(false)
        driver.focusField("qa_plain_text")
        observePreview(phase = 1, enabled = false, policy = InputPolicy.NORMAL, expectedVisible = false)
        driver.setKeyPreviewForTest(true)
        driver.focusField("qa_password")
        observePreview(phase = 2, enabled = true, policy = InputPolicy.SENSITIVE, expectedVisible = false)
    }

    /** Eventual visual policy, not a frame-latency or continuous-absence measurement. */
    private fun observePreview(phase: Int, enabled: Boolean, policy: InputPolicy, expectedVisible: Boolean) {
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
                InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
                    putInt("preview_phase", phase)
                    putInt("preview_samples", samples)
                    putInt("preview_max_changed_pixels", maxChanged)
                    putLong("preview_first_visible_sample_ms", firstVisibleMs)
                    putLong("preview_observed_ms", SystemClock.uptimeMillis() - touch.downTime)
                })
            }
            val matches = if (expectedVisible) maxChanged > 40 else maxChanged in 0..40
            if (!matches) {
                driver.saveFailureBitmap("popup-$phase-before.png", baseline)
                peak?.let { driver.saveFailureBitmap("popup-$phase-peak.png", it) }
            }
            assertTrue("Preview phase $phase: $maxChanged changed pixels across $samples samples", matches)
        } finally {
            baseline.recycle()
            peak?.recycle()
        }
    }

    @Test
    fun syntheticCanaryIsAbsentFromRuneProcessLogcat() {
        driver.shell("logcat -c")
        driver.tapQaControl("qa_seed_canary")
        driver.tapDelete()
        val imePid = driver.shell("pidof ${ImeTestDriver.PACKAGE_NAME}").split(' ').firstOrNull().orEmpty()
        val logs = if (imePid.isEmpty()) "" else driver.shell("logcat -d --pid=$imePid")
        assertTrue("Synthetic editor text appeared in Rune-scoped Logcat", "RUNE_QA_CANARY_7429" !in logs)
    }
}
