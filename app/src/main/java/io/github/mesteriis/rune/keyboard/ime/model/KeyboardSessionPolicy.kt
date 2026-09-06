package io.github.mesteriis.rune.keyboard.ime.model

import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.settings.StartingLanguage

/**
 * Decides what survives an editor session boundary and preserves the existing caps lookup policy.
 *
 * Framework restarts preserve visual state. Configuration-driven Activity recreation can also
 * deliver a fresh start; ConfigurationVisualContinuity handles that bounded visual-only case
 * before this default fresh-editor policy. Neither policy restores typing ownership.
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

    /** No new editor read: the callback is the service's pre-existing NORMAL caps-mode lookup. */
    fun withAutomaticCapitalization(
        state: KeyboardState,
        editor: EditorContext,
        hasComposingWord: Boolean,
        ownedSentenceBoundary: Boolean,
        readCursorCapsMode: () -> Int?,
    ): KeyboardState {
        if (!editor.supportsAutomaticCapitalization || state.layer != KeyboardLayer.LETTERS) {
            return state.withAutomaticCapitalization(false)
        }
        if (hasComposingWord) return state
        if (ownedSentenceBoundary) return state.withAutomaticCapitalization(true)
        val caps = readCursorCapsMode() ?: return state
        return state.withAutomaticCapitalization(caps != 0)
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
