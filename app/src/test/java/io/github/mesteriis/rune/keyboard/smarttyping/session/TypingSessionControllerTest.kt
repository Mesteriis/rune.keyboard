package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.text.InputType
import android.view.inputmethod.EditorInfo
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TypingSessionControllerTest {
    private val controller = TypingSessionController(jvmGraphemes)
    private val edits = mutableListOf<TypingEdit>()
    private val execute: (TypingEdit) -> Boolean = { edits.add(it); true }

    @Test
    fun `first letter composes and following letters replace only that span`() {
        start()
        assertEquals(TypingTextResult.HANDLED, controller.typeText("п", execute))
        controller.typeText("р", execute)
        assertEquals(listOf(TypingEdit.SetComposingText("п"), TypingEdit.SetComposingText("пр")), edits)
        assertEquals("пр", controller.state.composing?.typedWord)
        assertEquals("пр", controller.state.contextText)
    }

    @Test
    fun `space creates visible pending boundary and next word replaces it without duplication`() {
        start()
        controller.typeText("Я", execute)
        controller.typeText(" ", execute)
        assertEquals(ComposingSegment(" ", ""), controller.state.composing)
        controller.typeText("думаю", execute)
        assertEquals(
            listOf(TypingEdit.SetComposingText("Я"), TypingEdit.FinishComposingText,
                TypingEdit.SetComposingText(" "), TypingEdit.SetComposingText(" думаю")), edits,
        )
        assertEquals("Я думаю", controller.state.contextText)
    }

    @Test
    fun `repeated spaces finish previous pending boundary instead of duplicating it`() {
        start()
        controller.typeText(" ", execute)
        controller.typeText(" ", execute)
        assertEquals("  ", controller.state.contextText)
        assertEquals(ComposingSegment(" ", ""), controller.state.composing)
        assertEquals(listOf(TypingEdit.SetComposingText(" "), TypingEdit.FinishComposingText,
            TypingEdit.SetComposingText(" ")), edits)
    }

    @Test
    fun `delayed coalesced and duplicate own callbacks preserve newest composing word`() {
        start(10, 10)
        controller.typeText("a", execute)
        controller.typeText("b", execute)
        controller.typeText("c", execute)
        assertFalse(selection(11, 11, 10, 11))
        assertFalse(selection(13, 13, 10, 13))
        assertFalse(selection(13, 13, 10, 13))
        controller.typeText("d", execute)
        assertFalse(selection(14, 14, 10, 14))
        assertEquals("abcd", controller.state.composing?.text)
        assertEquals("abcd", controller.state.contextText)
    }

    @Test
    fun `rapid typing and delayed acknowledgement across words retain ownership`() {
        start()
        repeat(50) { controller.typeText("abc", execute); controller.typeText(" ", execute) }
        assertFalse(selection(3, 3, 0, 3))
        assertFalse(selection(3, 3, -1, -1))
        assertFalse(selection(200, 200, 199, 200))
        controller.typeText("z", execute)
        assertFalse(selection(201, 201, 199, 201))
        assertEquals(" z", controller.state.composing?.text)
    }

    @Test
    fun `synchronous own callback is acknowledged before command result`() {
        start()
        val synchronous: (TypingEdit) -> Boolean = {
            assertFalse(selection(1, 1, 0, 1))
            true
        }
        assertEquals(TypingTextResult.HANDLED, controller.typeText("a", synchronous))
        assertEquals("a", controller.state.contextText)
    }

    @Test
    fun `synchronous external callback cannot resurrect the in flight buffer`() {
        start()
        controller.typeText("a") {
            assertTrue(selection(7, 7, -1, -1))
            true
        }
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
        assertFalse(controller.state.enabled)
    }

    @Test
    fun `editor switch during word finish prevents pending boundary in new sensitive session`() {
        start()
        controller.typeText("old", execute)
        val result = controller.typeText(" ") { edit ->
            edits.add(edit)
            controller.startSession(
                EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD, 0),
                0,
                0,
            )
            true
        }
        assertEquals(TypingTextResult.REJECTED, result)
        assertEquals(2, edits.size)
        assertEquals(TypingEdit.FinishComposingText, edits.last())
        assertFalse(controller.state.enabled)
        assertEquals("", controller.state.contextText)
        assertNull(controller.state.composing)
    }

    @Test
    fun `cursor move finishes a still owned span and clears context`() {
        start()
        controller.typeText("hello", execute)
        val revision = controller.state.revision
        assertTrue(selection(2, 2, 0, 5))
        assertEquals(TypingEdit.FinishComposingText, edits.last())
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
        assertTrue(controller.state.revision > revision)
        controller.typeText("x", execute)
        assertEquals("x", controller.state.composing?.text)
        assertFalse(selection(3, 3, 2, 3))
    }

    @Test
    fun `loss of composing region abandons buffer without writing it back`() {
        start()
        controller.typeText("abc", execute)
        assertTrue(selection(3, 3, -1, -1))
        assertEquals(1, edits.size)
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
        assertFalse(controller.state.enabled)
        assertEquals(TypingTextResult.BYPASS, controller.typeText("d", execute))
    }

    @Test
    fun `external replacement composing span is never finished or overwritten`() {
        start()
        controller.typeText("abc", execute)
        assertTrue(selection(8, 8, 6, 8))
        assertEquals(1, edits.size)
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
        assertFalse(controller.state.enabled)
    }

    @Test
    fun `editor rewrite to an acknowledged older span invalidates instead of matching history`() {
        start()
        controller.typeText("a", execute)
        assertFalse(selection(1, 1, 0, 1))
        controller.typeText("b", execute)
        assertFalse(selection(2, 2, 0, 2))
        assertTrue(selection(1, 1, 0, 1))
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
        assertFalse(controller.state.enabled)
    }

    @Test
    fun `coalesced acknowledgement retires skipped historical snapshots`() {
        start()
        controller.typeText("a", execute)
        controller.typeText("b", execute)
        controller.typeText("c", execute)
        assertFalse(selection(3, 3, 0, 3))
        assertTrue(selection(1, 1, 0, 1))
        assertNull(controller.state.composing)
        assertFalse(controller.state.enabled)
    }

    @Test
    fun `known initial selection can be replaced and subsequent ownership starts at minimum bound`() {
        start(9, 4)
        controller.typeText("a", execute)
        assertFalse(selection(5, 5, 4, 5))
        assertEquals("a", controller.state.contextText)
    }

    @Test
    fun `unknown initial selection bypasses without retaining input`() {
        start(-1, -1)
        assertEquals(TypingTextResult.BYPASS, controller.typeText("private", execute))
        assertTrue(edits.isEmpty())
        assertFalse(controller.state.enabled)
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `sensitive raw email URI and numeric editors bypass with no retained content`() {
        val editors = listOf(
            EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD, 0),
            EditorContext.from(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING),
            EditorContext.from(InputType.TYPE_NULL, 0),
            EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS, 0),
            EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI, 0),
            EditorContext.from(InputType.TYPE_CLASS_NUMBER, 0),
        )
        for (editor in editors) {
            controller.startSession(editor, 0, 0)
            assertEquals(TypingTextResult.BYPASS, controller.typeText("private", execute))
            assertEquals(TypingTextResult.BYPASS, controller.deletePrevious(execute))
            assertEquals("", controller.state.contextText)
            assertNull(controller.state.composing)
        }
        assertTrue(edits.isEmpty())
    }

    @Test
    fun `rejected composition disables only current session and never replays accepted buffer`() {
        start()
        controller.typeText("a", execute)
        val reject: (TypingEdit) -> Boolean = { edits.add(it); false }
        assertEquals(TypingTextResult.REJECTED, controller.typeText("b", reject))
        assertEquals(listOf(TypingEdit.SetComposingText("a"), TypingEdit.SetComposingText("ab"),
            TypingEdit.FinishComposingText), edits)
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
        assertFalse(controller.state.enabled)
        assertEquals(TypingTextResult.BYPASS, controller.typeText("c", execute))
        start()
        assertEquals(TypingTextResult.HANDLED, controller.typeText("d", execute))
    }

    @Test
    fun `rejected finish stops a following boundary from being inserted`() {
        start()
        controller.typeText("a", execute)
        assertEquals(TypingTextResult.REJECTED, controller.typeText(" ") { edits.add(it); false })
        assertEquals(TypingEdit.FinishComposingText, edits.last())
        assertEquals(2, edits.size)
        assertFalse(controller.state.enabled)
    }

    @Test
    fun `finish boundaries invalidate revision and context can be explicitly cleared`() {
        start()
        controller.typeText("word", execute)
        val revision = controller.state.revision
        assertTrue(controller.finishComposition(execute))
        assertTrue(controller.state.revision > revision)
        assertNull(controller.state.composing)
        assertEquals("word", controller.state.contextText)
        assertTrue(controller.invalidate(execute))
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `restart and end destroy buffers and session IDs increase`() {
        start()
        controller.typeText("first", execute)
        val first = controller.state
        start()
        assertTrue(controller.state.sessionId > first.sessionId)
        assertTrue(controller.state.revision > first.revision)
        assertEquals("", controller.state.contextText)
        controller.typeText("second", execute)
        controller.endSession()
        assertFalse(controller.state.enabled)
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `backspace removes a decomposed grapheme including its base`() {
        start()
        controller.typeText("e", execute)
        controller.typeText("\u0301", execute)
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        assertEquals(TypingEdit.SetComposingText(""), edits[edits.lastIndex - 1])
        assertEquals(TypingEdit.FinishComposingText, edits.last())
        assertNull(controller.state.composing)
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `backspace preserves boundary until word is empty then deletes pending space`() {
        start()
        controller.typeText("first", execute)
        controller.typeText(" ", execute)
        controller.typeText("a", execute)
        controller.deletePrevious(execute)
        assertEquals(ComposingSegment(" ", ""), controller.state.composing)
        assertEquals("first ", controller.state.contextText)
        controller.deletePrevious(execute)
        assertNull(controller.state.composing)
        assertEquals("first", controller.state.contextText)
        assertEquals(TypingTextResult.BYPASS, controller.deletePrevious(execute))
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `last grapheme deletion acknowledges intermediate empty composing span then finishes`() {
        start()
        controller.typeText("a", execute)
        assertFalse(selection(1, 1, 0, 1))
        val result = controller.deletePrevious { edit ->
            edits.add(edit)
            when (edit) {
                is TypingEdit.SetComposingText -> {
                    assertEquals("", edit.value)
                    assertFalse(selection(0, 0, 0, 0))
                }
                TypingEdit.FinishComposingText -> assertFalse(selection(0, 0, -1, -1))
                is TypingEdit.CommitText -> throw AssertionError("Unexpected commit")
            }
            true
        }
        assertEquals(TypingTextResult.HANDLED, result)
        assertTrue(controller.state.enabled)
        assertNull(controller.state.composing)
        controller.typeText("b", execute)
        assertFalse(selection(1, 1, 0, 1))
        assertEquals("b", controller.state.contextText)
    }

    @Test
    fun `last grapheme deletion also accepts editor removing empty span immediately`() {
        start()
        controller.typeText("a", execute)
        val result = controller.deletePrevious {
            assertFalse(selection(0, 0, -1, -1))
            true
        }
        assertEquals(TypingTextResult.HANDLED, result)
        assertTrue(controller.state.enabled)
        assertNull(controller.state.composing)
    }

    @Test
    fun `emoji and punctuation finish composing then commit without reading editor`() {
        start()
        controller.typeText("word", execute)
        controller.typeText("👩🏽‍💻", execute)
        assertEquals(listOf(TypingEdit.SetComposingText("word"), TypingEdit.FinishComposingText,
            TypingEdit.CommitText("👩🏽‍💻")), edits)
        assertNull(controller.state.composing)
        assertEquals("word👩🏽‍💻", controller.state.contextText)
    }

    @Test
    fun `composing overflow acknowledges plain word suffix until next boundary`() {
        start()
        controller.typeText("a".repeat(256), execute)
        assertEquals(TypingTextResult.HANDLED, controller.typeText("b", execute))
        assertNull(controller.state.composing)
        assertEquals("a".repeat(256) + "b", controller.state.contextText)
        assertEquals(TypingEdit.CommitText("b"), edits.last())
        controller.typeText("c", execute)
        assertEquals(TypingEdit.CommitText("c"), edits.last())
        assertFalse(selection(258, 258, -1, -1))
        controller.typeText(" ", execute)
        controller.typeText("d", execute)
        assertFalse(selection(260, 260, 258, 260))
        assertEquals(" d", controller.state.composing?.text)
    }

    @Test
    fun `unknown plain deletion suspends composing until changed selection arrives`() {
        start()
        controller.typeText("abc", execute)
        controller.finishComposition(execute)
        assertEquals(TypingTextResult.BYPASS, controller.deletePrevious(execute))
        assertFalse(selection(3, 3, 0, 3)) // delayed own callback predating deletion
        assertFalse(selection(3, 3, -1, -1))
        assertEquals(TypingTextResult.BYPASS, controller.typeText("d", execute))
        assertEquals("", controller.state.contextText)
        assertTrue(selection(2, 2, -1, -1))
        assertEquals(TypingTextResult.HANDLED, controller.typeText("x", execute))
        assertFalse(selection(3, 3, 2, 3))
        assertEquals("x", controller.state.contextText)
    }

    @Test
    fun `legacy mutation wait clears context and ignores stale own acknowledgements`() {
        start()
        controller.typeText("a", execute)
        assertTrue(controller.awaitEditorSelection(execute))
        assertFalse(selection(1, 1, 0, 1))
        assertFalse(selection(1, 1, -1, -1))
        assertEquals(TypingTextResult.BYPASS, controller.typeText("b", execute))
        assertTrue(selection(0, 0, -1, -1))
        controller.typeText("c", execute)
        assertFalse(selection(1, 1, 0, 1))
        assertEquals("c", controller.state.contextText)
    }

    @Test
    fun `legacy double space acknowledges known delta and next word starts at updated caret`() {
        start()
        controller.typeText("word", execute)
        controller.typeText(" ", execute)
        var boundaryCalls = 0
        val result = controller.legacyDoubleSpace(execute) {
            boundaryCalls++
            true
        }
        assertEquals(TypingTextResult.HANDLED, result)
        assertEquals(1, boundaryCalls)
        assertEquals(TypingEdit.FinishComposingText, edits.last())
        assertFalse(selection(6, 6, -1, -1))
        assertEquals("", controller.state.contextText)
        assertNull(controller.state.composing)
        controller.typeText("x", execute)
        assertFalse(selection(7, 7, 6, 7))
        assertEquals("x", controller.state.contextText)
    }

    @Test
    fun `legacy double space handles synchronous callback and delayed following typing`() {
        start(10)
        controller.typeText("a", execute)
        controller.typeText(" ", execute)
        assertEquals(TypingTextResult.HANDLED, controller.legacyDoubleSpace(execute) {
            assertFalse(selection(13, 13, -1, -1))
            true
        })
        controller.typeText("b", execute)
        controller.typeText("c", execute)
        assertFalse(selection(15, 15, 13, 15))
        assertEquals("bc", controller.state.composing?.text)
    }

    @Test
    fun `legacy double space bypasses uncertain selection without invoking boundary`() {
        start(4, 7)
        var boundaryCalls = 0
        assertEquals(TypingTextResult.BYPASS, controller.legacyDoubleSpace(execute) {
            boundaryCalls++
            true
        })
        assertEquals(0, boundaryCalls)
        assertEquals(TypingTextResult.BYPASS, controller.typeText("a", execute))
        assertEquals("", controller.state.contextText)
        assertTrue(selection(5, 5, -1, -1))
        assertEquals(TypingTextResult.HANDLED, controller.typeText("b", execute))
        assertFalse(selection(6, 6, 5, 6))
    }

    @Test
    fun `legacy double space aborts if session changes while finishing word`() {
        start()
        controller.typeText("a", execute)
        var boundaryCalls = 0
        val result = controller.legacyDoubleSpace(
            executeTypingEdit = {
                controller.endSession()
                true
            },
            executeBoundary = {
                boundaryCalls++
                true
            },
        )
        assertEquals(TypingTextResult.REJECTED, result)
        assertEquals(0, boundaryCalls)
        assertFalse(controller.state.enabled)
    }

    @Test
    fun `legacy double space cannot acknowledge into a session created during boundary execution`() {
        start()
        controller.typeText("a", execute)
        val result = controller.legacyDoubleSpace(execute) {
            start(20)
            true
        }
        assertEquals(TypingTextResult.REJECTED, result)
        controller.typeText("b", execute)
        assertFalse(selection(21, 21, 20, 21))
        assertEquals("b", controller.state.contextText)
    }

    @Test
    fun `legacy double space rejection disables stale caret tracking without replay`() {
        start()
        controller.typeText("a", execute)
        var boundaryCalls = 0
        val result = controller.legacyDoubleSpace(execute) {
            boundaryCalls++
            false
        }
        assertEquals(TypingTextResult.REJECTED, result)
        assertEquals(1, boundaryCalls)
        assertFalse(controller.state.enabled)
        assertEquals(TypingTextResult.BYPASS, controller.typeText("b", execute))
        assertEquals("", controller.state.contextText)
    }

    private fun start(start: Int = 0, end: Int = start) {
        controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), start, end)
    }

    private fun selection(start: Int, end: Int, composingStart: Int, composingEnd: Int): Boolean =
        controller.updateSelection(start, end, composingStart, composingEnd, execute)
}
