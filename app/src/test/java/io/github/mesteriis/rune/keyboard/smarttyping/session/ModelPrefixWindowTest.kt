package io.github.mesteriis.rune.keyboard.smarttyping.session

import org.junit.Assert.*
import org.junit.Test

class ModelPrefixWindowTest {
    private fun window() = ModelPrefixWindow(jvmGraphemes)

    @Test fun `short qualified prefixes retain all bytes and separator`() {
        val window = window()
        val prefix = "a".repeat(256) + " "
        assertEquals(prefix, window.bound(prefix))
        assertEquals("привет world ", window.bound("привет world "))
        assertNull(window.bound("   "))
    }

    @Test fun `long unicode input is bounded on word and grapheme boundaries`() {
        val prefix = ("слово 👨‍👩‍👧‍👦 ".repeat(100))
        val result = assertNotNullResult(window().bound(prefix))
        assertTrue(result.endsWith(" "))
        assertTrue(result.dropLast(1).toByteArray(Charsets.UTF_8).size <= 256)
        assertTrue(prefix.endsWith(result))
        val start = prefix.length - result.length
        assertTrue(jvmGraphemes.boundaries(prefix).contains(start))
        assertTrue(Character.isWhitespace(prefix.codePointBefore(start)))
    }

    @Test fun `hysteresis retains the same start as text extends`() {
        val window = window()
        val original = "word ".repeat(60)
        val first = assertNotNullResult(window.bound(original))
        val extended = original + "next "
        val second = assertNotNullResult(window.bound(extended))
        assertEquals(first + "next ", second)
        assertTrue(second.dropLast(1).toByteArray().size <= 256)
    }

    @Test fun `no whole word or malformed surrogate fails closed and resets`() {
        val window = window()
        assertNull(window.bound("x".repeat(257) + " "))
        assertNull(window.bound("abc\uD800 "))
        assertEquals("safe ", window.bound("safe "))
    }

    @Test fun `a single long complete final word can use the larger budget`() {
        val prefix = "older ".repeat(25) + "x".repeat(200) + " "
        val result = assertNotNullResult(window().bound(prefix))
        assertTrue(result.contains("x".repeat(200)))
        assertTrue(result.dropLast(1).toByteArray().size <= 256)
    }

    @Test fun `combining marks never become a cut inside a grapheme`() {
        val prefix = "word \u0301next ".repeat(100)
        val result = assertNotNullResult(window().bound(prefix))
        val offset = prefix.length - result.length
        assertTrue(jvmGraphemes.boundaries(prefix).contains(offset))
        assertFalse(result.startsWith("\u0301"))
    }

    @Test fun `replacement clears stale anchor rather than reusing an unrelated prefix`() {
        val window = window()
        assertNotNull(window.bound("alpha ".repeat(60)))
        assertEquals("brief ", window.bound("brief "))
        window.clear()
        assertEquals("another ", window.bound("another "))
    }

    @Test fun `native cache probe uses exact successive window outputs`() {
        fun words(first: Int, last: Int) = (first..last).joinToString("") { "word${it.toString().padStart(2, '0')} " }
        val window = window()
        assertEquals(words(17, 39), window.bound(words(0, 39)))
        assertEquals(words(17, 40), window.bound(words(0, 40)))
        assertEquals(words(34, 56), window.bound(words(0, 56)))
    }

    private fun assertNotNullResult(value: String?): String = requireNotNull(value)
}
