package io.github.mesteriis.rune.keyboard.settings

import android.os.SystemClock
import android.view.KeyCharacterMap
import android.view.KeyEvent
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.editor.GraphemeDeletion
import android.widget.EditText
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardReducer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState

/** Runs only the keyboard reducer against a disposable, local sample field. */
internal object PreviewEditor {
    fun apply(field: EditText, state: KeyboardState, action: KeyboardAction, context: EditorContext): KeyboardState {
        val transition = KeyboardReducer.reduce(state.copy(doubleSpacePeriodEnabled = false), action, context, SystemClock.uptimeMillis())
        val text = field.text
        val start = minOf(field.selectionStart, field.selectionEnd).coerceAtLeast(0)
        val end = maxOf(field.selectionStart, field.selectionEnd).coerceAtLeast(start)
        fun insert(value: String) {
            text.replace(start, end, value)
            field.setSelection(start + value.length)
        }
        when (val command = transition.command) {
            is EditorCommand.CommitText -> insert(command.value)
            EditorCommand.InsertNewline -> insert("\n")
            EditorCommand.DeletePreviousCodePoint -> {
                val from = if (start == end && start > 0) GraphemeDeletion.previousBoundary(text.substring(0, start)) else start
                text.delete(from, end)
                field.setSelection(from)
            }
            is EditorCommand.MoveCursor -> {
                val available = if (command.steps > 0) Character.codePointCount(text, end, text.length)
                    else Character.codePointCount(text, 0, start)
                val steps = command.steps.coerceIn(-available, available)
                field.setSelection(Character.offsetByCodePoints(text, if (steps > 0) end else start, steps))
            }
            is EditorCommand.NavigateCursor -> {
                field.requestFocus()
                // The embedded sample is not an IME-served editor. A manually created
                // InputConnection cannot establish that ownership; dispatch only to this view.
                EditorCommandExecutor.dispatchNavigation(command) { eventAction, code, meta ->
                    val now = SystemClock.uptimeMillis()
                    val handled = field.dispatchKeyEvent(KeyEvent(now, now, eventAction, code, 0,
                        meta, KeyCharacterMap.VIRTUAL_KEYBOARD, 0, KeyEvent.FLAG_SOFT_KEYBOARD))
                    // Modifier delivery may update TextView's meta state without consuming the
                    // event. Continue its paired sequence and always release Shift.
                    handled || code == KeyEvent.KEYCODE_SHIFT_LEFT
                }
            }
            is EditorCommand.ContextMenu -> {
                field.requestFocus()
                field.onTextContextMenuItem(EditorCommandExecutor.contextMenuActionId(command.action))
            }
            EditorCommand.ConvertPrecedingSpaceToPeriod -> insert(" ")
            // The preview owns no external editor, IME picker, or composing session.
            else -> Unit
        }
        return transition.state
    }
}
