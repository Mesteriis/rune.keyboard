package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import org.junit.Assert.*
import org.junit.After
import org.junit.Test

class EditorSimulatorTest {
    private val editors = mutableListOf<EditorSimulator>()
    @After fun noPayloadReads() {
        val writes = setOf("beginBatchEdit", "endBatchEdit", "setComposingRegion",
            "setComposingText", "commitText", "finishComposingText")
        for (editor in editors) assertTrue(editor.calls.all { it in writes })
    }
    private fun prepared(): EditorSimulator = EditorSimulator().apply {
        type(" ")
        assertEquals("outside ", document)
        assertTrue(controller.state.enabled)
    }.also { editors += it }

    @Test fun `normal callbacks retain exact Undo and the external prefix`() {
        val editor = prepared()
        editor.type("teh"); val before = editor.snapshot()
        editor.publishCommon("the"); editor.type(" ")
        assertEquals("outside the ", editor.document)
        assertTrue(editor.controller.state.enabled)
        editor.undo()
        assertEquals(before, editor.snapshot())
    }

    @Test fun `no callback on a stationary caret keeps subsequent correction available`() {
        val editor = prepared().apply { profile = EditorSimulator.Profile.NO_CALLBACK_ON_NOOP_CURSOR }
        editor.type("teh"); editor.finish()
        assertTrue(editor.suppressedCallbacks > 0)
        assertTrue(editor.controller.state.enabled)
        editor.type(" "); editor.type("teh"); editor.publishCommon("the"); editor.type(" ")
        assertEquals("outside teh the ", editor.document)
        assertTrue(editor.controller.state.enabled)
        editor.undo()
        assertEquals("outside teh teh", editor.document)
    }

    @Test fun `selection before composition disables conservatively without losing the word`() {
        val editor = prepared().apply { profile = EditorSimulator.Profile.SELECTION_THEN_COMPOSITION }
        editor.type("teh")
        assertFalse(editor.controller.state.enabled)
        assertNull(editor.controller.state.lastAutoEdit)
        editor.type(" ")
        assertEquals("outside teh ", editor.document)
    }

    @Test fun `prefix insert before region acknowledgement preserves outside text and removes Undo`() {
        val editor = prepared()
        editor.type("teh"); editor.publishCommon("the")
        editor.profile = EditorSimulator.Profile.SHIFTED_SPAN_AFTER_PREFIX_INSERT
        editor.type(" ")
        assertEquals("X outside the ", editor.document)
        assertFalse(editor.controller.state.enabled)
        assertNull(editor.controller.state.lastAutoEdit)
        editor.type("x")
        assertEquals("X outside the x", editor.document)
    }

    @Test fun `late reported composition is finished once without reviving ownership`() {
        val editor = prepared().apply { profile = EditorSimulator.Profile.SELECTION_THEN_COMPOSITION }
        editor.type("teh")
        val count = editor.calls.count { it == "finishComposingText" }
        assertEquals(1, count)
        val late = editor.callbacks.last { it.start >= 0 }
        editor.controller.updateSelection(late.caret, late.caret, late.start, late.end, editor.execute)
        assertEquals(count, editor.calls.count { it == "finishComposingText" })
        assertFalse(editor.controller.state.enabled)
        assertNull(editor.controller.state.composing)
        assertNull(editor.controller.state.lastAutoEdit)
    }

    @Test fun `refused late cleanup is not retried and cannot revive Undo`() {
        for (throws in listOf(false, true)) {
            val editor = prepared().apply {
                profile = EditorSimulator.Profile.SELECTION_THEN_COMPOSITION
                refuseFinish = !throws
                throwOnFinish = throws
            }
            editor.type("teh")
            assertEquals("outside teh", editor.document)
            assertEquals(1, editor.calls.count { it == "finishComposingText" })
            assertFalse(editor.controller.state.enabled)
            assertNull(editor.controller.state.lastAutoEdit)
        }
    }

    @Test fun `new password session cannot receive obsolete composition cleanup`() {
        val editor = prepared().apply {
            profile = EditorSimulator.Profile.SELECTION_THEN_COMPOSITION
            autoFlush = false
        }
        editor.type("teh"); editor.deliverNext()
        assertFalse(editor.controller.state.enabled)
        editor.controller.startSession(EditorContext.from(129, 0), 0, 0)
        editor.flush()
        assertFalse(editor.controller.state.enabled)
        assertEquals(0, editor.calls.count { it == "finishComposingText" })
    }

    @Test fun `late cleanup returning after session replacement cannot disable the new session`() {
        val editor = prepared().apply { profile = EditorSimulator.Profile.SELECTION_THEN_COMPOSITION }
        val previousSession = editor.controller.state.sessionId
        editor.afterFinish = {
            val caret = editor.document.length
            editor.controller.startSession(EditorContext.from(1, 0), caret, caret)
        }
        editor.type("teh")
        assertTrue(editor.controller.state.sessionId > previousSession)
        assertTrue(editor.controller.state.enabled)
        assertEquals("outside teh", editor.document)
        assertEquals(1, editor.calls.count { it == "finishComposingText" })
        assertNull(editor.controller.state.lastAutoEdit)
    }

    @Test fun `silent span loss documents duplicate composition and disables without Undo`() {
        val editor = prepared()
        editor.type("teh")
        editor.profile = EditorSimulator.Profile.SPAN_DROPPED_SILENTLY
        editor.dropSpanSilently(); editor.type("x")
        assertEquals("outside teh tehx", editor.document)
        assertFalse(editor.controller.state.enabled)
        assertNull(editor.controller.state.lastAutoEdit)
        editor.type("y")
        assertEquals("outside teh tehxy", editor.document)
    }
}
