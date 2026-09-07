package io.github.mesteriis.rune.keyboard.ime.ui

import android.graphics.Insets
import android.graphics.Rect
import android.view.WindowInsets
import androidx.test.filters.SdkSuppress
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import org.junit.Assert.assertEquals
import org.junit.Test

class SafeInsetsInstrumentedTest {
    @Test
    @SdkSuppress(minSdkVersion = 30)
    fun hiddenBarsAndCutoutUseStableInsetsWithoutAccumulating() = onMain {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val keyboard = RuneKeyboardView(context, KeyboardViewMetrics(52, 3))
        val base = context.resources.getDimensionPixelSize(R.dimen.keyboard_padding)
        val bars = WindowInsets.Type.navigationBars()
        val cutout = WindowInsets.Type.displayCutout()
        val hidden = WindowInsets.Builder()
            .setInsets(bars or cutout, Insets.NONE)
            .setInsetsIgnoringVisibility(bars, Insets.of(0, 0, 0, 48))
            .setInsetsIgnoringVisibility(cutout, Insets.of(20, 0, 12, 0))
            .setVisible(bars or cutout, false)
            .build()
        repeat(3) {
            keyboard.dispatchApplyWindowInsets(hidden)
            assertEquals(base + 20, keyboard.paddingLeft)
            assertEquals(base, keyboard.paddingTop)
            assertEquals(base + 12, keyboard.paddingRight)
            assertEquals(base + 48, keyboard.paddingBottom)
            assertEquals(0, keyboard.getChildAt(1).paddingBottom)
        }
        keyboard.dispatchApplyWindowInsets(WindowInsets.Builder().build())
        assertEquals(base, keyboard.paddingLeft)
        assertEquals(base, keyboard.paddingRight)
        assertEquals(base, keyboard.paddingBottom)
    }

    @Test
    @SdkSuppress(minSdkVersion = 30)
    fun imeCaptionControlsExcludeTheirFullHeightWithoutAddingOverlappingNavigationHeight() = onMain {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val keyboard = RuneKeyboardView(context, KeyboardViewMetrics(52, 3))
        val base = context.resources.getDimensionPixelSize(R.dimen.keyboard_padding)
        val bars = WindowInsets.Type.navigationBars()
        val caption = WindowInsets.Type.captionBar()
        val insets = WindowInsets.Builder()
            .setInsetsIgnoringVisibility(bars, Insets.of(0, 0, 0, 24))
            .setInsetsIgnoringVisibility(caption, Insets.of(0, 0, 0, 48))
            .setVisible(bars or caption, false)
            .build()
        keyboard.dispatchApplyWindowInsets(insets)
        assertEquals(base + 48, keyboard.paddingBottom)
    }

    @Test
    @SdkSuppress(maxSdkVersion = 29)
    @Suppress("DEPRECATION")
    fun legacyMissingStableInsetsFallsBackToSystemWindowInsets() = onMain {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val keyboard = RuneKeyboardView(context, KeyboardViewMetrics(52, 3))
        val base = context.resources.getDimensionPixelSize(R.dimen.keyboard_padding)
        val insets = WindowInsets::class.java.getConstructor(Rect::class.java)
            .newInstance(Rect(12, 0, 20, 48))
        repeat(3) {
            keyboard.dispatchApplyWindowInsets(insets)
            assertEquals(base + 12, keyboard.paddingLeft)
            assertEquals(base + 20, keyboard.paddingRight)
            assertEquals(base + 48, keyboard.paddingBottom)
        }
    }

    private fun onMain(block: () -> Unit) {
        var result: Result<Unit>? = null
        InstrumentationRegistry.getInstrumentation().runOnMainSync { result = runCatching(block) }
        checkNotNull(result).getOrThrow()
    }
}
