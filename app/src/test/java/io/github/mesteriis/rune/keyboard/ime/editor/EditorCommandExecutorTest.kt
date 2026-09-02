package io.github.mesteriis.rune.keyboard.ime.editor

import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import java.lang.reflect.InvocationHandler
import java.lang.reflect.Proxy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EditorCommandExecutorTest {
    @Test
    fun `insert newline clears selection after successful commit`() {
        val connection = RecordingInputConnection(commitTextResult = true)

        val result = EditorCommandExecutor.execute(
            command = EditorCommand.InsertNewline,
            inputConnection = connection.proxy,
            hasSelection = true,
            requiresRawKeyEvents = false,
        )

        assertTrue(result.handled)
        assertTrue(result.clearsSelection)
        assertEquals(listOf("\n"), connection.committedText)
    }

    @Test
    fun `editor action fallback clears selection after successful newline`() {
        val connection = RecordingInputConnection(
            performEditorActionResult = false,
            commitTextResult = true,
        )

        val result = EditorCommandExecutor.execute(
            command = EditorCommand.PerformEditorAction(42),
            inputConnection = connection.proxy,
            hasSelection = true,
            requiresRawKeyEvents = false,
        )

        assertTrue(result.handled)
        assertTrue(result.clearsSelection)
        assertEquals(listOf(42), connection.editorActions)
        assertEquals(listOf("\n"), connection.committedText)
    }

    @Test
    fun `handled editor action preserves selection`() {
        val connection = RecordingInputConnection(performEditorActionResult = true)

        val result = EditorCommandExecutor.execute(
            command = EditorCommand.PerformEditorAction(42),
            inputConnection = connection.proxy,
            hasSelection = true,
            requiresRawKeyEvents = false,
        )

        assertTrue(result.handled)
        assertFalse(result.clearsSelection)
        assertTrue(connection.committedText.isEmpty())
    }

    @Test
    fun `double space fallback cannot transform unowned editor text or read it`() {
        val connection = RecordingInputConnection(commitTextResult = true, textBeforeCursor = "d ")
        val result = EditorCommandExecutor.execute(
            command = EditorCommand.ConvertPrecedingSpaceToPeriod,
            inputConnection = connection.proxy,
            hasSelection = false,
            requiresRawKeyEvents = false,
        )
        assertTrue(result.handled)
        assertEquals(listOf(" "), connection.committedText)
        assertTrue(connection.deletedSurroundingText.isEmpty())
        assertEquals(0, connection.batchEdits)
        assertEquals(0, connection.textReads)
    }

    @Test
    fun `cursor plan maps direction and step count to arrow keys`() {
        val left = EditorCommandExecutor.cursorKeyPlan(-3)
        val right = EditorCommandExecutor.cursorKeyPlan(2)

        assertEquals(KeyEvent.KEYCODE_DPAD_LEFT, left.keyCode)
        assertEquals(3, left.presses)
        assertEquals(KeyEvent.KEYCODE_DPAD_RIGHT, right.keyCode)
        assertEquals(2, right.presses)
    }

    private class RecordingInputConnection(
        private val performEditorActionResult: Boolean = false,
        private val commitTextResult: Boolean = false,
        private val textBeforeCursor: String? = null,
        private val deleteSurroundingTextResult: Boolean = false,
        private val deleteSurroundingTextInCodePointsResult: Boolean = false,
    ) : InvocationHandler {
        val committedText = mutableListOf<String>()
        val editorActions = mutableListOf<Int>()
        val deletedSurroundingText = mutableListOf<Pair<Int, Int>>()
        val deletedCodePoints = mutableListOf<Pair<Int, Int>>()
        var textReads = 0
            private set
        var batchEdits = 0
            private set

        val proxy: InputConnection = Proxy.newProxyInstance(
            InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java),
            this,
        ) as InputConnection

        override fun invoke(proxy: Any, method: java.lang.reflect.Method, args: Array<out Any?>?): Any? =
            when (method.name) {
                "commitText" -> {
                    committedText += args?.get(0).toString()
                    commitTextResult
                }
                "performEditorAction" -> {
                    editorActions += args?.get(0) as Int
                    performEditorActionResult
                }
                "getTextBeforeCursor" -> { textReads++; textBeforeCursor }
                "deleteSurroundingText" -> {
                    deletedSurroundingText += (args?.get(0) as Int) to (args[1] as Int)
                    deleteSurroundingTextResult
                }
                "deleteSurroundingTextInCodePoints" -> {
                    deletedCodePoints += (args?.get(0) as Int) to (args[1] as Int)
                    deleteSurroundingTextInCodePointsResult
                }
                "beginBatchEdit" -> {
                    batchEdits++
                    true
                }
                "endBatchEdit" -> false
                "sendKeyEvent" -> false
                "toString" -> "RecordingInputConnection"
                "hashCode" -> System.identityHashCode(this)
                "equals" -> proxy === args?.get(0)
                else -> defaultValue(method.returnType)
            }

        private fun defaultValue(returnType: Class<*>): Any? = when (returnType) {
            Boolean::class.javaPrimitiveType -> false
            Int::class.javaPrimitiveType -> 0
            Long::class.javaPrimitiveType -> 0L
            else -> null
        }
    }
}
