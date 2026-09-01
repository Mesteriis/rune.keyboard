package io.github.mesteriis.rune.keyboard.ime.model

import android.view.inputmethod.EditorInfo

object KeyboardReducer {
    fun reduce(
        state: KeyboardState,
        action: KeyboardAction,
        editorContext: EditorContext,
        nowMillis: Long,
    ): KeyboardTransition {
        // Only Backspace consumes the double-space undo; every other action invalidates it.
        val base = if (action == KeyboardAction.Delete) state else state.clearDoubleSpaceUndo()
        return when (action) {
            is KeyboardAction.CommitLetter -> KeyboardTransition(
                state = base.afterTextCommitted(),
                command = EditorCommand.CommitText(
                    if (base.shiftMode.usesUppercase) {
                        action.value.uppercase(base.language.locale)
                    } else {
                        action.value.lowercase(base.language.locale)
                    },
                ),
            )
            is KeyboardAction.CommitText -> KeyboardTransition(
                state = base.afterTextCommitted(),
                command = EditorCommand.CommitText(action.value),
            )
            KeyboardAction.Space -> KeyboardTransition(
                state = base.afterTextCommitted(),
                command = EditorCommand.CommitText(" "),
            )
            KeyboardAction.DoubleSpaceTap -> reduceDoubleSpaceTap(base, editorContext)
            KeyboardAction.Delete -> if (base.pendingDoubleSpaceUndo) {
                KeyboardTransition(
                    state = base.clearDoubleSpaceUndo(),
                    command = EditorCommand.RevertDoubleSpacePeriod,
                )
            } else {
                KeyboardTransition(
                    state = base,
                    command = EditorCommand.DeletePreviousCodePoint,
                )
            }
            KeyboardAction.Enter -> KeyboardTransition(
                state = base,
                command = resolveEnterCommand(editorContext),
            )
            KeyboardAction.Shift -> KeyboardTransition(base.onShiftPressed(nowMillis))
            KeyboardAction.ToggleSymbols -> KeyboardTransition(base.toggleSymbols())
            KeyboardAction.ToggleSymbolsPage -> KeyboardTransition(base.toggleSymbolsPage())
            is KeyboardAction.SwitchLanguage -> KeyboardTransition(base.switchLanguage(action.direction))
            is KeyboardAction.MoveCursor -> KeyboardTransition(
                state = base,
                command = EditorCommand.MoveCursor(action.steps),
            )
            KeyboardAction.HideKeyboard -> KeyboardTransition(
                state = base,
                command = EditorCommand.HideKeyboard,
            )
            KeyboardAction.NextInputMethod -> KeyboardTransition(
                state = base,
                command = EditorCommand.SwitchToNextInputMethod,
            )
        }
    }

    private fun reduceDoubleSpaceTap(
        state: KeyboardState,
        editorContext: EditorContext,
    ): KeyboardTransition {
        val eligible = state.doubleSpacePeriodEnabled && editorContext.supportsDoubleSpacePeriod
        return if (eligible) {
            KeyboardTransition(
                state = state.afterTextCommitted().copy(pendingDoubleSpaceUndo = true),
                command = EditorCommand.ConvertPrecedingSpaceToPeriod,
            )
        } else {
            KeyboardTransition(
                state = state.afterTextCommitted(),
                command = EditorCommand.CommitText(" "),
            )
        }
    }

    fun resolveEnterCommand(editorContext: EditorContext): EditorCommand {
        val suppressAction = editorContext.imeOptions and EditorInfo.IME_FLAG_NO_ENTER_ACTION != 0
        // A multi-line field needs the enter key for newlines; apps surface their action elsewhere.
        return if (suppressAction || editorContext.isMultiLine) {
            EditorCommand.InsertNewline
        } else {
            editorContext.customActionId?.let(EditorCommand::PerformEditorAction)
                ?: resolveEnterCommand(editorContext.imeOptions)
        }
    }

    fun resolveEnterCommand(imeOptions: Int): EditorCommand {
        val actionId = imeOptions and EditorInfo.IME_MASK_ACTION
        val suppressAction = imeOptions and EditorInfo.IME_FLAG_NO_ENTER_ACTION != 0
        return if (!suppressAction && actionId in EditorInfo.IME_ACTION_GO..EditorInfo.IME_ACTION_PREVIOUS) {
            EditorCommand.PerformEditorAction(actionId)
        } else {
            EditorCommand.InsertNewline
        }
    }
}
