package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.KeyboardDistance
import org.junit.Assert.*
import org.junit.Test

class NeighborRecoverySearchTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val running = CandidateCancellation { false }

    @Test fun `recovers two and three neighbour errors without changing baseline evidence`() {
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("проверка"), ru).ready()))
        val generator = CandidateGenerator(reader)
        for (typed in listOf("рооверка", "ролверка", "Ролверка")) {
            val baseline = generator.generate(typed, ru)
            val recovered = generator.generateRecovery(typed, ru, baseline)
            assertEquals(baseline.localSearch, recovered.localSearch)
            assertEquals(baseline.alternatives, recovered.alternatives)
            assertEquals(CandidateCompletion.COMPLETE, recovered.neighborRecovery.completion)
            assertEquals(listOf(if (typed.first().isUpperCase()) "Проверка" else "проверка"),
                recovered.neighborRecovery.alternatives.map { it.text })
        }
    }

    @Test fun `logged multi-error shapes retain competing words without changing the baseline`() {
        val words = listOf("решение", "решением", "решаете", "полетать", "прилетать", "пролетать")
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(words, ru).ready()))
        val generator = CandidateGenerator(reader)
        for ((typed, target) in listOf("решкнте" to "решение", "прлетатт" to "полетать")) {
            val baseline = generator.generate(typed, ru)
            val recovered = generator.generateRecovery(typed, ru, baseline)
            assertEquals(baseline.alternatives, recovered.alternatives)
            assertEquals(baseline.localSearch, recovered.localSearch)
            assertEquals(CandidateCompletion.COMPLETE, recovered.neighborRecovery.completion)
            assertTrue("$typed -> $target", recovered.neighborRecovery.alternatives.any { it.text == target })
            assertTrue(recovered.neighborRecovery.alternatives.all { distance(typed, it.text) in 2..3 })
        }
    }

    @Test fun `trie matches independent structural enumeration including pending transpose`() {
        val words = listOf("проверка", "работает", "клавиатура", "соседний", "опечатка")
        val index = PackedFixture.build(words, ru).ready()
        val search = NeighborRecoverySearch({ index }, nanoTime = { 0 })
        val queries = words.flatMap { word -> buildList {
            for (a in word.indices) for (b in a + 1 until word.length) {
                val typo = word.mapIndexed { i, c -> if (i == a || i == b) neighbor(c) else c }.joinToString("")
                add(typo)
                add(typo.dropLast(1))
                add(typo + "а")
                for (i in 0 until word.lastIndex) add(typo.replaceRange(i, i + 2, "${typo[i + 1]}${typo[i]}"))
            }
        } }.distinct()
        for (query in queries) {
            val radius = if (query.length >= 7) 3 else 2
            val expected = words.filter { query.length in 5..32 && distance(query, it) in 2..radius }.toSet()
            val actual = search.search(query, running)
            assertEquals(CandidateCompletion.COMPLETE, actual.completion)
            assertEquals("query=$query", expected, actual.alternatives.map { it.text }.toSet())
        }
    }

    @Test fun `budgets cancellation and case eligibility cannot certify incomplete retrieval`() {
        val index = PackedFixture.build(listOf("проверка"), ru).ready()
        assertEquals(CandidateCompletion.STATES_EXHAUSTED,
            NeighborRecoverySearch({ index }, { 0 }, maximumStates = 1).search("ролверка", running).completion)
        assertEquals(CandidateCompletion.VERIFIED_EXHAUSTED,
            NeighborRecoverySearch({ index }, { 0 }, maximumTerminals = 0).search("ролверка", running).completion)
        var clock = -100_000_000L
        val timed = NeighborRecoverySearch({ index }, { clock += 100_000_000; clock })
        assertEquals(CandidateCompletion.STATES_EXHAUSTED, timed.search("ролверка", running).completion)
        val search = NeighborRecoverySearch({ index }, { 0 })
        val cancelled = search.search("ролверка", CandidateCancellation { true })
        assertEquals(CandidateCompletion.CANCELLED, cancelled.completion)
        assertTrue(cancelled.alternatives.isEmpty())
        for (query in listOf("РОЛВЕРКА", "ролВерка", "abcded", "а".repeat(33), "ролв")) {
            assertEquals(LocalSearchEvidence.NONE, search.search(query, running))
        }
        assertTrue(search.search("ролверка", running).alternatives.isNotEmpty())
    }

    private fun neighbor(c: Char): Char = ('а'..'я').first { KeyboardDistance.areAdjacent(c.code, it.code, ru) }

    /** Enumerate the position of at most one structural edit, then count adjacent substitutions. */
    private fun distance(input: String, target: String): Int {
        fun substitutions(a: String, b: String): Int = if (a.length != b.length) 100 else
            a.indices.sumOf { i -> when {
                a[i] == b[i] -> 0
                KeyboardDistance.areAdjacent(a[i].code, b[i].code, ru) -> 1
                else -> 100
            } }
        var best = substitutions(input, target)
        if (input.length == target.length + 1) for (i in input.indices)
            best = minOf(best, 1 + substitutions(input.removeRange(i, i + 1), target))
        if (target.length == input.length + 1) for (i in target.indices)
            best = minOf(best, 1 + substitutions(input, target.removeRange(i, i + 1)))
        if (input.length == target.length) for (i in 0 until input.lastIndex) {
            if (input[i] == target[i + 1] && input[i + 1] == target[i]) {
                best = minOf(best, 1 + substitutions(input.removeRange(i, i + 2), target.removeRange(i, i + 2)))
            }
        }
        return best
    }
}
