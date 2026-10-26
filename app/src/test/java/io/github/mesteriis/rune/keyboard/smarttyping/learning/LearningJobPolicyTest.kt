package io.github.mesteriis.rune.keyboard.smarttyping.learning

import java.time.ZoneId
import java.time.ZonedDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LearningJobPolicyTest {
    private val zone = ZoneId.of("Europe/Madrid")
    private fun at(year: Int, month: Int, day: Int, hour: Int, minute: Int = 0) =
        ZonedDateTime.of(year, month, day, hour, minute, 0, 0, zone)

    @Test fun `night window includes one through five exclusively`() {
        assertFalse(LearningJobPolicy.isNight(at(2026, 9, 19, 0, 59)))
        assertTrue(LearningJobPolicy.isNight(at(2026, 9, 19, 1)))
        assertTrue(LearningJobPolicy.isNight(at(2026, 9, 19, 4, 59)))
        assertFalse(LearningJobPolicy.isNight(at(2026, 9, 19, 5)))
    }

    @Test fun `initial work can use current window but following work waits for tomorrow`() {
        val now = at(2026, 9, 19, 2)
        assertEquals(0L, LearningJobPolicy.delayUntilNight(now, allowCurrentWindow = true))
        assertEquals(23L * 60L * 60L * 1000L,
            LearningJobPolicy.delayUntilNight(now, allowCurrentWindow = false))
    }

    @Test fun `delay is measured to the next local window`() {
        val beforeFallback = at(2026, 10, 24, 6)
        assertEquals(19L * 60L * 60L * 1000L,
            LearningJobPolicy.delayUntilNight(beforeFallback, allowCurrentWindow = true))
    }

    @Test fun `every runtime condition fails closed independently`() {
        val ready = LearningJobPolicy.RuntimeConditions(true, true, true, true, true, true, true)
        assertTrue(LearningJobPolicy.allowsRun(ready))
        val failures = listOf(
            ready.copy(enabled = false), ready.copy(night = false), ready.copy(idle = false),
            ready.copy(thermallySafe = false), ready.copy(charging = false),
            ready.copy(batteryNotLow = false), ready.copy(storageNotLow = false),
        )
        assertTrue(failures.all { !LearningJobPolicy.allowsRun(it) })
    }
}
