package io.github.mesteriis.rune.keyboard.ime.ui

import android.os.SystemClock
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.layout.KeyAlternate
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayout
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.ShiftMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.smarttyping.touch.PhysicalTouchSample
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PhysicalTouchInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val spec = KeySpec("a", KeyboardAction.CommitLetter("a"), longPressAlternates =
        listOf(KeyAlternate("á", KeyboardAction.CommitLetter("á"))))
    private val layout = KeyboardLayout(listOf(listOf(spec, KeySpec("s", KeyboardAction.CommitLetter("s")))))
    private val state = KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.OFF)

    @Test fun physicalTapReportsOriginalNormalizedContactBeforeAction() = onMain {
        val events = mutableListOf<String>()
        val samples = mutableListOf<PhysicalTouchSample>()
        val keyboard = keyboard().apply {
            setOnPhysicalTouchListener { samples += it; events += "touch" }
            setOnActionListener { events += "action" }
        }
        val key = key(keyboard)
        touch(key, MotionEvent.ACTION_DOWN, key.width * 0.25f, key.height * 0.75f)
        touch(key, MotionEvent.ACTION_UP)
        assertEquals(listOf("touch", "action"), events)
        val sample = samples.single()
        assertEquals('a', sample.observedKey)
        assertEquals(-0.25, sample.offsets.single { it.key == 'a' }.x, 0.0001)
        assertEquals(0.25, sample.offsets.single { it.key == 'a' }.y, 0.0001)
        assertTrue(sample.offsets.any { it.key == 's' })
    }

    @Test fun accessibilityAlternateAndCancelledGesturesDoNotReportSamples() = onMain {
        val samples = mutableListOf<PhysicalTouchSample>()
        val keyboard = keyboard().apply { setOnPhysicalTouchListener(samples::add) }
        val key = key(keyboard)
        key.performClick()
        key.performLongClick()
        touch(key, MotionEvent.ACTION_DOWN)
        touch(key, MotionEvent.ACTION_CANCEL)
        touch(key, MotionEvent.ACTION_UP)
        touch(key, MotionEvent.ACTION_DOWN)
        keyboard.cancelActiveTouches()
        touch(key, MotionEvent.ACTION_UP)
        touch(key, MotionEvent.ACTION_DOWN)
        touch(key, MotionEvent.ACTION_UP, key.width + 10f)
        assertTrue(samples.isEmpty())
    }

    @Test fun disabledAndEveryNonNormalPolicySuppressTouchSamples() = onMain {
        val samples = mutableListOf<PhysicalTouchSample>()
        val keyboard = keyboard().apply { setOnPhysicalTouchListener(samples::add) }
        InputPolicy.entries.filter { it != InputPolicy.NORMAL }.forEach { policy ->
            keyboard.setPopupPolicy(false, policy)
            touch(key(keyboard), MotionEvent.ACTION_DOWN)
            touch(key(keyboard), MotionEvent.ACTION_UP)
        }
        keyboard.setPopupPolicy(false, InputPolicy.NORMAL)
        keyboard.setTouchLearningEnabled(false)
        touch(key(keyboard), MotionEvent.ACTION_DOWN)
        touch(key(keyboard), MotionEvent.ACTION_UP)
        assertTrue(samples.isEmpty())
    }

    @Test fun languageAndSizeChangesInvalidatePendingTraceButShiftDoesNot() = onMain {
        val keyboard = keyboard()
        var invalidations = 0
        keyboard.setOnTouchGeometryChangedListener { invalidations++ }
        keyboard.render(layout, state.copy(shiftMode = ShiftMode.ONCE))
        assertEquals(0, invalidations)
        keyboard.render(layout, state.copy(language = KeyboardLanguage.RUSSIAN))
        assertEquals(1, invalidations)
        measure(keyboard, 800)
        assertTrue(invalidations >= 2)
    }

    private fun keyboard() = RuneKeyboardView(instrumentation.targetContext, KeyboardViewMetrics(100, 4)).apply {
        setPopupPolicy(false, InputPolicy.NORMAL)
        setTouchLearningEnabled(true)
        render(layout, state)
        measure(this, 600)
    }

    private fun key(keyboard: RuneKeyboardView): View =
        ((keyboard.getChildAt(1) as ViewGroup).getChildAt(0) as ViewGroup).getChildAt(0)

    private fun measure(view: View, width: Int) {
        view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        view.layout(0, 0, width, view.measuredHeight)
    }

    private fun touch(view: View, action: Int, x: Float = view.width / 2f, y: Float = view.height / 2f) {
        val now = SystemClock.uptimeMillis()
        val event = MotionEvent.obtain(now, now, action, x, y, 0)
        try { view.onTouchEvent(event) } finally { event.recycle() }
    }

    private fun onMain(block: () -> Unit) = instrumentation.runOnMainSync(block)
}
