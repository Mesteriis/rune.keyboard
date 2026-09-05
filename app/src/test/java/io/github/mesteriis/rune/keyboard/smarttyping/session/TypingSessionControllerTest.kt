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
    fun `original candidate selection is scoped to current session and revision without editor writes`() {
        start()
        controller.typeText("ab", execute)
        val originalId = checkNotNull(controller.originalCandidateId)
        val count = edits.size
        assertTrue(controller.selectOriginal(originalId))
        assertTrue(controller.state.originalSelected)
        assertEquals(count, edits.size)
        assertFalse(controller.selectOriginal(originalId))
        assertTrue(originalId != controller.originalCandidateId)
        val currentId = checkNotNull(controller.originalCandidateId)
        start()
        assertFalse(controller.selectOriginal(currentId))
        assertNull(controller.originalCandidateId)
    }

    @Test
    fun `selecting original protects the same word until its next boundary`() {
        start()
        controller.typeText("ab", execute)
        assertTrue(controller.selectOriginal(checkNotNull(controller.originalCandidateId)))
        controller.typeText("c", execute)
        assertTrue(controller.state.originalSelected)
        controller.typeText(" ", execute)
        assertFalse(controller.state.originalSelected)
        assertNull(controller.originalCandidateId)
        controller.typeText("d", execute)
        assertFalse(controller.state.originalSelected)
        assertTrue(controller.originalCandidateId != null)
    }

    @Test
    fun `deleting the entire selected original does not protect a later word`() {
        start()
        controller.typeText("a", execute)
        controller.selectOriginal(checkNotNull(controller.originalCandidateId))
        controller.deletePrevious(execute)
        assertFalse(controller.state.originalSelected)
        assertNull(controller.originalCandidateId)
        controller.typeText("b", execute)
        assertFalse(controller.state.originalSelected)
    }

    @Test
    fun `editor invalidation rejects a pending original tap`() {
        start()
        controller.typeText("ab", execute)
        val id = checkNotNull(controller.originalCandidateId)
        selection(2, 2, -1, -1)
        assertFalse(controller.selectOriginal(id))
        assertNull(controller.originalCandidateId)
        assertFalse(controller.state.originalSelected)
    }

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
    fun `repeated spaces retain one pending boundary without duplicating it`() {
        start()
        controller.typeText(" ", execute)
        controller.typeText(" ", execute)
        assertEquals("  ", controller.state.contextText)
        assertEquals(ComposingSegment("  ", ""), controller.state.composing)
        assertEquals(listOf(TypingEdit.SetComposingText(" "), TypingEdit.SetComposingText("  ")), edits)
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
    fun `backspace preserves boundary until word is empty then reopens complete owned word`() {
        start()
        controller.typeText("first", execute)
        controller.typeText(" ", execute)
        controller.typeText("a", execute)
        controller.deletePrevious(execute)
        assertEquals(ComposingSegment(" ", ""), controller.state.composing)
        assertEquals("first ", controller.state.contextText)
        controller.deletePrevious(execute)
        assertEquals(ComposingSegment("", "first"), controller.state.composing)
        assertEquals("first", controller.state.contextText)
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        assertEquals("firs", controller.state.contextText)
    }

    @Test
    fun `pending space backspace reopens the whole previous word inside owned context`() {
        start()
        controller.typeText("hello", execute)
        controller.typeText(" ", execute)
        controller.typeText("first", execute)
        controller.typeText(" ", execute)

        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        assertEquals(ComposingSegment("", "first"), controller.state.composing)
        assertEquals("hello first", controller.state.contextText)
        val batch = edits.last() as TypingEdit.Batch
        assertEquals(listOf(TypingEdit.SetComposingText(""), TypingEdit.SetComposingRegion(6, 11)), batch.edits)
    }

    @Test
    fun `pending space does not claim a word whose left boundary predates Rune context`() {
        start(100, 100)
        controller.typeText("first", execute)
        controller.typeText(" ", execute)

        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        assertNull(controller.state.composing)
        assertEquals("first", controller.state.contextText)
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
                else -> throw AssertionError("Unexpected edit")
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
    fun `double space replaces only owned pending boundary and records one transaction`() {
        pendingSpace("word")
        val beforeRevision = controller.state.revision

        assertEquals(TypingTextResult.HANDLED, controller.doubleSpace(execute))

        assertEquals(listOf(TypingEdit.SetComposingText(". ")), edits)
        assertEquals(ComposingSegment(". "), controller.state.composing)
        assertEquals("word. ", controller.state.contextText)
        val undo = controller.state.lastAutoEdit!!
        assertEquals(" ", undo.original)
        assertEquals(". ", undo.applied)
        assertEquals(ComposingSegment(" "), undo.restoreComposition)
        assertEquals(controller.state.sessionId, undo.sessionId)
        assertEquals(controller.state.revision, undo.revision)
        assertTrue(undo.revision > beforeRevision)
    }

    @Test
    fun `first backspace restores original boundary and second reopens its owned word`() {
        pendingSpace("word")
        controller.doubleSpace(execute)
        edits.clear()

        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        assertEquals(listOf(TypingEdit.SetComposingText(" ")), edits)
        assertEquals("word ", controller.state.contextText)
        assertEquals(ComposingSegment(" "), controller.state.composing)
        assertNull(controller.state.lastAutoEdit)
        assertFalse(selection(5, 5, 4, 5))

        edits.clear()
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        val batch = edits.single() as TypingEdit.Batch
        assertEquals(listOf(TypingEdit.SetComposingText(""), TypingEdit.SetComposingRegion(0, 4)), batch.edits)
        assertEquals("word", controller.state.contextText)
        assertEquals(ComposingSegment("", "word"), controller.state.composing)
    }

    @Test
    fun `next word retains the converted boundary and closes undo`() {
        pendingSpace("a")
        controller.doubleSpace(execute)
        controller.typeText("b", execute)
        assertEquals(TypingEdit.SetComposingText(". b"), edits.last())
        assertEquals("a. b", controller.state.contextText)
        assertNull(controller.state.lastAutoEdit)
        assertFalse(selection(4, 4, 1, 4))
        controller.deletePrevious(execute)
        assertEquals("a. ", controller.state.contextText)
        assertEquals(ComposingSegment(". "), controller.state.composing)
    }

    @Test
    fun `double space requires a complete ordinary word in owned context`() {
        for (prefix in listOf("a", "я", "e\u0301")) {
            pendingSpace(prefix)
            assertEquals(prefix, TypingTextResult.HANDLED, controller.doubleSpace(execute))
            assertEquals(prefix + ". ", controller.state.contextText)
            controller.deletePrevious(execute)
            assertEquals(prefix + " ", controller.state.contextText)
        }
        for (prefix in listOf("", " ", "\n", "\t", ".", ",", "!", "?", "5", ":", ";", "😀", "👩🏽‍💻", "🇷🇺")) {
            pendingSpace(prefix)
            assertEquals(prefix, TypingTextResult.BYPASS, controller.doubleSpace(execute))
            assertTrue(edits.isEmpty())
            assertNull(controller.state.lastAutoEdit)
            assertEquals(prefix + " ", controller.state.contextText)
        }
    }

    @Test
    fun `double space bypasses disabled unknown and noncollapsed initial selections without writes`() {
        for ((start, end) in listOf(-1 to -1, 4 to 7, 0 to 0)) {
            start(start, end)
            edits.clear()
            assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
            assertTrue(edits.isEmpty())
            assertNull(controller.state.lastAutoEdit)
        }
        controller.startSession(
            EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD, 0),
            0, 0,
        )
        assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
        assertTrue(edits.isEmpty())
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `double space bypasses finished or uncertain ownership without editor reads or writes`() {
        pendingSpace("word")
        controller.finishComposition(execute)
        edits.clear()
        assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
        assertTrue(edits.isEmpty())

        controller.awaitEditorSelection(execute)
        edits.clear()
        assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
        assertTrue(edits.isEmpty())
        assertNull(controller.state.lastAutoEdit)
    }

    @Test
    fun `double space bypasses when only editor could know preceding character`() {
        start(50)
        controller.typeText(" ", execute)
        edits.clear()
        assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
        assertTrue(edits.isEmpty())
        assertEquals(" ", controller.state.contextText)
    }

    @Test
    fun `double space bypass followed by plain space preserves both visible spaces`() {
        for (prefix in listOf("", ".", ",", "!", "?")) {
            pendingSpace(prefix)
            assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
            assertEquals(TypingTextResult.HANDLED, controller.typeText(" ", execute))
            assertEquals(listOf(TypingEdit.SetComposingText(prefix + "  ")), edits)
            assertEquals(prefix + "  ", controller.state.contextText)
            assertEquals(ComposingSegment(prefix + "  "), controller.state.composing)
            assertNull(controller.state.lastAutoEdit)
        }
    }

    @Test
    fun `double space bypasses caret overflow`() {
        start(Int.MAX_VALUE - 2)
        controller.typeText("a", execute)
        controller.typeText(" ", execute)
        edits.clear()
        assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
        assertTrue(edits.isEmpty())
        assertEquals("a ", controller.state.contextText)
    }

    @Test
    fun `double space and undo accept synchronous callbacks and delayed following typing`() {
        pendingSpace("a")
        assertEquals(TypingTextResult.HANDLED, controller.doubleSpace {
            edits.add(it)
            assertFalse(selection(3, 3, 1, 3))
            true
        })
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious {
            edits.add(it)
            assertFalse(selection(2, 2, 1, 2))
            true
        })
        controller.typeText("b", execute)
        controller.typeText("c", execute)
        assertFalse(selection(4, 4, 1, 4))
        assertEquals("a bc", controller.state.contextText)
    }

    @Test
    fun `delayed own callbacks preserve undo until its latest span is acknowledged`() {
        pendingSpace("word")
        controller.doubleSpace(execute)
        assertFalse(selection(4, 4, 0, 4))
        assertFalse(selection(5, 5, 4, 5))
        assertFalse(selection(6, 6, 4, 6))
        assertFalse(selection(6, 6, 4, 6))
        assertTrue(controller.state.lastAutoEdit != null)
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious(execute))
        assertEquals("word ", controller.state.contextText)
    }

    @Test
    fun `acknowledged older span cannot revive stale undo after external replacement`() {
        pendingSpace("word")
        controller.doubleSpace(execute)
        assertFalse(selection(6, 6, 4, 6))
        edits.clear()
        assertTrue(selection(5, 5, 4, 5))
        assertNull(controller.state.lastAutoEdit)
        assertFalse(controller.state.enabled)
        assertEquals(TypingTextResult.BYPASS, controller.deletePrevious(execute))
        assertTrue(edits.isEmpty())
    }

    @Test
    fun `cursor move clears undo and never restores suffix at new caret`() {
        pendingSpace("word")
        controller.doubleSpace(execute)
        assertTrue(selection(0, 0, 4, 6))
        assertNull(controller.state.lastAutoEdit)
        edits.clear()
        assertEquals(TypingTextResult.BYPASS, controller.deletePrevious(execute))
        assertTrue(edits.isEmpty())
        assertEquals("", controller.state.contextText)
    }

    @Test
    fun `every other text action closes the immediate undo slot`() {
        for (text in listOf("b", " ", "!", "😀", "\n")) {
            pendingSpace("word")
            controller.doubleSpace(execute)
            controller.typeText(text, execute)
            assertNull(controller.state.lastAutoEdit)
        }
        pendingSpace("word")
        controller.doubleSpace(execute)
        edits.clear()
        assertEquals(TypingTextResult.BYPASS, controller.doubleSpace(execute))
        assertNull(controller.state.lastAutoEdit)
        assertTrue(edits.isEmpty())
    }

    @Test
    fun `finish invalidate settings discard and session lifecycle close undo`() {
        val boundaries: List<() -> Unit> = listOf(
            { controller.finishComposition(execute) },
            { controller.invalidate(execute) },
            { controller.discardUndo() },
            { controller.endSession() },
            { start(20) },
        )
        for (boundary in boundaries) {
            pendingSpace("word")
            controller.doubleSpace(execute)
            boundary()
            assertNull(controller.state.lastAutoEdit)
        }
    }

    @Test
    fun `a later automatic edit replaces the undo slot without retaining history`() {
        pendingSpace("first")
        controller.doubleSpace(execute)
        val first = controller.state.lastAutoEdit!!
        controller.typeText("second", execute)
        controller.typeText(" ", execute)
        controller.doubleSpace(execute)
        assertTrue(controller.state.lastAutoEdit!!.revision > first.revision)
        controller.deletePrevious(execute)
        assertEquals("first. second ", controller.state.contextText)
        assertNull(controller.state.lastAutoEdit)
    }

    @Test
    fun `rejected conversion or undo clears transaction and never replays text`() {
        for (undo in listOf(false, true)) {
            pendingSpace("word")
            if (undo) controller.doubleSpace(execute)
            edits.clear()
            val rejecting: (TypingEdit) -> Boolean = { edits.add(it); false }
            val result = if (undo) controller.deletePrevious(rejecting) else controller.doubleSpace(rejecting)
            assertEquals(TypingTextResult.REJECTED, result)
            assertEquals(listOf(TypingEdit.SetComposingText(if (undo) " " else ". "),
                TypingEdit.FinishComposingText), edits)
            assertNull(controller.state.lastAutoEdit)
            assertFalse(controller.state.enabled)
            assertEquals("", controller.state.contextText)
            assertEquals(TypingTextResult.BYPASS, controller.deletePrevious(execute))
            assertEquals(2, edits.size)
        }
    }

    @Test
    fun `session switch during conversion or undo cannot publish into new session`() {
        for (undo in listOf(false, true)) {
            pendingSpace("word")
            if (undo) controller.doubleSpace(execute)
            val switching: (TypingEdit) -> Boolean = {
                start(20)
                true
            }
            val result = if (undo) controller.deletePrevious(switching) else controller.doubleSpace(switching)
            assertEquals(TypingTextResult.REJECTED, result)
            assertNull(controller.state.lastAutoEdit)
            assertEquals("", controller.state.contextText)
            controller.typeText("b", execute)
            assertFalse(selection(21, 21, 20, 21))
            assertEquals("b", controller.state.contextText)
        }
    }

    @Test
    fun `external callback during conversion or undo cannot resurrect old context`() {
        for (undo in listOf(false, true)) {
            pendingSpace("word")
            if (undo) controller.doubleSpace(execute)
            val replacing: (TypingEdit) -> Boolean = {
                assertTrue(selection(30, 30, 29, 30))
                true
            }
            val result = if (undo) controller.deletePrevious(replacing) else controller.doubleSpace(replacing)
            assertEquals(TypingTextResult.REJECTED, result)
            assertNull(controller.state.lastAutoEdit)
            assertFalse(controller.state.enabled)
            assertEquals("", controller.state.contextText)
        }
    }

    @Test
    fun `undo restores bounded context prefix evicted by conversion without breaking Unicode`() {
        for (prefix in listOf("x ".repeat(509) + "hello", "😀".repeat(1_017) + "\nhello")) {
            pendingSpace(prefix)
            val original = controller.state.contextText
            assertEquals(1_024, original.codePointCount(0, original.length))
            controller.doubleSpace(execute)
            assertTrue(controller.state.contextText.length <= 2_048)
            assertEquals(1_024, controller.state.contextText.codePointCount(0, controller.state.contextText.length))
            controller.deletePrevious(execute)
            assertEquals(original, controller.state.contextText)
            assertEquals(ComposingSegment(" "), controller.state.composing)
        }
    }

    private fun pendingSpace(prefix: String, initialCaret: Int = 0) {
        start(initialCaret)
        controller.typeText(prefix, execute)
        controller.typeText(" ", execute)
        edits.clear()
    }

    private fun start(start: Int = 0, end: Int = start) {
        controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), start, end)
    }

    private fun selection(start: Int, end: Int, composingStart: Int, composingEnd: Int): Boolean =
        controller.updateSelection(start, end, composingStart, composingEnd, execute)
}
