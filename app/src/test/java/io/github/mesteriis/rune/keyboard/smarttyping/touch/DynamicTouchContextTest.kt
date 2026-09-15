package io.github.mesteriis.rune.keyboard.smarttyping.touch

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.session.ExperimentalTypingInput
import org.junit.Assert.*
import org.junit.Test

class DynamicTouchContextTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val input = ExperimentalTypingInput("скажи ", "приве")
    @Test fun ownershipAndSwitchChangesInvalidateTokensAndCachedContext() {
        val context = DynamicTouchContext(); var calls = 0
        fun predict(a: String, b: String, language: KeyboardLanguage): Map<Char, Double> {
            assertEquals("скажи ", a); assertEquals("приве", b); assertEquals(ru, language)
            calls++; return mapOf('т' to 0.9)
        }
        val token = context.update(1, 1, ru, input, true, false)
        assertNotEquals(0L, token); assertFalse(context.applies)
        repeat(3) { assertEquals(mapOf('т' to 0.9), context.probabilities(::predict)) }
        assertEquals(1, calls)
        assertNotEquals(token, context.update(1, 1, ru, input, true, true))
        assertTrue(context.applies)
        assertEquals(0L, context.update(1, 1, ru, input, false, true))
        assertTrue(context.probabilities(::predict).isEmpty())
        assertEquals(1, calls)
        assertEquals(0L, context.update(1, 2, ru, null, true, true))
        assertEquals(0L, context.update(1, 2, KeyboardLanguage.ENGLISH, input, true, true))
    }
    @Test fun backspaceSuppressesUntilBoundaryOrNewSession() {
        val context = DynamicTouchContext()
        context.update(1, 1, ru, input, true, true)
        context.afterDelete()
        assertEquals(0L, context.update(1, 2, ru, input, true, true))
        context.invalidate() // Geometry/settings invalidation cannot forget the delete guard.
        assertEquals(0L, context.update(1, 3, ru, input, true, true))
        context.afterBoundary()
        assertNotEquals(0L, context.update(1, 4, ru, input, true, true))
        context.afterDelete()
        assertNotEquals(0L, context.update(2, 1, ru, input, true, true))
    }
    @Test fun malformedPredictionsAndOversizedInputAbstain() {
        for (invalid in listOf(mapOf('a' to 0.5), mapOf('т' to Double.NaN), mapOf('т' to 1.1))) {
            val context = DynamicTouchContext()
            context.update(1, 1, ru, input, true, false)
            assertTrue(context.probabilities { _, _, _ -> invalid }.isEmpty())
        }
        val context = DynamicTouchContext()
        assertEquals(0L, context.update(1, 1, ru, ExperimentalTypingInput("", "а".repeat(49)), true, true))
    }
}
