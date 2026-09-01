package io.github.mesteriis.rune.keyboard.ime.feedback

import io.github.mesteriis.rune.keyboard.settings.HapticMode
import io.github.mesteriis.rune.keyboard.settings.SoundMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FeedbackPolicyTest {
    @Test
    fun `haptics can be turned off`() {
        assertEquals(HapticSpec.None, FeedbackPolicy.hapticSpec(HapticMode.OFF))
    }

    @Test
    fun `the system mode uses the platform keyboard tap`() {
        assertEquals(
            HapticSpec.Platform(HapticFeel.KEYBOARD_TAP),
            FeedbackPolicy.hapticSpec(HapticMode.SYSTEM),
        )
    }

    @Test
    fun `intensities map to increasingly strong platform effects`() {
        assertEquals(
            HapticSpec.Platform(HapticFeel.LIGHT_TICK),
            FeedbackPolicy.hapticSpec(HapticMode.LIGHT),
        )
        assertEquals(
            HapticSpec.Platform(HapticFeel.VIRTUAL_KEY),
            FeedbackPolicy.hapticSpec(HapticMode.NORMAL),
        )
        assertEquals(
            HapticSpec.Platform(HapticFeel.LONG_PRESS),
            FeedbackPolicy.hapticSpec(HapticMode.STRONG),
        )
    }

    @Test
    fun `every explicit intensity is a distinct effect`() {
        val feels = listOf(HapticMode.LIGHT, HapticMode.NORMAL, HapticMode.STRONG)
            .map { FeedbackPolicy.hapticSpec(it) }
            .filterIsInstance<HapticSpec.Platform>()
            .map { it.feel }

        assertEquals(feels.size, feels.distinct().size)
    }

    @Test
    fun `sound modes map to fixed volumes`() {
        assertEquals(SoundSpec.None, FeedbackPolicy.soundSpec(SoundMode.OFF))
        assertEquals(SoundSpec.SystemDefault, FeedbackPolicy.soundSpec(SoundMode.SYSTEM))

        val quiet = FeedbackPolicy.soundSpec(SoundMode.QUIET) as SoundSpec.FixedVolume
        val normal = FeedbackPolicy.soundSpec(SoundMode.NORMAL) as SoundSpec.FixedVolume

        assertTrue(quiet.volume > 0f)
        assertTrue(quiet.volume < normal.volume)
        assertTrue(normal.volume <= 1f)
    }

    @Test
    fun `a press that changed nothing stays silent`() {
        assertFalse(FeedbackPolicy.shouldProvide(false, CommandOutcome.DROPPED))
        assertFalse(FeedbackPolicy.shouldProvide(false, CommandOutcome.NO_COMMAND))
    }

    @Test
    fun `state changes and delivered commands are confirmed`() {
        assertTrue(FeedbackPolicy.shouldProvide(true, CommandOutcome.NO_COMMAND))
        assertTrue(FeedbackPolicy.shouldProvide(false, CommandOutcome.DELIVERED))
        assertTrue(FeedbackPolicy.shouldProvide(true, CommandOutcome.DROPPED))
    }
}
