package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.os.Build
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Synthetic public strings only; run on an emulator. */
class ModelPrefixWindowInstrumentedTest {
    @Test fun boundsAtIcuGraphemeAndWordBoundariesWithoutSplittingText() {
        assumeTrue(Build.HARDWARE in setOf("ranchu", "goldfish"))
        val window = ModelPrefixWindow(IcuGraphemeSegmenter)
        val original = ("слово 👨‍👩‍👧‍👦 \u0301next ".repeat(100))
        val result = requireNotNull(window.bound(original))
        val start = original.length - result.length
        assertTrue(start > 0)
        assertTrue(original.endsWith(result))
        assertTrue(IcuGraphemeSegmenter.boundaries(original).contains(start))
        assertTrue(Character.isWhitespace(original.codePointBefore(start)))
        assertFalse(result.startsWith("\u0301"))
        assertTrue(result.dropLast(1).toByteArray(Charsets.UTF_8).size <= 256)
        assertEquals(result + "more ", window.bound(original + "more "))
        window.clear()
        assertEquals("a".repeat(256) + " ", window.bound("a".repeat(256) + " "))
        assertNull(window.bound("x".repeat(257) + " "))
    }
}
