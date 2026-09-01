package io.github.mesteriis.rune.keyboard.ime.model

sealed interface EditorCommand {
    data class CommitText(val value: String) : EditorCommand
    data object DeletePreviousCodePoint : EditorCommand
    data class PerformEditorAction(val actionId: Int) : EditorCommand
    data object InsertNewline : EditorCommand
    data object SwitchToNextInputMethod : EditorCommand
}

data class KeyboardTransition(
    val state: KeyboardState,
    val command: EditorCommand? = null,
)

