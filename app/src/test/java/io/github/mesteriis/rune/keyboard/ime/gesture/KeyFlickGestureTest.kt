package io.github.mesteriis.rune.keyboard.ime.gesture

import org.junit.Assert.*
import org.junit.Test

class KeyFlickGestureTest {
    private fun gesture() = KeyFlickGesture(20f, 25f, 18f, 24f, 8f, 100f)

    @Test fun `small movements remain ordinary taps`() {
        val g = gesture()
        assertEquals(KeyFlickGesture.State.PENDING, g.move(23f, 31f))
        assertFalse(g.movedBeyondTap)
    }
    @Test fun `downward movement selects even when the only sample is release`() {
        val g = gesture()
        assertEquals(KeyFlickGesture.State.SELECTED, g.move(22f, 48f))
        assertTrue(g.movedBeyondTap)
    }
    @Test fun `selected flick tolerates small reversal but can be returned to a letter`() {
        val g = gesture()
        g.move(20f, 50f)
        assertEquals(KeyFlickGesture.State.SELECTED, g.move(20f, 40f))
        assertEquals(KeyFlickGesture.State.PENDING, g.move(20f, 28f))
        assertTrue(g.movedBeyondTap) // Never train letter touch correction from a reverted gesture.
    }
    @Test fun `sideways and upward escapes cannot become symbols or letters later`() {
        for ((x, y) in listOf(50f to 50f, 20f to 10f, 20f to 130f)) {
            val g = gesture()
            assertEquals(KeyFlickGesture.State.CANCELLED, g.move(x, y))
            assertEquals(KeyFlickGesture.State.CANCELLED, g.move(20f, 50f))
        }
    }
    @Test fun `diagonal movement requires vertical intent`() {
        assertEquals(KeyFlickGesture.State.PENDING, gesture().move(40f, 46f))
        assertEquals(KeyFlickGesture.State.SELECTED, gesture().move(32f, 50f))
    }
    @Test fun `nonfinite coordinates cancel`() {
        assertEquals(KeyFlickGesture.State.CANCELLED, gesture().move(Float.NaN, 50f))
        assertEquals(KeyFlickGesture.State.CANCELLED, gesture().move(20f, Float.POSITIVE_INFINITY))
    }
}
