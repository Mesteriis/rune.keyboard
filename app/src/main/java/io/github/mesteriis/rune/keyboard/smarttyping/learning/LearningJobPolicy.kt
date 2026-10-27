package io.github.mesteriis.rune.keyboard.smarttyping.learning

import java.time.Duration
import java.time.ZonedDateTime

/** Pure local-time policy shared by scheduling and the runtime fail-closed check. */
internal object LearningJobPolicy {
    const val NIGHT_START_HOUR = 1
    const val NIGHT_END_HOUR = 5

    fun isNight(now: ZonedDateTime): Boolean = now.hour in NIGHT_START_HOUR until NIGHT_END_HOUR

    data class RuntimeConditions(
        val enabled: Boolean,
        val night: Boolean,
        val screenOff: Boolean,
        val thermallySafe: Boolean,
        val charging: Boolean,
        val batteryNotLow: Boolean,
        val storageNotLow: Boolean,
    )

    fun allowsRun(conditions: RuntimeConditions): Boolean = conditions.run {
        enabled && night && screenOff && thermallySafe && charging && batteryNotLow && storageNotLow
    }

    fun delayUntilNight(now: ZonedDateTime, allowCurrentWindow: Boolean): Long {
        if (allowCurrentWindow && isNight(now)) return 0L
        val today = now.toLocalDate().atTime(NIGHT_START_HOUR, 0).atZone(now.zone)
        val target = if (now.isBefore(today)) today else today.plusDays(1)
        return Duration.between(now.toInstant(), target.toInstant()).toMillis().coerceAtLeast(0L)
    }
}
