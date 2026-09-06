package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualPunctuationPolicy.Score
import org.junit.Assert.*
import org.junit.Test

class ContextualPunctuationPolicyTest {
    @Test fun `longer punctuation cannot win by averaging a worse total`() {
        val scores = listOf(Score(0, -2.0, 1), Score(1, -3.0, 2), Score(2, -10.0, 1))
        assertNull(ContextualPunctuationPolicy.choose(listOf(0, 1, 2), scores))
    }

    @Test fun `best total wins even when a longer rival has a better average`() {
        val scores = listOf(Score(0, -8.0, 1), Score(1, -1.0, 1), Score(2, -5.0, 255))
        assertEquals(1, ContextualPunctuationPolicy.choose(listOf(0, 1, 2), scores))
    }

    @Test fun `punctuation must improve Original by strictly more than half a log unit`() {
        for ((original, expected) in listOf(
            -0.75 to null, -1.0 to null, -1.25 to null, -1.5 to null,
            -1.500001 to 1,
        )) {
            assertEquals("Original total $original", expected,
                ContextualPunctuationPolicy.choose(ids, scores(original = original)))
        }
    }

    @Test fun `punctuation must beat the closest rival by at least four log units`() {
        for ((rival, expected) in listOf(-1.0 to null, -4.999999 to null, -5.0 to 1, -5.000001 to 1)) {
            assertEquals("Rival total $rival", expected,
                ContextualPunctuationPolicy.choose(ids, scores(rival = rival)))
        }
    }

    @Test fun `score and expected ID order do not change the selected candidate`() {
        val scores = scores().map { it.copy(candidateId = when (it.candidateId) { 1 -> 6; 6 -> 1; else -> it.candidateId }) }
        val orders = listOf(ids, ids.reversed(), listOf(4, 6, 0, 2, 5, 1, 3))
        for (expectedOrder in orders) for (scoreOrder in orders) {
            assertEquals(6, ContextualPunctuationPolicy.choose(expectedOrder,
                scoreOrder.map { id -> scores.single { it.candidateId == id } }))
        }
    }

    @Test fun `equal punctuation totals abstain regardless of ID and input order`() {
        val scores = scores(rival = -1.0)
        assertNull(ContextualPunctuationPolicy.choose(ids, scores))
        assertNull(ContextualPunctuationPolicy.choose(ids.reversed(), scores.reversed()))
    }

    @Test fun `missing duplicate or unexpected score IDs reject the entire reply`() {
        val valid = scores()
        for (malformed in listOf(
            emptyList(), valid.drop(1), valid.dropLast(1), valid + Score(7, -20.0, 1),
            valid.map { if (it.candidateId == 6) it.copy(candidateId = 1) else it },
            valid.map { if (it.candidateId == 6) it.copy(candidateId = 7) else it },
            valid.map { if (it.candidateId == 6) it.copy(candidateId = -1) else it },
        )) assertNull(ContextualPunctuationPolicy.choose(ids, malformed))
    }

    @Test fun `malformed expected candidate sets cannot authorize a suggestion`() {
        for (expected in listOf(
            emptyList(), listOf(0), listOf(0, 1), listOf(1, 2, 3), listOf(0, 1, 1),
            listOf(0, 1, -1), (0..8).toList(),
        )) {
            val scores = expected.map { Score(it, if (it == 1) -1.0 else -10.0, 1) }
            assertNull(ContextualPunctuationPolicy.choose(expected, scores))
        }
    }

    @Test fun `nonfinite or positive sums in any candidate reject the entire reply`() {
        for (id in ids) for (invalid in listOf(Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY, 0.001)) {
            val scores = scores().map { if (it.candidateId == id) it.copy(sumLogProbability = invalid) else it }
            assertNull("Candidate $id sum $invalid", ContextualPunctuationPolicy.choose(ids, scores))
        }
    }

    @Test fun `zero negative or out of contract token counts reject the entire reply`() {
        for (id in ids) for (invalid in listOf(0, -1, 256)) {
            val scores = scores().map { if (it.candidateId == id) it.copy(tokenCount = invalid) else it }
            assertNull("Candidate $id token count $invalid", ContextualPunctuationPolicy.choose(ids, scores))
        }
    }

    @Test fun `no divergent probability evidence abstains`() {
        assertNull(ContextualPunctuationPolicy.choose(ids, ids.map { Score(it, 0.0, 1) }))
        assertNull(ContextualPunctuationPolicy.choose(ids, ids.map { Score(it, 0.0, 0) }))
    }

    @Test fun `finite zero total and positive token counts are accepted when both margins pass`() {
        val scores = scores().map { if (it.candidateId == 1) it.copy(sumLogProbability = 0.0) else it }
        assertEquals(1, ContextualPunctuationPolicy.choose(ids, scores))
    }

    private val ids = (0..6).toList()

    private fun scores(original: Double = -8.0, rival: Double = -5.0) = ids.map {
        Score(it, when (it) { 0 -> original; 1 -> -1.0; 2 -> rival; else -> -12.0 }, 2)
    }
}
