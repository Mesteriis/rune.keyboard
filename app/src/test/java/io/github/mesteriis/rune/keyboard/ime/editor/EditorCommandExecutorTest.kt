package io.github.mesteriis.rune.keyboard.ime.editor

import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import android.view.inputmethod.EditorInfo
import java.lang.reflect.InvocationHandler
import java.lang.reflect.Proxy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EditorCommandExecutorTest {
    @Test fun `owned batch checks guard between writes and ends on the original connection`() {
        for (loseOwnership in listOf(false, true)) {
            val calls = mutableListOf<String>()
            var current = true
            val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
                arrayOf(InputConnection::class.java)) { _, method, _ ->
                calls.add(method.name)
                if (method.name == "commitText" && loseOwnership) current = false
                method.name != "endBatchEdit"
            } as InputConnection
            val command = EditorCommand.Batch(listOf(EditorCommand.CommitText("word "),
                EditorCommand.SetComposingRegion(4, 5))) { current }
            val result = EditorCommandExecutor.execute(command, connection, false, false)
            assertEquals(!loseOwnership, result.handled)
            assertEquals(if (loseOwnership) listOf("beginBatchEdit", "commitText", "endBatchEdit") else
                listOf("beginBatchEdit", "commitText", "setComposingRegion", "endBatchEdit"), calls)
        }
    }

    @Test fun `batch privacy raw selection and stale guard reject before touching connection`() {
        val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java)) { _, _, _ -> throw AssertionError("Forbidden connection operation") } as InputConnection
        for (case in 0..4) {
            val command = EditorCommand.Batch(listOf(EditorCommand.SetComposingText("word"))) { case != 4 }
            val policy = when (case) {
                0 -> InputPolicy.SENSITIVE
                1 -> EditorContext.from(1, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING).inputPolicy
                else -> InputPolicy.NORMAL
            }
            assertFalse(EditorCommandExecutor.execute(command, connection, case == 2, case == 3, policy).handled)
        }
    }

    @Test fun `batch editor exception stops remaining writes and attempts cleanup`() {
        for (failure in listOf("beginBatchEdit", "commitText", "setComposingRegion", "endBatchEdit")) {
            val calls = mutableListOf<String>()
            val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
                arrayOf(InputConnection::class.java)) { _, method, _ ->
                calls.add(method.name)
                if (method.name == failure) throw IllegalStateException("Synthetic editor failure")
                true
            } as InputConnection
            val command = EditorCommand.Batch(listOf(EditorCommand.CommitText("word "), EditorCommand.SetComposingRegion(4, 5))) { true }
            assertFalse(EditorCommandExecutor.execute(command, connection, false, false).handled)
            if (failure == "beginBatchEdit") assertEquals(listOf("beginBatchEdit"), calls)
            else assertEquals("endBatchEdit", calls.last())
            if (failure == "commitText") assertFalse("setComposingRegion" in calls)
        }
    }

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
