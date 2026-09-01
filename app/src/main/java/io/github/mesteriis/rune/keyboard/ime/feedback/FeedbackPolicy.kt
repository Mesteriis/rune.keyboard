package io.github.mesteriis.rune.keyboard.ime.feedback

import io.github.mesteriis.rune.keyboard.settings.HapticMode
import io.github.mesteriis.rune.keyboard.settings.SoundMode

/** What happened to the editor command produced by a key press. */
enum class CommandOutcome {
    /** The press only changed keyboard state, e.g. Shift. */
    NO_COMMAND,
    DELIVERED,

    /** No input connection, or the editor refused the command. */
    DROPPED,
}

/**
 * The platform haptic effects Rune uses, ordered by perceived strength.
 *
 * Rune ships without `android.permission.VIBRATE`, so intensities are expressed as platform
 * haptic constants rather than raw vibration amplitudes. How strong each one feels is up to the
 * device, and all of them follow the system touch-feedback setting.
 */
enum class HapticFeel {
    LIGHT_TICK,
    KEYBOARD_TAP,
    VIRTUAL_KEY,
    LONG_PRESS,
}

sealed interface HapticSpec {
    data object None : HapticSpec
    data class Platform(val feel: HapticFeel) : HapticSpec
}

sealed interface SoundSpec {
    data object None : SoundSpec

    /** Play at the system effect volume, honouring the system touch-sounds setting. */
    data object SystemDefault : SoundSpec

    data class FixedVolume(val volume: Float) : SoundSpec
}

/** Pure mapping from user preferences to concrete feedback, so every row is unit-tested. */
object FeedbackPolicy {
    fun hapticSpec(mode: HapticMode): HapticSpec = when (mode) {
        HapticMode.OFF -> HapticSpec.None
        HapticMode.SYSTEM -> HapticSpec.Platform(HapticFeel.KEYBOARD_TAP)
        HapticMode.LIGHT -> HapticSpec.Platform(HapticFeel.LIGHT_TICK)
        HapticMode.NORMAL -> HapticSpec.Platform(HapticFeel.VIRTUAL_KEY)
        HapticMode.STRONG -> HapticSpec.Platform(HapticFeel.LONG_PRESS)
    }

    fun soundSpec(mode: SoundMode): SoundSpec = when (mode) {
        SoundMode.OFF -> SoundSpec.None
        SoundMode.SYSTEM -> SoundSpec.SystemDefault
        SoundMode.QUIET -> SoundSpec.FixedVolume(QUIET_VOLUME)
        SoundMode.NORMAL -> SoundSpec.FixedVolume(NORMAL_VOLUME)
    }

    /** No click, no buzz when a press changed nothing — for example a dead input connection. */
    fun shouldProvide(stateChanged: Boolean, outcome: CommandOutcome): Boolean =
        stateChanged || outcome == CommandOutcome.DELIVERED

    private const val QUIET_VOLUME = 0.1f
    private const val NORMAL_VOLUME = 0.5f
}
