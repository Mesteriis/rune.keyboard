package io.github.mesteriis.rune.keyboard.ime.model

sealed interface EditorCommand {
    data class CommitText(val value: String) : EditorCommand
    data class SetComposingText(val value: String) : EditorCommand {
        override fun toString(): String = "SetComposingText(redacted)"
    }
    data object FinishComposingText : EditorCommand
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
     * Requests typing-owned double-space handling. The executor's fallback commits a plain space;
     * only the typing controller may transform its own suffix or retain an Undo transaction.
     */
    data object ConvertPrecedingSpaceToPeriod : EditorCommand

}

data class KeyboardTransition(
    val state: KeyboardState,
    val command: EditorCommand? = null,
)
