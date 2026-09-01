package io.github.mesteriis.rune.keyboard.ime.gesture

import io.github.mesteriis.rune.keyboard.ime.gesture.SpaceGestureDetector.GestureEvent
import io.github.mesteriis.rune.keyboard.ime.gesture.SpaceGestureDetector.SwipeDirection
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SpaceGestureDetectorTest {
    private val detector = SpaceGestureDetector(
        SpaceGestureDetector.Config(
            swipeThresholdPx = 40f,
            cursorStepPx = 16f,
            verticalEscapePx = 52f,
            doubleTapWindowMillis = 400L,
        ),
    )

    @Test
    fun `a press and release is a tap`() {
        assertTrue(detector.onDown(100f, 10f, 0L).isEmpty())
        assertEquals(listOf(GestureEvent.Tap), detector.onUp(100f, 10f, 50L))
    }

    @Test
    fun `a second press inside the window is a double tap`() {
        detector.onDown(100f, 10f, 0L)
        detector.onUp(100f, 10f, 50L)
        detector.onDown(100f, 10f, 200L)

        assertEquals(listOf(GestureEvent.DoubleTap), detector.onUp(100f, 10f, 250L))
    }

    @Test
    fun `a slow second press is another tap`() {
        detector.onDown(100f, 10f, 0L)
        detector.onUp(100f, 10f, 50L)
        detector.onDown(100f, 10f, 600L)

        assertEquals(listOf(GestureEvent.Tap), detector.onUp(100f, 10f, 650L))
    }

    @Test
    fun `a third quick press does not chain into another double tap`() {
        detector.onDown(100f, 10f, 0L)
        detector.onUp(100f, 10f, 50L)
        detector.onDown(100f, 10f, 200L)
        detector.onUp(100f, 10f, 250L)
        detector.onDown(100f, 10f, 300L)

        assertEquals(listOf(GestureEvent.Tap), detector.onUp(100f, 10f, 350L))
    }

    @Test
    fun `sloppy drift still commits a space`() {
        detector.onDown(100f, 10f, 0L)

        assertTrue(detector.onMove(130f, 14f, 20L).isEmpty())
        assertEquals(listOf(GestureEvent.Tap), detector.onUp(130f, 14f, 40L))
    }

    @Test
    fun `swiping right switches to the next language exactly once`() {
        detector.onDown(100f, 10f, 0L)

        assertEquals(
            listOf(GestureEvent.LanguageSwipe(SwipeDirection.RIGHT)),
            detector.onMove(145f, 12f, 20L),
        )
        assertTrue(detector.onMove(220f, 12f, 40L).isEmpty())
        assertTrue(detector.onUp(220f, 12f, 60L).isEmpty())
    }

    @Test
    fun `swiping left switches to the previous language`() {
        detector.onDown(100f, 10f, 0L)

        assertEquals(
            listOf(GestureEvent.LanguageSwipe(SwipeDirection.LEFT)),
            detector.onMove(55f, 12f, 20L),
        )
    }

    @Test
    fun `a double tap candidate can still swipe`() {
        detector.onDown(100f, 10f, 0L)
        detector.onUp(100f, 10f, 50L)
        detector.onDown(100f, 10f, 200L)

        assertEquals(
            listOf(GestureEvent.LanguageSwipe(SwipeDirection.RIGHT)),
            detector.onMove(150f, 12f, 220L),
        )
        assertTrue(detector.onUp(150f, 12f, 240L).isEmpty())
    }

    @Test
    fun `sliding off the space bar cancels the gesture`() {
        detector.onDown(100f, 40f, 0L)

        assertEquals(listOf(GestureEvent.GestureCancelled), detector.onMove(100f, -20f, 20L))
        assertTrue(detector.onUp(100f, -20f, 40L).isEmpty())
    }

    @Test
    fun `holding enters cursor mode`() {
        detector.onDown(100f, 10f, 0L)

        assertEquals(listOf(GestureEvent.CursorModeStarted), detector.onHoldTimeout(500L))
        assertTrue(detector.isInCursorMode)
    }

    @Test
    fun `holding after a first tap also enters cursor mode`() {
        detector.onDown(100f, 10f, 0L)
        detector.onUp(100f, 10f, 50L)
        detector.onDown(100f, 10f, 200L)

        assertEquals(listOf(GestureEvent.CursorModeStarted), detector.onHoldTimeout(700L))
    }

    @Test
    fun `cursor movement accumulates into discrete steps`() {
        enterCursorMode(anchorX = 100f)

        assertEquals(listOf(GestureEvent.CursorMove(1)), detector.onMove(116f, 10f, 520L))
        assertTrue(detector.onMove(124f, 10f, 540L).isEmpty())
        assertEquals(listOf(GestureEvent.CursorMove(1)), detector.onMove(132f, 10f, 560L))
    }

    @Test
    fun `cursor movement reverses direction`() {
        enterCursorMode(anchorX = 100f)
        detector.onMove(116f, 10f, 520L)

        assertEquals(listOf(GestureEvent.CursorMove(-1)), detector.onMove(100f, 10f, 540L))
    }

    @Test
    fun `jitter below one step emits nothing`() {
        enterCursorMode(anchorX = 100f)

        assertTrue(detector.onMove(108f, 10f, 520L).isEmpty())
        assertTrue(detector.onMove(100f, 10f, 540L).isEmpty())
    }

    @Test
    fun `a single event cannot emit more than the step cap`() {
        enterCursorMode(anchorX = 100f)

        assertEquals(listOf(GestureEvent.CursorMove(20)), detector.onMove(100f + 16f * 25, 10f, 520L))
    }

    @Test
    fun `cursor mode never switches the language`() {
        enterCursorMode(anchorX = 100f)

        val events = detector.onMove(400f, 10f, 520L)

        assertTrue(events.none { it is GestureEvent.LanguageSwipe })
    }

    @Test
    fun `releasing cursor mode ends it without committing a space`() {
        enterCursorMode(anchorX = 100f)

        assertEquals(listOf(GestureEvent.CursorModeEnded), detector.onUp(140f, 10f, 600L))
        assertFalse(detector.isInCursorMode)
    }

    @Test
    fun `hold timeouts are ignored outside an undecided press`() {
        assertTrue(detector.onHoldTimeout(100L).isEmpty())

        detector.onDown(100f, 10f, 0L)
        detector.onMove(160f, 10f, 20L)

        assertTrue(detector.onHoldTimeout(500L).isEmpty())
    }

    @Test
    fun `cancelling cursor mode reports the end of the mode`() {
        enterCursorMode(anchorX = 100f)

        assertEquals(listOf(GestureEvent.CursorModeEnded), detector.onCancel())
        assertFalse(detector.isInCursorMode)
    }

    @Test
    fun `cancelling an undecided press resets the visuals`() {
        detector.onDown(100f, 10f, 0L)

        assertEquals(listOf(GestureEvent.GestureCancelled), detector.onCancel())
        assertTrue(detector.onUp(100f, 10f, 40L).isEmpty())
    }

    @Test
    fun `cancelling while idle emits nothing`() {
        assertTrue(detector.onCancel().isEmpty())
    }

    @Test
    fun `cancelling clears the double tap history`() {
        detector.onDown(100f, 10f, 0L)
        detector.onUp(100f, 10f, 50L)
        detector.onCancel()
        detector.onDown(100f, 10f, 200L)

        assertEquals(listOf(GestureEvent.Tap), detector.onUp(100f, 10f, 250L))
    }

    private fun enterCursorMode(anchorX: Float) {
        detector.onDown(anchorX, 10f, 0L)
        detector.onHoldTimeout(500L)
    }
}
