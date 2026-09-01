package io.github.mesteriis.rune.keyboard.ime.model

sealed interface EditorCommand {
    data class CommitText(val value: String) : EditorCommand
    data object DeletePreviousCodePoint : EditorCommand
    data class PerformEditorAction(val actionId: Int) : EditorCommand
    data object InsertNewline : EditorCommand
    data object SwitchToNextInputMethod : EditorCommand
    data object HideKeyboard : EditorCommand

    data class MoveCursor(val steps: Int) : EditorCommand {
        init {
            require(steps != 0) { "Cursor movement must not be empty" }
        }
    }

    /**
     * Replaces the space committed by the first of two quick space taps with ". ".
     * Falls back to committing a plain space when the surrounding text is not eligible.
     */
    data object ConvertPrecedingSpaceToPeriod : EditorCommand

    /** Undoes [ConvertPrecedingSpaceToPeriod], restoring the plain space. */
    data object RevertDoubleSpacePeriod : EditorCommand
}

data class KeyboardTransition(
    val state: KeyboardState,
    val command: EditorCommand? = null,
)
