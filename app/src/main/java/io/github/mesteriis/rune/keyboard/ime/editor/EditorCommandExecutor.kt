package io.github.mesteriis.rune.keyboard.ime.editor

import android.os.SystemClock
import android.view.KeyCharacterMap
import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy

internal data class EditorExecutionResult(
    val handled: Boolean,
    val clearsSelection: Boolean = false,
)

object EditorCommandExecutor {
    /** Kept for reducer-adjacent JVM tests and raw-editor callers. */
    internal fun execute(
        command: EditorCommand,
        inputConnection: InputConnection,
        hasSelection: Boolean,
        requiresRawKeyEvents: Boolean,
        inputPolicy: InputPolicy = InputPolicy.NORMAL,
    ): EditorExecutionResult = execute(
        command = command,
        inputConnection = inputConnection,
        hasSelection = hasSelection,
        deleteMode = if (requiresRawKeyEvents) DeleteMode.RAW_KEY_EVENT else DeleteMode.CODE_POINT,
        inputPolicy = inputPolicy,
    )

    internal fun execute(
        command: EditorCommand,
        inputConnection: InputConnection,
        hasSelection: Boolean,
        deleteMode: DeleteMode,
        inputPolicy: InputPolicy = InputPolicy.NORMAL,
    ): EditorExecutionResult = when (command) {
        is EditorCommand.SetComposingText -> textMutationResult(
            inputPolicy == InputPolicy.NORMAL && deleteMode != DeleteMode.RAW_KEY_EVENT &&
                inputConnection.setComposingText(command.value, 1),
        )
        EditorCommand.FinishComposingText -> EditorExecutionResult(
            handled = inputPolicy == InputPolicy.NORMAL && deleteMode != DeleteMode.RAW_KEY_EVENT &&
                inputConnection.finishComposingText(),
        )
        is EditorCommand.CommitText -> textMutationResult(
            if (deleteMode == DeleteMode.RAW_KEY_EVENT) {
                sendTextAsKeyEvents(inputConnection, command.value)
            } else {
                inputConnection.commitText(command.value, 1)
            },
        )
        EditorCommand.DeletePreviousCodePoint -> textMutationResult(
            deletePrevious(
                inputConnection = inputConnection,
                hasSelection = hasSelection,
                deleteMode = if (inputPolicy == InputPolicy.SENSITIVE && deleteMode != DeleteMode.RAW_KEY_EVENT) {
                    DeleteMode.CODE_POINT
                } else deleteMode,
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
            if (deleteMode == DeleteMode.RAW_KEY_EVENT) {
                sendKey(inputConnection, KeyEvent.KEYCODE_ENTER)
            } else {
                insertNewline(inputConnection)
            },
        )
        EditorCommand.ConvertPrecedingSpaceToPeriod -> textMutationResult(
            if (deleteMode == DeleteMode.RAW_KEY_EVENT) sendTextAsKeyEvents(inputConnection, " ")
            else inputConnection.commitText(" ", 1),
        )
        is EditorCommand.MoveCursor -> {
            val plan = cursorKeyPlan(command.steps)
            var allSent = true
            repeat(plan.presses) {
                allSent = sendKey(inputConnection, plan.keyCode) && allSent
            }
            EditorExecutionResult(handled = allSent, clearsSelection = true)
        }
        EditorCommand.SwitchToNextInputMethod,
        EditorCommand.HideKeyboard,
        -> EditorExecutionResult(handled = false)
    }

    internal data class CursorKeyPlan(val keyCode: Int, val presses: Int)

    /**
     * Cursor mode moves through the editor's own arrow-key handling: it steps by grapheme
     * cluster, works in TYPE_NULL editors, and needs no text or selection reads.
     */
    internal fun cursorKeyPlan(steps: Int): CursorKeyPlan = CursorKeyPlan(
        keyCode = if (steps < 0) KeyEvent.KEYCODE_DPAD_LEFT else KeyEvent.KEYCODE_DPAD_RIGHT,
        presses = if (steps < 0) -steps else steps,
    )

    private fun deletePrevious(
        inputConnection: InputConnection,
        hasSelection: Boolean,
        deleteMode: DeleteMode,
    ): Boolean {
        if (deleteMode == DeleteMode.RAW_KEY_EVENT) return sendKey(inputConnection, KeyEvent.KEYCODE_DEL)
        if (hasSelection) return inputConnection.commitText("", 1)
        val deleted = when (deleteMode) {
            DeleteMode.GRAPHEME_AWARE -> GraphemeDeletion.deletePrevious(inputConnection)
            DeleteMode.CODE_POINT -> inputConnection.deleteSurroundingTextInCodePoints(1, 0)
            DeleteMode.RAW_KEY_EVENT -> false
        }
        return deleted ||
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
