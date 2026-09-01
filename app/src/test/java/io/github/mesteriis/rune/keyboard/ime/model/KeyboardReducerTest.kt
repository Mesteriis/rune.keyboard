package io.github.mesteriis.rune.keyboard.ime.model

import android.text.InputType
import android.view.inputmethod.EditorInfo
import org.junit.Assert.assertEquals
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
    fun `delete maps to Unicode-aware delete command`() {
        val transition = KeyboardReducer.reduce(
            state = KeyboardState(KeyboardLanguage.ENGLISH),
            action = KeyboardAction.Delete,
            editorContext = textEditor,
            nowMillis = 0,
        )

        assertTrue(transition.command is EditorCommand.DeletePreviousCodePoint)
    }
}
