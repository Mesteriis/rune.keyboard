package io.github.mesteriis.rune.keyboard.ime.ui

import android.os.SystemClock
import android.graphics.Rect
import android.view.InputDevice
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

    @Test fun parentDispatchSplitsTwoKeysAndDefersRenderUntilReverseOrderedReleasesFinish() = onMain {
        for (firstReleasedId in listOf(0, 1)) {
            val actions = mutableListOf<KeyboardAction>()
            val original = KeyboardLayout(listOf(listOf(
                spec.copy(flickDown = KeyAlternate("1", KeyboardAction.CommitText("1"))),
                KeySpec("s", KeyboardAction.CommitLetter("s"),
                    flickDown = KeyAlternate("2", KeyboardAction.CommitText("2"))),
            )))
            val replacement = KeyboardLayout(listOf(listOf(
                KeySpec("x", KeyboardAction.CommitLetter("x")),
                KeySpec("y", KeyboardAction.CommitLetter("y")),
            )))
            val keyboard = RuneKeyboardView(instrumentation.targetContext, KeyboardViewMetrics(100, 4)).apply {
                setPopupPolicy(false, InputPolicy.NORMAL)
                setOnActionListener(actions::add)
                render(original, state)
                measure(this, 600)
            }
            val first = key(keyboard, 0)
            val second = key(keyboard, 1)
            val points = listOf(centerInParent(keyboard, first), centerInParent(keyboard, second))
            val downTime = SystemClock.uptimeMillis()
            dispatch(keyboard, downTime, MotionEvent.ACTION_DOWN, listOf(Finger(0, points[0])))
            dispatch(keyboard, downTime, MotionEvent.ACTION_POINTER_DOWN or
                (1 shl MotionEvent.ACTION_POINTER_INDEX_SHIFT),
                listOf(Finger(0, points[0]), Finger(1, points[1])))

            keyboard.render(replacement, state)
            assertEquals("a", (first as android.widget.TextView).text.toString())
            assertEquals("s", (second as android.widget.TextView).text.toString())

            dispatch(keyboard, downTime, MotionEvent.ACTION_POINTER_UP or
                (firstReleasedId shl MotionEvent.ACTION_POINTER_INDEX_SHIFT),
                listOf(Finger(0, points[0]), Finger(1, points[1])))
            assertEquals(listOf(if (firstReleasedId == 0) KeyboardAction.CommitLetter("a")
                else KeyboardAction.CommitLetter("s")), actions)
            assertEquals("a", first.text.toString()) // One contact still owns the old geometry.

            val remaining = 1 - firstReleasedId
            dispatch(keyboard, downTime, MotionEvent.ACTION_UP, listOf(Finger(remaining, points[remaining])))
            assertEquals(if (firstReleasedId == 0) {
                listOf(KeyboardAction.CommitLetter("a"), KeyboardAction.CommitLetter("s"))
            } else {
                listOf(KeyboardAction.CommitLetter("s"), KeyboardAction.CommitLetter("a"))
            }, actions)
            assertEquals("x", (key(keyboard, 0) as android.widget.TextView).text.toString())
            assertEquals("y", (key(keyboard, 1) as android.widget.TextView).text.toString())
        }
    }

    private fun keyboard() = RuneKeyboardView(instrumentation.targetContext, KeyboardViewMetrics(100, 4)).apply {
        setPopupPolicy(false, InputPolicy.NORMAL)
        setTouchLearningEnabled(true)
        render(layout, state)
        measure(this, 600)
    }

    private fun key(keyboard: RuneKeyboardView, index: Int = 0): View =
        ((keyboard.getChildAt(1) as ViewGroup).getChildAt(0) as ViewGroup).getChildAt(index)

    private fun centerInParent(parent: RuneKeyboardView, child: View): Point {
        val bounds = Rect(0, 0, child.width, child.height)
        parent.offsetDescendantRectToMyCoords(child, bounds)
        return Point(bounds.exactCenterX(), bounds.exactCenterY())
    }

    private fun dispatch(parent: RuneKeyboardView, downTime: Long, action: Int, fingers: List<Finger>) {
        val properties = fingers.map { finger -> MotionEvent.PointerProperties().apply {
            id = finger.id
            toolType = MotionEvent.TOOL_TYPE_FINGER
        } }.toTypedArray()
        val coordinates = fingers.map { finger -> MotionEvent.PointerCoords().apply {
            x = finger.point.x
            y = finger.point.y
            pressure = 1f
            size = 1f
        } }.toTypedArray()
        val event = MotionEvent.obtain(downTime, SystemClock.uptimeMillis(), action, fingers.size,
            properties, coordinates, 0, 0, 1f, 1f, 0, 0, InputDevice.SOURCE_TOUCHSCREEN, 0)
        try {
            assertTrue(parent.dispatchTouchEvent(event))
        } finally {
            event.recycle()
        }
    }

    private data class Point(val x: Float, val y: Float)
    private data class Finger(val id: Int, val point: Point)

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
