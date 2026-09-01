package io.github.mesteriis.rune.keyboard.ime.gesture

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BackspaceRepeatScheduleTest {
    @Test
    fun `the first repeats keep the precise interval`() {
        assertEquals(BackspaceRepeatSchedule.INITIAL_INTERVAL_MILLIS, BackspaceRepeatSchedule.intervalMillis(0))
        assertEquals(BackspaceRepeatSchedule.INITIAL_INTERVAL_MILLIS, BackspaceRepeatSchedule.intervalMillis(7))
    }

    @Test
    fun `holding longer accelerates in two steps`() {
        assertEquals(BackspaceRepeatSchedule.FAST_INTERVAL_MILLIS, BackspaceRepeatSchedule.intervalMillis(8))
        assertEquals(BackspaceRepeatSchedule.FAST_INTERVAL_MILLIS, BackspaceRepeatSchedule.intervalMillis(23))
        assertEquals(BackspaceRepeatSchedule.TURBO_INTERVAL_MILLIS, BackspaceRepeatSchedule.intervalMillis(24))
        assertEquals(BackspaceRepeatSchedule.TURBO_INTERVAL_MILLIS, BackspaceRepeatSchedule.intervalMillis(5_000))
    }

    @Test
    fun `the interval never grows`() {
        val intervals = (0..40).map(BackspaceRepeatSchedule::intervalMillis)

        intervals.zipWithNext().forEach { (current, next) ->
            assertTrue(next <= current)
        }
    }
}
