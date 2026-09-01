package io.github.mesteriis.rune.keyboard.ime.model

import android.text.InputType
import android.view.inputmethod.EditorInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class KeyboardReducerTest {
    private val textEditor = EditorContext.from(
        inputType = InputType.TYPE_CLASS_TEXT,
        imeOptions = EditorInfo.IME_ACTION_NONE,
    )

    @Test
    fun `character commits exact rendered text and consumes one-shot shift`() {
        val shifted = KeyboardState(KeyboardLanguage.ENGLISH).onShiftPressed(nowMillis = 1_000)

        val transition = KeyboardReducer.reduce(
            state = shifted,
            action = KeyboardAction.CommitText("A"),
            editorContext = textEditor,
            nowMillis = 1_100,
        )

        assertEquals(EditorCommand.CommitText("A"), transition.command)
        assertEquals(ShiftMode.OFF, transition.state.shiftMode)
    }

    @Test
    fun `explicit editor action is performed`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT,
            imeOptions = EditorInfo.IME_ACTION_SEARCH,
        )

        val transition = KeyboardReducer.reduce(
            state = KeyboardState(KeyboardLanguage.ENGLISH),
            action = KeyboardAction.Enter,
            editorContext = context,
            nowMillis = 0,
        )

        assertEquals(EditorCommand.PerformEditorAction(EditorInfo.IME_ACTION_SEARCH), transition.command)
    }

    @Test
    fun `no-enter-action flag inserts newline`() {
        val options = EditorInfo.IME_ACTION_DONE or EditorInfo.IME_FLAG_NO_ENTER_ACTION

        assertEquals(EditorCommand.InsertNewline, KeyboardReducer.resolveEnterCommand(options))
    }

    @Test
    fun `custom editor action has priority`() {
        val context = textEditor.copy(customActionId = 42, customActionLabel = "Apply")

        assertEquals(EditorCommand.PerformEditorAction(42), KeyboardReducer.resolveEnterCommand(context))
    }

    @Test
    fun `no-enter-action flag suppresses custom editor action`() {
        val context = textEditor.copy(
            imeOptions = EditorInfo.IME_ACTION_SEND or EditorInfo.IME_FLAG_NO_ENTER_ACTION,
            customActionId = 42,
            customActionLabel = "Apply",
        )

        assertEquals(EditorCommand.InsertNewline, KeyboardReducer.resolveEnterCommand(context))
    }

    @Test
    fun `multi-line editor keeps the enter key on newline`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )

        assertEquals(EditorCommand.InsertNewline, KeyboardReducer.resolveEnterCommand(context))
    }

    @Test
    fun `multi-line editor outranks a custom editor action`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
            imeOptions = EditorInfo.IME_ACTION_SEND,
        ).copy(customActionId = 7, customActionLabel = "Apply")

        assertEquals(EditorCommand.InsertNewline, KeyboardReducer.resolveEnterCommand(context))
    }

    @Test
    fun `single-line editor still performs its action`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )

        assertEquals(
            EditorCommand.PerformEditorAction(EditorInfo.IME_ACTION_DONE),
            KeyboardReducer.resolveEnterCommand(context),
        )
    }

    @Test
    fun `overlapping letters resolve case from latest state`() {
        val initialState = KeyboardState.initial(
            language = KeyboardLanguage.ENGLISH,
            automaticCapitalization = true,
        )
        val first = KeyboardReducer.reduce(
            state = initialState,
            action = KeyboardAction.CommitLetter("a"),
            editorContext = textEditor,
            nowMillis = 0,
        )
        val second = KeyboardReducer.reduce(
            state = first.state,
            action = KeyboardAction.CommitLetter("b"),
            editorContext = textEditor,
            nowMillis = 1,
        )

        assertEquals(EditorCommand.CommitText("A"), first.command)
        assertEquals(EditorCommand.CommitText("b"), second.command)
    }

    @Test
    fun `spanish accent commits uppercase through the locale`() {
        val state = KeyboardState(
            language = KeyboardLanguage.SPANISH,
            shiftMode = ShiftMode.ONCE,
        )

        val transition = KeyboardReducer.reduce(
            state = state,
            action = KeyboardAction.CommitLetter("ñ"),
            editorContext = textEditor,
            nowMillis = 0,
        )

        assertEquals(EditorCommand.CommitText("Ñ"), transition.command)
        assertEquals(ShiftMode.OFF, transition.state.shiftMode)
    }

    @Test
    fun `delete maps to Unicode-aware delete command`() {
        val transition = KeyboardReducer.reduce(
            state = KeyboardState(KeyboardLanguage.ENGLISH),
            action = KeyboardAction.Delete,
            editorContext = textEditor,
            nowMillis = 0,
        )

        assertTrue(transition.command is EditorCommand.DeletePreviousCodePoint)
    }

    @Test
    fun `double space converts the preceding space in plain text`() {
        val transition = reduceDoubleSpace(KeyboardState(KeyboardLanguage.ENGLISH), textEditor)

        assertEquals(EditorCommand.ConvertPrecedingSpaceToPeriod, transition.command)
        assertTrue(transition.state.pendingDoubleSpaceUndo)
    }

    @Test
    fun `double space commits a plain space in ineligible editors`() {
        val ineligible = listOf(
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI,
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD,
            InputType.TYPE_CLASS_NUMBER,
            InputType.TYPE_CLASS_PHONE,
            InputType.TYPE_CLASS_DATETIME,
            InputType.TYPE_NULL,
        )

        ineligible.forEach { inputType ->
            val context = EditorContext.from(inputType, EditorInfo.IME_ACTION_NONE)
            val transition = reduceDoubleSpace(KeyboardState(KeyboardLanguage.ENGLISH), context)

            assertEquals(EditorCommand.CommitText(" "), transition.command)
            assertFalse(transition.state.pendingDoubleSpaceUndo)
        }
    }

    @Test
    fun `double space commits a plain space when the setting is off`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH, doubleSpacePeriodEnabled = false)

        val transition = reduceDoubleSpace(state, textEditor)

        assertEquals(EditorCommand.CommitText(" "), transition.command)
        assertFalse(transition.state.pendingDoubleSpaceUndo)
    }

    @Test
    fun `backspace right after a double space reverts it`() {
        val converted = reduceDoubleSpace(KeyboardState(KeyboardLanguage.ENGLISH), textEditor).state

        val transition = KeyboardReducer.reduce(
            state = converted,
            action = KeyboardAction.Delete,
            editorContext = textEditor,
            nowMillis = 1,
        )

        assertEquals(EditorCommand.RevertDoubleSpacePeriod, transition.command)
        assertFalse(transition.state.pendingDoubleSpaceUndo)
    }

    @Test
    fun `any other action clears the pending double space undo`() {
        val converted = reduceDoubleSpace(KeyboardState(KeyboardLanguage.ENGLISH), textEditor).state

        val transition = KeyboardReducer.reduce(
            state = converted,
            action = KeyboardAction.CommitLetter("a"),
            editorContext = textEditor,
            nowMillis = 1,
        )

        assertFalse(transition.state.pendingDoubleSpaceUndo)

        val afterDelete = KeyboardReducer.reduce(
            state = transition.state,
            action = KeyboardAction.Delete,
            editorContext = textEditor,
            nowMillis = 2,
        )

        assertEquals(EditorCommand.DeletePreviousCodePoint, afterDelete.command)
    }

    @Test
    fun `cursor movement passes through without touching state`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.LOCKED)

        val transition = KeyboardReducer.reduce(
            state = state,
            action = KeyboardAction.MoveCursor(-3),
            editorContext = textEditor,
            nowMillis = 0,
        )

        assertEquals(EditorCommand.MoveCursor(-3), transition.command)
        assertEquals(state, transition.state)
    }

    @Test
    fun `hide keyboard emits the hide command`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH)

        val transition = KeyboardReducer.reduce(
            state = state,
            action = KeyboardAction.HideKeyboard,
            editorContext = textEditor,
            nowMillis = 0,
        )

        assertEquals(EditorCommand.HideKeyboard, transition.command)
        assertEquals(state, transition.state)
    }

    @Test
    fun `language swipe cycles in the requested direction`() {
        val transition = KeyboardReducer.reduce(
            state = KeyboardState(KeyboardLanguage.ENGLISH),
            action = KeyboardAction.SwitchLanguage(LanguageDirection.PREVIOUS),
            editorContext = textEditor,
            nowMillis = 0,
        )

        assertEquals(KeyboardLanguage.SPANISH, transition.state.language)
        assertEquals(null, transition.command)
    }

    private fun reduceDoubleSpace(
        state: KeyboardState,
        editorContext: EditorContext,
    ): KeyboardTransition = KeyboardReducer.reduce(
        state = state,
        action = KeyboardAction.DoubleSpaceTap,
        editorContext = editorContext,
        nowMillis = 0,
    )
}
