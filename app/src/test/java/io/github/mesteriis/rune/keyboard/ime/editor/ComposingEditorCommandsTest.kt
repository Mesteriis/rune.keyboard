package io.github.mesteriis.rune.keyboard.ime.editor

import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import java.lang.reflect.Proxy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ComposingEditorCommandsTest {
    @Test
    fun `composing passes exact leading boundary and word once without reads`() {
        val editor = RecordingConnection()
        val result = execute(EditorCommand.SetComposingText(" это"), editor)

        assertTrue(result.handled)
        assertTrue(result.clearsSelection)
        assertEquals(listOf("setComposingText"), editor.calls)
        assertEquals(listOf(" это"), editor.payloads)
    }

    @Test
    fun `rejected composing is not replayed as commit`() {
        val editor = RecordingConnection(false)
        val result = execute(EditorCommand.SetComposingText("word"), editor)

        assertFalse(result.handled)
        assertFalse(result.clearsSelection)
        assertEquals(listOf("setComposingText"), editor.calls)
    }

    @Test
    fun `finish removes composing span without committing text or clearing selection`() {
        val editor = RecordingConnection()
        val result = execute(EditorCommand.FinishComposingText, editor)

        assertTrue(result.handled)
        assertFalse(result.clearsSelection)
        assertEquals(listOf("finishComposingText"), editor.calls)
        assertTrue(editor.payloads.isEmpty())
    }

    @Test
    fun `sensitive policy blocks composing and legacy automatic edit reads`() {
        val editor = RecordingConnection()
        assertFalse(execute(EditorCommand.SetComposingText("text"), editor, InputPolicy.SENSITIVE).handled)
        assertFalse(execute(EditorCommand.FinishComposingText, editor, InputPolicy.SENSITIVE).handled)
        execute(EditorCommand.ConvertPrecedingSpaceToPeriod, editor, InputPolicy.SENSITIVE)
        execute(EditorCommand.RevertDoubleSpacePeriod, editor, InputPolicy.SENSITIVE)
        execute(EditorCommand.DeletePreviousCodePoint, editor, InputPolicy.SENSITIVE)

        assertEquals(listOf("commitText", "deleteSurroundingTextInCodePoints", "deleteSurroundingTextInCodePoints"), editor.calls)
        assertEquals(listOf(" "), editor.payloads)
    }

    @Test
    fun `raw editor cannot receive a composing call`() {
        val editor = RecordingConnection()
        val result = EditorCommandExecutor.execute(
            EditorCommand.SetComposingText("a"), editor.proxy,
            hasSelection = false, deleteMode = DeleteMode.RAW_KEY_EVENT,
        )

        assertFalse(result.handled)
        assertTrue(editor.calls.isEmpty())
    }

    private fun execute(
        command: EditorCommand,
        editor: RecordingConnection,
        policy: InputPolicy = InputPolicy.NORMAL,
    ) = EditorCommandExecutor.execute(
        command, editor.proxy, hasSelection = false,
        deleteMode = DeleteMode.GRAPHEME_AWARE, inputPolicy = policy,
    )

    private class RecordingConnection(private val accepted: Boolean = true) {
        val calls = mutableListOf<String>()
        val payloads = mutableListOf<String>()
        val proxy: InputConnection = Proxy.newProxyInstance(
            InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java),
        ) { _, method, args ->
            calls += method.name
            if (method.name == "commitText" || method.name == "setComposingText") {
                payloads += args?.get(0).toString()
            }
            when (method.returnType) {
                Boolean::class.javaPrimitiveType -> accepted
                Int::class.javaPrimitiveType -> 0
                else -> null
            }
        } as InputConnection
    }
}
