package io.github.mesteriis.rune.keyboard.ime.model

sealed interface KeyboardAction {
    data class CommitLetter(val value: String) : KeyboardAction {
        init {
            require(value.isNotEmpty()) { "Committed letter must not be empty" }
        }
    }

    data class CommitText(val value: String) : KeyboardAction {
        init {
            require(value.isNotEmpty()) { "Committed text must not be empty" }
        }
    }

    data object Shift : KeyboardAction
    data object Delete : KeyboardAction
    data object Space : KeyboardAction
    data object Enter : KeyboardAction
    data object ToggleSymbols : KeyboardAction
    data object ToggleLanguage : KeyboardAction
    data object NextInputMethod : KeyboardAction
}
