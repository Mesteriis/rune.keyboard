package io.github.mesteriis.rune.keyboard.ime.editor

import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.model.CursorDirection
import io.github.mesteriis.rune.keyboard.ime.model.EditorContextAction
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
    @Test fun `exact editor action reports refusal or exception without inserting fallback text`() {
        for ((result, throws, expected) in listOf(
            Triple(true, false, EditorCommandExecutor.EditorActionResult.ACCEPTED),
            Triple(false, false, EditorCommandExecutor.EditorActionResult.REFUSED),
            Triple(false, true, EditorCommandExecutor.EditorActionResult.UNKNOWN))) {
            val calls = mutableListOf<String>()
            val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
                arrayOf(InputConnection::class.java)) { _, method, _ ->
                calls += method.name
                if (throws) throw IllegalStateException("synthetic")
                result
            } as InputConnection
            assertEquals(expected, EditorCommandExecutor.performEditorActionOnly(connection, 4))
            assertEquals(listOf("performEditorAction"), calls)
        }
    }

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
        for (case in listOf(0, 2, 3, 4)) {
            val command = EditorCommand.Batch(listOf(EditorCommand.SetComposingText("word"))) { case != 4 }
            val policy = when (case) {
                0 -> InputPolicy.SENSITIVE
                else -> InputPolicy.NORMAL
            }
            assertFalse(EditorCommandExecutor.execute(command, connection, case == 2, case == 3, policy).handled)
        }
    }

    @Test fun `incognito permits owned composing batch but forces deletion without reads`() {
        val calls = mutableListOf<String>()
        val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java)) { _, method, _ ->
            check(method.name in setOf("beginBatchEdit", "setComposingText", "setComposingRegion",
                "finishComposingText", "endBatchEdit", "deleteSurroundingTextInCodePoints"))
            calls += method.name
            true
        } as InputConnection
        val command = EditorCommand.Batch(listOf(EditorCommand.SetComposingText("word"),
            EditorCommand.SetComposingRegion(0, 4))) { true }
        assertTrue(EditorCommandExecutor.execute(command, connection, false, DeleteMode.GRAPHEME_AWARE,
            InputPolicy.INCOGNITO).handled)
        assertEquals(listOf("beginBatchEdit", "setComposingText", "setComposingRegion", "endBatchEdit"), calls)
        assertTrue(EditorCommandExecutor.execute(EditorCommand.FinishComposingText, connection, false,
            DeleteMode.GRAPHEME_AWARE, InputPolicy.INCOGNITO).handled)
        calls.clear()
        assertTrue(EditorCommandExecutor.execute(EditorCommand.DeletePreviousCodePoint, connection, false,
            DeleteMode.GRAPHEME_AWARE, InputPolicy.INCOGNITO).handled)
        assertEquals(listOf("deleteSurroundingTextInCodePoints"), calls)
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

    @Test fun navigationUsesEditorKeyDirectionsAndNoSyntheticSelectionMetadata() {
        val expected = mapOf(CursorDirection.LEFT to KeyEvent.KEYCODE_DPAD_LEFT,
            CursorDirection.RIGHT to KeyEvent.KEYCODE_DPAD_RIGHT, CursorDirection.UP to KeyEvent.KEYCODE_DPAD_UP,
            CursorDirection.DOWN to KeyEvent.KEYCODE_DPAD_DOWN, CursorDirection.HOME to KeyEvent.KEYCODE_MOVE_HOME,
            CursorDirection.END to KeyEvent.KEYCODE_MOVE_END)
        for ((direction, code) in expected) for (extend in listOf(false, true)) {
            val events = mutableListOf<Triple<Int, Int, Int>>()
            assertTrue(EditorCommandExecutor.dispatchNavigation(EditorCommand.NavigateCursor(direction, extend)) { action, key, meta ->
                events += Triple(action, key, meta); true
            })
            val meta = if (extend) KeyEvent.META_SHIFT_ON else 0
            val arrows = listOf(Triple(KeyEvent.ACTION_DOWN, code, meta), Triple(KeyEvent.ACTION_UP, code, meta))
            val plan = if (extend) listOf(Triple(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_SHIFT_LEFT, meta)) + arrows +
                Triple(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_SHIFT_LEFT, 0) else arrows
            assertEquals(plan, events)
        }
    }

    @Test fun navigationRefusalOrExceptionAlwaysAttemptsReleasesAndNeverRetries() {
        for (failure in 0..3) for (throws in listOf(false, true)) {
            val events = mutableListOf<Pair<Int, Int>>()
            val handled = EditorCommandExecutor.dispatchNavigation(EditorCommand.NavigateCursor(CursorDirection.LEFT, true)) { action, key, _ ->
                val index = events.size
                events += action to key
                if (index == failure && throws) throw IllegalStateException("synthetic")
                index != failure
            }
            assertFalse(handled)
            assertEquals(KeyEvent.ACTION_UP to KeyEvent.KEYCODE_SHIFT_LEFT, events.last())
            assertEquals(if (failure == 0) 2 else 4, events.size)
            if (failure != 0) assertEquals(KeyEvent.ACTION_UP to KeyEvent.KEYCODE_DPAD_LEFT, events[2])
        }
    }

    @Test fun ordinaryNavigationAlsoReleasesARefusedOrThrowingArrowDown() {
        for (throws in listOf(false, true)) {
            val actions = mutableListOf<Int>()
            assertFalse(EditorCommandExecutor.dispatchNavigation(EditorCommand.NavigateCursor(CursorDirection.END)) { action, _, meta ->
                assertEquals(0, meta)
                actions += action
                if (action == KeyEvent.ACTION_DOWN && throws) throw IllegalStateException("synthetic")
                action != KeyEvent.ACTION_DOWN
            })
            assertEquals(listOf(KeyEvent.ACTION_DOWN, KeyEvent.ACTION_UP), actions)
        }
    }

    @Test fun contextMenuDispatchesOnlyTheNamedEditorActionWithoutReadsOrSelectionClaims() {
        val ids = mapOf(EditorContextAction.SELECT_ALL to android.R.id.selectAll,
            EditorContextAction.COPY to android.R.id.copy, EditorContextAction.CUT to android.R.id.cut,
            EditorContextAction.PASTE to android.R.id.paste)
        for ((action, id) in ids) for (policy in listOf(InputPolicy.NORMAL, InputPolicy.INCOGNITO)) {
            for (accepted in listOf(false, true)) {
                val calls = mutableListOf<Pair<String, Int>>()
                val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
                    arrayOf(InputConnection::class.java)) { _, method, args ->
                    check(method.name == "performContextMenuAction") { "Unexpected editor operation" }
                    calls += method.name to (args!![0] as Int)
                    accepted
                } as InputConnection
                val result = EditorCommandExecutor.execute(EditorCommand.ContextMenu(action), connection, true, false, policy)
                assertEquals(accepted, result.handled)
                assertFalse(result.clearsSelection)
                assertEquals(listOf("performContextMenuAction" to id), calls)
            }
        }
    }

    @Test fun rawAndSensitiveContextMenusRefuseBeforeTouchingTheEditor() {
        val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java)) { _, _, _ -> throw AssertionError("Forbidden editor call") } as InputConnection
        for (action in EditorContextAction.entries) {
            assertFalse(EditorCommandExecutor.execute(EditorCommand.ContextMenu(action), connection, false, true).handled)
            assertFalse(EditorCommandExecutor.execute(EditorCommand.ContextMenu(action), connection, false, false, InputPolicy.SENSITIVE).handled)
        }
    }

    @Test fun contextMenuExceptionReturnsUnknownFailureWithoutRetryOrSelectionReset() {
        var calls = 0
        val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java)) { _, method, _ ->
            check(method.name == "performContextMenuAction")
            calls++
            throw IllegalStateException("synthetic")
        } as InputConnection
        val result = EditorCommandExecutor.execute(EditorCommand.ContextMenu(EditorContextAction.PASTE), connection, true, false)
        assertFalse(result.handled)
        assertFalse(result.clearsSelection)
        assertEquals(1, calls)
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
