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
        EditorCommand.ConvertPrecedingSpaceToPeriod -> textMutationResult(
            convertPrecedingSpaceToPeriod(inputConnection),
        )
        EditorCommand.RevertDoubleSpacePeriod -> textMutationResult(
            revertDoubleSpacePeriod(
                inputConnection = inputConnection,
                hasSelection = hasSelection,
                requiresRawKeyEvents = requiresRawKeyEvents,
            ),
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

    private fun convertPrecedingSpaceToPeriod(inputConnection: InputConnection): Boolean {
        val before = inputConnection.getTextBeforeCursor(2, 0)
        if (!DoubleSpacePeriod.canConvert(before)) {
            return inputConnection.commitText(" ", 1)
        }
        inputConnection.beginBatchEdit()
        return try {
            inputConnection.deleteSurroundingText(1, 0) &&
                inputConnection.commitText(". ", 1)
        } finally {
            inputConnection.endBatchEdit()
        }
    }

    private fun revertDoubleSpacePeriod(
        inputConnection: InputConnection,
        hasSelection: Boolean,
        requiresRawKeyEvents: Boolean,
    ): Boolean {
        if (hasSelection || requiresRawKeyEvents) {
            return deletePreviousCodePoint(inputConnection, hasSelection, requiresRawKeyEvents)
        }
        val before = inputConnection.getTextBeforeCursor(2, 0)
        if (!DoubleSpacePeriod.canRevert(before)) {
            return deletePreviousCodePoint(inputConnection, hasSelection = false, requiresRawKeyEvents = false)
        }
        inputConnection.beginBatchEdit()
        return try {
            inputConnection.deleteSurroundingText(2, 0) &&
                inputConnection.commitText(" ", 1)
        } finally {
            inputConnection.endBatchEdit()
        }
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
