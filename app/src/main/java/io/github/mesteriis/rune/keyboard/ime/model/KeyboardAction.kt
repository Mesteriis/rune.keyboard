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

    data class SwitchLanguage(val direction: LanguageDirection) : KeyboardAction

    data class MoveCursor(val steps: Int) : KeyboardAction {
        init {
            require(steps != 0) { "Cursor movement must not be empty" }
        }
    }

    data object Shift : KeyboardAction
    data object Delete : KeyboardAction
    data object Space : KeyboardAction
    data object DoubleSpaceTap : KeyboardAction
    data object Enter : KeyboardAction
    data object ToggleSymbols : KeyboardAction
    data object ToggleSymbolsPage : KeyboardAction
    data object HideKeyboard : KeyboardAction
    data object NextInputMethod : KeyboardAction
}
