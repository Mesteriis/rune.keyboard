package io.github.mesteriis.rune.keyboard.ime.ui

import android.os.SystemClock
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.ViewConfiguration
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayout
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.smarttyping.touch.DynamicTouchResolver
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DynamicTouchInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val state = KeyboardState(KeyboardLanguage.RUSSIAN)
    private fun layout(upper: Boolean = false) = KeyboardLayout(listOf(listOf(
        KeySpec(if (upper) "А" else "а", KeyboardAction.CommitLetter(if (upper) "А" else "а")),
        KeySpec("с", KeyboardAction.CommitLetter("с")))))
    private val priors = mapOf('а' to 0.05, 'с' to 0.9)

    @Test fun appliedTapPreservesCaseAndDoesNotTrainOrLeakToAccessibility() = onMain {
        for (upper in listOf(false, true)) {
            val actions = mutableListOf<KeyboardAction>()
            var learned = 0
            val keyboard = keyboard(upper).apply {
                setTouchLearningEnabled(true)
                setOnPhysicalTouchListener { learned++ }
                setOnActionListener(actions::add)
                setDynamicTouchResolver({ 1L }) { DynamicTouchResolver.propose(it, priors) }
            }
            val key = key(keyboard)
            tap(key)
            key.performClick()
            assertEquals(listOf(KeyboardAction.CommitLetter(if (upper) "С" else "с"),
                KeyboardAction.CommitLetter(if (upper) "А" else "а")), actions)
            assertEquals(0, learned)
        }
    }

    @Test fun shadowReportsGenuineSampleAndWorksWithoutLearning() = onMain {
        val actions = mutableListOf<KeyboardAction>()
        var calls = 0
        var learned = 0
        val keyboard = keyboard().apply {
            setOnActionListener(actions::add)
            setOnPhysicalTouchListener { learned++ }
            setDynamicTouchResolver({ 1L }) { calls++; it.observedKey }
        }
        tap(key(keyboard))
        assertEquals(1, calls)
        assertEquals(0, learned)
        keyboard.setTouchLearningEnabled(true)
        tap(key(keyboard))
        assertEquals(2, calls)
        assertEquals(1, learned)
        assertEquals(listOf(KeyboardAction.CommitLetter("а"), KeyboardAction.CommitLetter("а")), actions)
    }

    @Test fun changedDisabledZeroAndCancelledStampsNeverResolve() = onMain {
        for (mode in listOf("changed", "disabled", "zero", "cancel", "render", "policy", "size", "multitouch")) {
            var stamp = if (mode == "zero") 0L else 1L
            var calls = 0
            val actions = mutableListOf<KeyboardAction>()
            val keyboard = keyboard().apply {
                setOnActionListener(actions::add)
                setDynamicTouchResolver({ stamp }) { calls++; 'с' }
            }
            val key = key(keyboard)
            touch(key, MotionEvent.ACTION_DOWN)
            when (mode) {
                "changed" -> stamp++
                "disabled" -> keyboard.setDynamicTouchResolver(null, null)
                "cancel" -> touch(key, MotionEvent.ACTION_CANCEL)
                "render" -> keyboard.render(layout(), state)
                "policy" -> keyboard.setPopupPolicy(false, InputPolicy.SENSITIVE)
                "size" -> measure(keyboard, 700)
                "multitouch" -> touch(key, MotionEvent.ACTION_POINTER_DOWN)
            }
            touch(key, MotionEvent.ACTION_UP)
            assertEquals(mode, 0, calls)
            assertEquals(mode, if (mode == "cancel") emptyList<KeyboardAction>() else listOf(KeyboardAction.CommitLetter("а")), actions)
        }
    }

    @Test fun longDurationAndUnsupportedOrFarResolverResultsStayOriginal() = onMain {
        for (mode in listOf("long", "latin", "absent", "accessibility")) {
            var calls = 0
            val actions = mutableListOf<KeyboardAction>()
            val keyboard = keyboard().apply {
                setOnActionListener(actions::add)
                setDynamicTouchResolver({ 1L }) { calls++; if (mode == "latin") 'a' else if (mode == "absent") 'т' else 'с' }
            }
            val key = key(keyboard)
            if (mode == "accessibility") key.performClick() else {
                touch(key, MotionEvent.ACTION_DOWN)
                touch(key, MotionEvent.ACTION_UP, if (mode == "long") ViewConfiguration.getLongPressTimeout().toLong() + 1 else 0)
            }
            assertEquals(listOf(KeyboardAction.CommitLetter("а")), actions)
            assertEquals(if (mode in listOf("long", "accessibility")) 0 else 1, calls)
        }
    }

    private fun keyboard(upper: Boolean = false) = RuneKeyboardView(instrumentation.targetContext, KeyboardViewMetrics(100, 4)).apply {
        setPopupPolicy(false, InputPolicy.NORMAL)
        render(layout(upper), state)
        measure(this, 600)
    }
    private fun key(keyboard: RuneKeyboardView): View =
        ((keyboard.getChildAt(1) as ViewGroup).getChildAt(0) as ViewGroup).getChildAt(0)
    private fun measure(view: View, width: Int) {
        view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        view.layout(0, 0, width, view.measuredHeight)
    }
    private fun tap(key: View) { touch(key, MotionEvent.ACTION_DOWN); touch(key, MotionEvent.ACTION_UP) }
    private fun touch(key: View, action: Int, delay: Long = 0) {
        val now = SystemClock.uptimeMillis()
        val event = MotionEvent.obtain(now, now + delay, action, key.width * 0.99f, key.height / 2f, 0)
        try { key.onTouchEvent(event) } finally { event.recycle() }
    }
    private fun onMain(block: () -> Unit) = instrumentation.runOnMainSync(block)
}
