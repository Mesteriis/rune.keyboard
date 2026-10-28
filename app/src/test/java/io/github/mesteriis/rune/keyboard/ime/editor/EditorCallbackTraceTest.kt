package io.github.mesteriis.rune.keyboard.ime.editor

import org.junit.After
import org.junit.Assert.*
import org.junit.Test

class EditorCallbackTraceTest {
    @After fun clear() { EditorCallbackTrace.end() }
    @Test fun `trace defaults off and drops metadata without an explicit session`() {
        EditorCallbackTrace.record(EditorCallbackTrace.COMPOSING_SPAN)
        assertEquals(0, EditorCallbackTrace.snapshot().total)
        assertFalse(EditorCallbackTrace.snapshot().active)
    }
    @Test fun `begin is exclusive and end returns a detached cleared snapshot`() {
        assertTrue(EditorCallbackTrace.begin())
        EditorCallbackTrace.record(2)
        assertFalse(EditorCallbackTrace.begin())
        assertEquals(listOf(2), EditorCallbackTrace.snapshot().events)
        val captured = EditorCallbackTrace.end()
        assertEquals(listOf(2), captured.events)
        assertFalse(captured.active)
        assertEquals(emptyList<Int>(), EditorCallbackTrace.snapshot().events)
        EditorCallbackTrace.record(1)
        assertEquals(0, EditorCallbackTrace.snapshot().total)
    }
    @Test fun `trace accepts only fixed flags and keeps the last 128 records`() {
        assertTrue(EditorCallbackTrace.begin())
        for (flags in listOf(-1, 64, Int.MAX_VALUE)) EditorCallbackTrace.record(flags)
        assertEquals(0, EditorCallbackTrace.snapshot().total)
        repeat(300) { EditorCallbackTrace.record(it % 64) }
        val captured = EditorCallbackTrace.snapshot()
        assertEquals(300, captured.total)
        assertEquals(172, captured.dropped)
        assertEquals((172 until 300).map { it % 64 }, captured.events)
    }
}
