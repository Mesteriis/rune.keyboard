package io.github.mesteriis.rune.keyboard.ime.model

import android.view.inputmethod.EditorInfo

object KeyboardReducer {
    fun reduce(
        state: KeyboardState,
        action: KeyboardAction,
        editorContext: EditorContext,
        nowMillis: Long,
    ): KeyboardTransition = when (action) {
        is KeyboardAction.CommitLetter -> KeyboardTransition(
            state = state.afterTextCommitted(),
            command = EditorCommand.CommitText(
                if (state.shiftMode.usesUppercase) {
                    action.value.uppercase(state.language.locale)
                } else {
                    action.value.lowercase(state.language.locale)
                },
            ),
        )
        is KeyboardAction.CommitText -> KeyboardTransition(
            state = state.afterTextCommitted(),
            command = EditorCommand.CommitText(action.value),
        )
        KeyboardAction.Space -> KeyboardTransition(
            state = state.afterTextCommitted(),
            command = EditorCommand.CommitText(" "),
        )
        KeyboardAction.Delete -> KeyboardTransition(
            state = state,
            command = EditorCommand.DeletePreviousCodePoint,
        )
        KeyboardAction.Enter -> KeyboardTransition(
            state = state,
            command = resolveEnterCommand(editorContext),
        )
        KeyboardAction.Shift -> KeyboardTransition(state.onShiftPressed(nowMillis))
        KeyboardAction.ToggleSymbols -> KeyboardTransition(state.toggleSymbols())
        KeyboardAction.ToggleLanguage -> KeyboardTransition(state.toggleLanguage())
        KeyboardAction.NextInputMethod -> KeyboardTransition(
            state = state,
            command = EditorCommand.SwitchToNextInputMethod,
        )
    }

    fun resolveEnterCommand(editorContext: EditorContext): EditorCommand {
        val suppressAction = editorContext.imeOptions and EditorInfo.IME_FLAG_NO_ENTER_ACTION != 0
        return if (suppressAction) {
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
