package io.github.mesteriis.rune.keyboard.ime.feedback

import android.content.Context
import android.media.AudioManager
import android.provider.Settings
import android.view.HapticFeedbackConstants
import android.view.View
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.settings.HapticMode
import io.github.mesteriis.rune.keyboard.settings.SoundMode

/** Executes what [FeedbackPolicy] decided. */
internal class FeedbackController(private val context: Context) {
    private val audioManager: AudioManager? = context.getSystemService(AudioManager::class.java)

    fun provide(
        view: View,
        action: KeyboardAction,
        hapticMode: HapticMode,
        soundMode: SoundMode,
    ) {
        performHaptic(view, FeedbackPolicy.hapticSpec(hapticMode))
        playSound(FeedbackPolicy.soundSpec(soundMode), soundEffectFor(action))
    }

    private fun performHaptic(view: View, spec: HapticSpec) {
        when (spec) {
            HapticSpec.None -> Unit
            is HapticSpec.Platform -> view.performHapticFeedback(hapticConstant(spec.feel))
        }
    }

    private fun playSound(spec: SoundSpec, effectId: Int) {
        val audioManager = audioManager ?: return
        when (spec) {
            SoundSpec.None -> Unit
            SoundSpec.SystemDefault -> if (systemSoundEffectsEnabled()) {
                audioManager.playSoundEffect(effectId)
            }
            is SoundSpec.FixedVolume -> if (
                audioManager.ringerMode == AudioManager.RINGER_MODE_NORMAL
            ) {
                audioManager.playSoundEffect(effectId, spec.volume)
            }
        }
    }

    private fun systemSoundEffectsEnabled(): Boolean = Settings.System.getInt(
        context.contentResolver,
        Settings.System.SOUND_EFFECTS_ENABLED,
        1,
    ) == 1

    private fun hapticConstant(feel: HapticFeel): Int = when (feel) {
        HapticFeel.LIGHT_TICK -> HapticFeedbackConstants.CLOCK_TICK
        HapticFeel.KEYBOARD_TAP -> HapticFeedbackConstants.KEYBOARD_TAP
        HapticFeel.VIRTUAL_KEY -> HapticFeedbackConstants.VIRTUAL_KEY
        HapticFeel.LONG_PRESS -> HapticFeedbackConstants.LONG_PRESS
    }

    private fun soundEffectFor(action: KeyboardAction): Int = when (action) {
        KeyboardAction.Delete -> AudioManager.FX_KEYPRESS_DELETE
        KeyboardAction.Space,
        KeyboardAction.DoubleSpaceTap,
        -> AudioManager.FX_KEYPRESS_SPACEBAR
        KeyboardAction.Enter -> AudioManager.FX_KEYPRESS_RETURN
        else -> AudioManager.FX_KEYPRESS_STANDARD
    }
}
