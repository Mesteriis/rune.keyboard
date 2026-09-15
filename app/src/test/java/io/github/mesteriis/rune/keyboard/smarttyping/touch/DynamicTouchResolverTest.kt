package io.github.mesteriis.rune.keyboard.smarttyping.touch

import org.junit.Assert.assertEquals
import org.junit.Test

class DynamicTouchResolverTest {
    private val profile = TouchLayoutProfile("RUSSIAN", "LETTERS", 600, 300, 1, 400, 800, 320, 0, "a".repeat(64))
    private val strong = mapOf('а' to 0.05, 'с' to 0.9)
    private fun sample(x: Double = 0.49, otherX: Double = -0.51) = PhysicalTouchSample(profile, 'а',
        listOf(TouchKeyOffset('а', x, 0.0), TouchKeyOffset('с', otherX, 0.0)))
    @Test fun centreAndWeakPriorsAbstain() {
        assertEquals('а', DynamicTouchResolver.propose(sample(0.25), strong))
        assertEquals('а', DynamicTouchResolver.propose(sample(), mapOf('а' to 0.2, 'с' to 0.59)))
        assertEquals('а', DynamicTouchResolver.propose(sample(), mapOf('а' to 0.3, 'с' to 0.7)))
    }
    @Test fun edgeMayWinButBoundedPriorCannotOvercomeGeometry() {
        assertEquals('с', DynamicTouchResolver.propose(sample(), strong))
        assertEquals('а', DynamicTouchResolver.propose(sample(0.26, -0.74), strong))
        assertEquals('а', DynamicTouchResolver.propose(sample(otherX = -0.76), strong))
        assertEquals('а', DynamicTouchResolver.propose(sample(), mapOf('т' to 1.0)))
    }
    @Test fun invalidDataAndNonRussianAbstain() {
        for (p in listOf(Double.NaN, Double.POSITIVE_INFINITY, -0.1, 1.1)) {
            assertEquals('а', DynamicTouchResolver.propose(sample(), mapOf('с' to p)))
            if (!p.isFinite()) assertEquals('а', DynamicTouchResolver.propose(sample(otherX = p), strong))
        }
        assertEquals('а', DynamicTouchResolver.propose(sample().copy(profile = profile.copy(language = "ENGLISH")), strong))
        assertEquals('а', DynamicTouchResolver.propose(sample(), mapOf('a' to 0.9)))
        assertEquals('а', DynamicTouchResolver.propose(sample().copy(offsets = sample().offsets + sample().offsets.first()), strong))
    }
    @Test fun exactTiesUseLetterOrder() {
        val s = sample().copy(offsets = sample().offsets + TouchKeyOffset('б', -0.51, 0.0))
        val priors = strong + ('б' to 0.9)
        assertEquals('б', DynamicTouchResolver.propose(s, priors))
        assertEquals('б', DynamicTouchResolver.propose(s.copy(offsets = s.offsets.reversed()), priors))
    }
}
