package io.github.mesteriis.rune.keyboard.ime.model

import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.settings.StartingLanguage

/**
 * Decides what survives an editor session boundary.
 *
 * A configuration change — most importantly folding or unfolding the device — re-delivers
 * `onStartInput(restarting = true)` for the same editor. Keeping the previous state there is what
 * preserves shift, caps lock, the active layer and the language across a fold (FOLD-003).
 */
object KeyboardSessionPolicy {
    fun onStartInput(
        previous: KeyboardState,
        restarting: Boolean,
        settings: KeyboardSettings,
        lastUsedLanguage: KeyboardLanguage?,
    ): KeyboardState {
        if (restarting) {
            return previous
                .withEnabledLanguages(settings.enabledLanguages)
                .copy(doubleSpacePeriodEnabled = settings.doubleSpacePeriod)
        }
        return KeyboardState.initial(
            language = resolveStartLanguage(settings, lastUsedLanguage),
            automaticCapitalization = false,
            enabledLanguages = settings.enabledLanguages,
            doubleSpacePeriodEnabled = settings.doubleSpacePeriod,
        )
    }

    fun resolveStartLanguage(
        settings: KeyboardSettings,
        lastUsedLanguage: KeyboardLanguage?,
    ): KeyboardLanguage {
        val candidate = when (val starting = settings.startingLanguage) {
            StartingLanguage.LastUsed -> lastUsedLanguage
            is StartingLanguage.Fixed -> starting.language
        }
        return candidate?.takeIf { it in settings.enabledLanguages }
            ?: settings.enabledLanguages.first()
    }
}
