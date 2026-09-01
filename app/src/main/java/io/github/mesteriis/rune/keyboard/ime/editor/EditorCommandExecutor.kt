package io.github.mesteriis.rune.keyboard.ime.editor

import android.os.SystemClock
import android.view.KeyCharacterMap
import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand

internal data class EditorExecutionResult(
    val handled: Boolean,
    val clearsSelection: Boolean = false,
)

object EditorCommandExecutor {
    internal fun execute(
        command: EditorCommand,
        inputConnection: InputConnection,
        hasSelection: Boolean,
        requiresRawKeyEvents: Boolean,
    ): EditorExecutionResult = when (command) {
        is EditorCommand.CommitText -> textMutationResult(
            if (requiresRawKeyEvents) {
                sendTextAsKeyEvents(inputConnection, command.value)
            } else {
                inputConnection.commitText(command.value, 1)
            },
        )
        EditorCommand.DeletePreviousCodePoint -> textMutationResult(
            deletePreviousCodePoint(
                inputConnection = inputConnection,
                hasSelection = hasSelection,
                requiresRawKeyEvents = requiresRawKeyEvents,
            ),
        )
        is EditorCommand.PerformEditorAction -> {
            if (inputConnection.performEditorAction(command.actionId)) {
                EditorExecutionResult(handled = true)
            } else {
                textMutationResult(insertNewline(inputConnection))
            }
        }
        EditorCommand.InsertNewline -> textMutationResult(
            if (requiresRawKeyEvents) {
                sendKey(inputConnection, KeyEvent.KEYCODE_ENTER)
            } else {
                insertNewline(inputConnection)
            },
        )
        EditorCommand.SwitchToNextInputMethod -> EditorExecutionResult(handled = false)
    }

    private fun deletePreviousCodePoint(
        inputConnection: InputConnection,
        hasSelection: Boolean,
        requiresRawKeyEvents: Boolean,
    ): Boolean {
        if (requiresRawKeyEvents) return sendKey(inputConnection, KeyEvent.KEYCODE_DEL)
        if (hasSelection) return inputConnection.commitText("", 1)
        return inputConnection.deleteSurroundingTextInCodePoints(1, 0) ||
            sendKey(inputConnection, KeyEvent.KEYCODE_DEL)
    }

    private fun insertNewline(inputConnection: InputConnection): Boolean =
        inputConnection.commitText("\n", 1) || sendKey(inputConnection, KeyEvent.KEYCODE_ENTER)

    private fun sendTextAsKeyEvents(
        inputConnection: InputConnection,
        value: String,
    ): Boolean {
        val events = KeyCharacterMap.load(KeyCharacterMap.VIRTUAL_KEYBOARD)
            .getEvents(value.toCharArray())
            ?: return inputConnection.sendKeyEvent(
                KeyEvent(
                    SystemClock.uptimeMillis(),
                    value,
                    KeyCharacterMap.VIRTUAL_KEYBOARD,
                    KeyEvent.FLAG_SOFT_KEYBOARD,
                ),
            )
        var allEventsSent = true
        events.forEach { event ->
            allEventsSent = inputConnection.sendKeyEvent(event) && allEventsSent
        }
        return allEventsSent
    }

    private fun textMutationResult(handled: Boolean): EditorExecutionResult = EditorExecutionResult(
        handled = handled,
        clearsSelection = handled,
    )

    private fun sendKey(inputConnection: InputConnection, keyCode: Int): Boolean {
        val sentDown = inputConnection.sendKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, keyCode))
        val sentUp = inputConnection.sendKeyEvent(KeyEvent(KeyEvent.ACTION_UP, keyCode))
        return sentDown && sentUp
    }
}
