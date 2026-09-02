package io.github.mesteriis.rune.keyboard.smarttyping.session

import java.util.regex.Pattern
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** JVM UAX #29 segmentation substitutes for Android ICU, which unit-test android.jar stubs. */
internal val jvmGraphemes = GraphemeSegmenter { text ->
    val matcher = Pattern.compile("\\X").matcher(text)
    buildList {
        add(0)
        while (matcher.find()) add(matcher.end())
    }
}

class SessionTextContextTest {
    @Test
    fun `bounded prefix eviction never cuts supported grapheme families`() {
        val clusters = listOf("e\u0301", "👩🏽‍💻", "🇷🇺", "\r\n", "✊🏽", "1️⃣")
        for (cluster in clusters) {
            // The minimum UTF-16 cut is inside the leading cluster, so discard it completely.
            val context = SessionTextContext(jvmGraphemes, maxUtf16 = cluster.length, maxCodePoints = 100)
            context.append(cluster + "x")
            assertEquals("x", context.text)
        }
    }

    @Test
    fun `code point budget can be tighter than UTF16 budget`() {
        val context = SessionTextContext(jvmGraphemes, maxUtf16 = 100, maxCodePoints = 3)
        context.append("ab😀x")
        assertEquals("b😀x", context.text)
        assertEquals(3, context.text.codePointCount(0, context.text.length))
    }

    @Test
    fun `regional indicators retain whole flag pairing when trimming`() {
        val context = SessionTextContext(jvmGraphemes, maxUtf16 = 7, maxCodePoints = 100)
        context.append("🇷🇺🇺🇸x")
        assertEquals("🇺🇸x", context.text)
    }

    @Test
    fun `single oversized grapheme is evicted completely`() {
        val context = SessionTextContext(jvmGraphemes, maxUtf16 = 5, maxCodePoints = 5)
        context.append("a" + "\u0301".repeat(20))
        assertEquals("", context.text)
    }

    @Test
    fun `default limits bound a long session`() {
        val context = SessionTextContext(jvmGraphemes)
        repeat(1_500) { context.append("😀") }
        assertEquals(2_048, context.text.length)
        assertEquals(1_024, context.text.codePointCount(0, context.text.length))
    }

    @Test
    fun `backspace removes whole final cluster and clear destroys retained text`() {
        val context = SessionTextContext(jvmGraphemes)
        context.append("word 👩🏽‍💻")
        context.removeLastGrapheme()
        assertEquals("word ", context.text)
        context.clear()
        context.removeLastGrapheme()
        assertEquals("", context.text)
    }

    @Test
    fun `suffix replacement rejects mismatches without mutating owned context`() {
        val context = SessionTextContext(jvmGraphemes).apply { append("word ") }
        assertFalse(context.replaceSuffix(". ", " "))
        assertFalse(context.replaceSuffix("", "replacement"))
        assertEquals("word ", context.text)
        assertTrue(context.replaceSuffix(" ", ". "))
        assertEquals("word. ", context.text)
    }

    @Test
    fun `suffix replacement and snapshot restoration retain bounds and whole graphemes`() {
        val context = SessionTextContext(jvmGraphemes, maxUtf16 = 6, maxCodePoints = 5)
        context.append("e\u0301ab ")
        val original = context.text
        assertTrue(context.replaceSuffix(" ", ". "))
        assertEquals("ab. ", context.text)
        context.restore(original)
        assertEquals("e\u0301ab ", context.text)
        context.restore("x".repeat(20))
        assertEquals("xxxxx", context.text)
    }

    @Test
    fun `diagnostic representations contain no typed content`() {
        val context = SessionTextContext(jvmGraphemes).apply { append("private phrase") }
        assertFalse(context.toString().contains("private phrase"))
        assertFalse(ComposingSegment(typedWord = "private phrase").toString().contains("private phrase"))
        assertTrue(TypingSessionState(contextText = "private phrase").toString().contains("sessionId"))
        assertFalse(TypingSessionState(contextText = "private phrase").toString().contains("private phrase"))
        val undo = UndoableTextEdit(
            original = "private original",
            applied = "private replacement",
            sessionId = 1,
            revision = 2,
            restoreComposition = ComposingSegment(typedWord = "private original"),
            contextBefore = "private context",
        )
        assertTrue(undo.toString().contains("sessionId=1"))
        assertFalse(undo.toString().contains("private"))
        assertFalse(TypingSessionState(lastAutoEdit = undo).toString().contains("private"))
    }
}
