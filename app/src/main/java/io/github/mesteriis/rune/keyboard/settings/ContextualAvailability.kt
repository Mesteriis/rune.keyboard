package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.R

internal object ContextualAvailability {
    fun summaryResource(mode: ContextualPunctuationMode, modelReady: Boolean): Int? = when (mode) {
        ContextualPunctuationMode.OFF -> null
        ContextualPunctuationMode.SUGGESTIONS -> if (modelReady) R.string.settings_contextual_ready
            else R.string.settings_contextual_unavailable
    }
}
