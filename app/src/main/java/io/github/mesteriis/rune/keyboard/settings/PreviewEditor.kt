package io.github.mesteriis.rune.keyboard.settings

import android.os.SystemClock
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
                val from = if (start == end && start > 0) Character.offsetByCodePoints(text, start, -1) else start
                text.delete(from, end)
                field.setSelection(from)
            }
            is EditorCommand.MoveCursor -> {
                val available = if (command.steps > 0) Character.codePointCount(text, end, text.length)
                    else Character.codePointCount(text, 0, start)
                val steps = command.steps.coerceIn(-available, available)
                field.setSelection(Character.offsetByCodePoints(text, if (steps > 0) end else start, steps))
            }
            EditorCommand.ConvertPrecedingSpaceToPeriod -> insert(" ")
            // The preview owns no external editor, IME picker, or composing session.
            else -> Unit
        }
        return transition.state
    }
}
