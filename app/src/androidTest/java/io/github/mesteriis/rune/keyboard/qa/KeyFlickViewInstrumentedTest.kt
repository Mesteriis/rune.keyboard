package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import android.view.MotionEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.FrameLayout
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeyAlternate
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.ui.KeyboardKeyView
import org.junit.Assert.*
import org.junit.Test

class KeyFlickViewInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()

    @Test fun downwardReleaseCommitsOneSymbolAndNeverTrainsTheLetterTouch() = instrumentation.runOnMainSync {
        val f = Fixture()
        f.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        f.touch(MotionEvent.ACTION_MOVE, 50f, 125f)
        assertTrue(f.actions.isEmpty())
        f.touch(MotionEvent.ACTION_UP, 50f, 125f)
        assertEquals(listOf(KeyboardAction.CommitText("1")), f.actions)
        assertEquals(0, f.learnedTouches)
        assertEquals(listOf(true, false), f.touches)
        // A following tap must not inherit the secondary value.
        f.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        f.touch(MotionEvent.ACTION_UP, 51f, 61f)
        assertEquals(KeyboardAction.CommitLetter("q"), f.actions.last())
        assertEquals(1, f.learnedTouches)
    }

    @Test fun fastReleaseCancellationAndRetreatDoNotDoubleCommit() = instrumentation.runOnMainSync {
        val fast = Fixture()
        fast.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        fast.touch(MotionEvent.ACTION_UP, 50f, 125f)
        assertEquals(listOf(KeyboardAction.CommitText("1")), fast.actions)
        val cancelled = Fixture()
        cancelled.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        cancelled.touch(MotionEvent.ACTION_MOVE, 50f, 125f)
        cancelled.touch(MotionEvent.ACTION_CANCEL, 50f, 125f)
        cancelled.touch(MotionEvent.ACTION_UP, 50f, 125f)
        assertTrue(cancelled.actions.isEmpty())
        val returned = Fixture()
        returned.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        returned.touch(MotionEvent.ACTION_MOVE, 50f, 125f)
        returned.touch(MotionEvent.ACTION_UP, 50f, 63f)
        assertEquals(listOf(KeyboardAction.CommitLetter("q")), returned.actions)
        assertEquals(0, returned.learnedTouches)
    }

    @Test fun secondaryAccessibilityActionDoesNotReplaceTapOrAccentLongPress() = instrumentation.runOnMainSync {
        val f = Fixture()
        val node = AccessibilityNodeInfo.obtain()
        try {
            f.key.onInitializeAccessibilityNodeInfo(node)
            assertTrue(node.actionList.any { it.id == R.id.action_key_flick })
            assertTrue(f.key.performAccessibilityAction(R.id.action_key_flick, null))
            f.key.performClick()
            f.key.performLongClick()
            assertEquals(listOf(KeyboardAction.CommitText("1"), KeyboardAction.CommitLetter("q"), KeyboardAction.CommitLetter("é")), f.actions)
            assertEquals(0, f.learnedTouches)
        } finally { node.recycle() }
    }

    @Test fun sidewaysEscapeAndReconfigurationCancelPendingSymbol() = instrumentation.runOnMainSync {
        val f = Fixture()
        f.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        f.touch(MotionEvent.ACTION_MOVE, 160f, 80f)
        f.touch(MotionEvent.ACTION_UP, 50f, 125f)
        assertTrue(f.actions.isEmpty())
        f.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        f.touch(MotionEvent.ACTION_MOVE, 50f, 125f)
        f.key.cancelPendingActions()
        f.touch(MotionEvent.ACTION_UP, 50f, 125f)
        assertTrue(f.actions.isEmpty())
        assertEquals(listOf(true, false, true, false), f.touches)
    }

    @Test fun secondPointerCancelsThePendingFlick() = instrumentation.runOnMainSync {
        val f = Fixture()
        f.touch(MotionEvent.ACTION_DOWN, 50f, 60f)
        f.touch(MotionEvent.ACTION_MOVE, 50f, 125f)
        val properties = Array(2) { index -> MotionEvent.PointerProperties().apply {
            id = index; toolType = MotionEvent.TOOL_TYPE_FINGER
        } }
        val coordinates = Array(2) { index -> MotionEvent.PointerCoords().apply {
            x = (50f + index * 10) * f.key.resources.displayMetrics.density
            y = 125f * f.key.resources.displayMetrics.density
            pressure = 1f; size = 1f
        } }
        val time = SystemClock.uptimeMillis()
        val event = MotionEvent.obtain(time, time + 60, MotionEvent.ACTION_POINTER_DOWN or (1 shl MotionEvent.ACTION_POINTER_INDEX_SHIFT),
            2, properties, coordinates, 0, 0, 1f, 1f, 0, 0, android.view.InputDevice.SOURCE_TOUCHSCREEN, 0)
        try { f.key.onTouchEvent(event) } finally { event.recycle() }
        f.touch(MotionEvent.ACTION_UP, 50f, 125f)
        assertTrue(f.actions.isEmpty())
        assertEquals(listOf(true, false), f.touches)
    }

    private inner class Fixture {
        val actions = mutableListOf<KeyboardAction>()
        val touches = mutableListOf<Boolean>()
        var learnedTouches = 0
        private val downTime = SystemClock.uptimeMillis()
        private var elapsed = 0L
        val key = KeyboardKeyView(instrumentation.targetContext).apply {
            FrameLayout(context).addView(this)
            val density = resources.displayMetrics.density
            layout(0, 0, (100 * density).toInt(), (150 * density).toInt())
            configure(KeySpec("q", KeyboardAction.CommitLetter("q"),
                longPressAlternates = listOf(KeyAlternate("é", KeyboardAction.CommitLetter("é"))),
                flickDown = KeyAlternate("1", KeyboardAction.CommitText("1"))),
                actionListener = { actions += it }, touchStateListener = { touches += it }, popupHost = null,
                physicalTouchListener = { _, _ -> learnedTouches++ }, physicalTouchAllowed = { true })
        }
        fun touch(action: Int, x: Float, y: Float) {
            elapsed += 20
            val event = MotionEvent.obtain(downTime, downTime + elapsed, action, x * key.resources.displayMetrics.density, y * key.resources.displayMetrics.density, 0)
            try { key.onTouchEvent(event) } finally { event.recycle() }
        }
    }
}
