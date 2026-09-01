package io.github.mesteriis.rune.keyboard.ime.editor

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

    private class RecordingInputConnection(
        private val performEditorActionResult: Boolean = false,
        private val commitTextResult: Boolean = false,
    ) : InvocationHandler {
        val committedText = mutableListOf<String>()
        val editorActions = mutableListOf<Int>()
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
