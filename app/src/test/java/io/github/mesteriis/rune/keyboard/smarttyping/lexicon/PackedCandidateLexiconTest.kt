package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.IOException
import org.junit.Assert.*
import org.junit.Test

class PackedCandidateLexiconTest {
    private val en = KeyboardLanguage.ENGLISH
    private val es = KeyboardLanguage.SPANISH
    private fun control() = CandidateSearchControl { false }

    @Test fun `exact uses Unicode scalar siblings and reports absent prefixes and unavailable languages`() {
        val words = listOf("a", "ab", "aé", "a😀", "é", "ñ", "ё", "😀", "😀a", "a".repeat(32))
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(words).ready()))
        for (word in words) assertEquals(ExactMembership.PRESENT, reader.exact(en, word, control()))
        for (word in listOf("b", "aè", "😀b", "aa")) assertEquals(ExactMembership.ABSENT, reader.exact(en, word, control()))
        assertEquals(ExactMembership.UNAVAILABLE, reader.exact(es, "a", control()))
        for (word in listOf("", "A", "e\u0301", "\ud800", "a".repeat(33), "a" + "\u0344".repeat(31))) {
            assertEquals(ExactMembership.UNAVAILABLE, reader.exact(en, word, control()))
            assertEquals(LexiconScanStatus.UNAVAILABLE, reader.scan(en, word, 2, control()) { _, _ -> fail("INVALID_QUERY_VISIT"); true })
        }
        assertCleared(reader)
    }

    @Test fun `full radius enumeration matches independent unrestricted edit graph`() {
        val words = buildList {
            var level = listOf("")
            repeat(4) { level = level.flatMap { word -> listOf(word + "a", word + "b") }; addAll(level) }
        }
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(words).ready()))
        var comparisons = 0
        for (query in words + listOf("ababa", "babab")) for (radius in 1..2) {
            val neighbors = graphNeighbors(query, listOf('a'.code, 'b'.code), radius)
            val expected = words.filter { it != query && it in neighbors }.sorted()
            val actual = mutableListOf<String>()
            val control = control()
            val status = reader.scan(en, query, radius, control) { terminal, rank ->
                if (!control.verifyTerminal()) false else { actual.add(terminal); assertTrue(rank > 0); true }
            }
            assertEquals(LexiconScanStatus.COMPLETE, status)
            assertEquals(expected, actual)
            assertEquals(expected.size, control.verifiedTerminals)
            assertTrue(control.inspectedStates <= 30)
            assertCleared(reader)
            comparisons++
        }
        assertEquals(64, comparisons)
    }

    @Test fun `unrestricted transposition and supplementary codepoints survive radius pruning`() {
        for ((query, word, radius) in listOf(Triple("caxxx", "abcxxx", 2), Triple("😀a", "a😀", 1),
            Triple("éaño", "aéño", 1), Triple("a".repeat(31) + "b", "a".repeat(32), 1))) {
            val reader = PackedCandidateLexicon(listOf(PackedFixture.build(listOf(word)).ready()))
            val found = mutableListOf<String>()
            assertEquals(LexiconScanStatus.COMPLETE, reader.scan(en, query, radius, control()) { text, _ -> found.add(text); true })
            assertEquals(listOf(word), found)
            assertCleared(reader)
        }
    }

    @Test fun `exact and scan share states and the last allowed inspected edge can complete`() {
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("a", "b")).ready()))
        val exact = control()
        repeat(8_190) { assertTrue(exact.inspectState()) }
        assertEquals(ExactMembership.PRESENT, reader.exact(en, "b", exact))
        assertEquals(8_192, exact.inspectedStates)
        assertNull(exact.stop)
        assertEquals(LexiconScanStatus.UNAVAILABLE, reader.scan(en, "c", 1, exact) { _, _ -> fail("OVER_BUDGET_VISIT"); true })
        assertEquals(CandidateCompletion.STATES_EXHAUSTED, exact.stop)
        for (available in 1..2) {
            val scan = control()
            repeat(8_192 - available) { scan.inspectState() }
            val found = mutableListOf<String>()
            val status = reader.scan(en, "c", 1, scan) { text, _ -> if (scan.verifyTerminal()) { found.add(text); true } else false }
            assertEquals(if (available == 2) LexiconScanStatus.COMPLETE else LexiconScanStatus.UNAVAILABLE, status)
            assertEquals(if (available == 2) listOf("a", "b") else listOf("a"), found)
            assertEquals(8_192, scan.inspectedStates)
        }
        // Even a whole length-pruned subtree requires inspection of its root edge.
        val lengths = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("aaaaa", "b")).ready()))
        val budget = control()
        assertEquals(LexiconScanStatus.COMPLETE, lengths.scan(en, "c", 1, budget) { _, _ -> true })
        assertEquals(2, budget.inspectedStates)
        assertCleared(reader)
    }

    @Test fun `actual generator retains partial suggestions when the shared verification budget ends`() {
        val words = (0..3).flatMap { position -> "bcdefghijklmnoprtuvxy".map { "aaaaa".replaceRange(position, position + 1, it.toString()) } }
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(words).ready(), PackedFixture.build(listOf("zzzzzzzzzz"), es).ready()))
        val result = CandidateGenerator(reader).generate("aaaaa", en)
        assertEquals(CandidateCompletion.VERIFIED_EXHAUSTED, result.completion)
        assertEquals(64, result.verifiedTerminals)
        assertEquals(7, result.alternatives.size)
        assertTrue(result.prohibitsAutoReplace)
        assertFalse(result.isComplete)
        assertCleared(reader)
    }

    @Test fun `sixty four terminals can finish but required sixty fifth verification is incomplete`() {
        val words = (0..2).flatMap { position -> ('b'..'z').map { "aaaaa".replaceRange(position, position + 1, it.toString()) } }
        for (count in 64..65) {
            val reader = PackedCandidateLexicon(listOf(PackedFixture.build(words.take(count)).ready()))
            val control = control()
            var accepted = 0
            val status = reader.scan(en, "aaaaa", 1, control) { _, _ -> if (control.verifyTerminal()) { accepted++; true } else false }
            assertEquals(if (count == 64) LexiconScanStatus.COMPLETE else LexiconScanStatus.UNAVAILABLE, status)
            assertEquals(64, accepted)
            assertEquals(64, control.verifiedTerminals)
            assertEquals(if (count == 64) null else CandidateCompletion.VERIFIED_EXHAUSTED, control.stop)
            assertCleared(reader)
        }
    }

    @Test fun `cancellation and visitor failures stop immediately and scrub scratch before reuse`() {
        val reader = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("cat", "cot", "cit")).ready()))
        var cancelled = false
        val cancellation = CandidateSearchControl { cancelled }
        var visits = 0
        assertEquals(LexiconScanStatus.UNAVAILABLE, reader.scan(en, "cut", 1, cancellation) { _, _ -> visits++; cancelled = true; true })
        assertEquals(1, visits)
        assertEquals(CandidateCompletion.CANCELLED, cancellation.stop)
        assertCleared(reader)
        val failure = assertThrows(PackedReaderException::class.java) {
            reader.scan(en, "cut", 1, control()) { _, _ -> throw IOException("PRIVATE_SENTINEL") }
        }
        assertEquals("PACKED_READER_FAILURE", failure.message)
        assertNull(failure.cause)
        assertFalse(failure.toString().contains("PRIVATE_SENTINEL"))
        assertCleared(reader)
        try {
            assertThrows(InterruptedException::class.java) { reader.scan(en, "cut", 1, control()) { _, _ -> throw InterruptedException("PRIVATE_SENTINEL") } }
            assertTrue(Thread.currentThread().isInterrupted)
            assertCleared(reader)
        } finally { Thread.interrupted() }
        val found = mutableListOf<String>()
        assertEquals(LexiconScanStatus.COMPLETE, reader.scan(en, "cut", 1, control()) { word, _ -> found.add(word); true })
        assertEquals(listOf("cat", "cit", "cot"), found)
        assertCleared(reader)
    }

    private fun assertCleared(reader: PackedCandidateLexicon) {
        for (field in reader.javaClass.declaredFields.filter { it.type == IntArray::class.java }) {
            field.isAccessible = true
            assertTrue((field.get(reader) as IntArray).all { it == 0 })
        }
    }

    /** BFS over literal single edits, independent of the implementation's DP recurrence/pruning. */
    private fun graphNeighbors(source: String, alphabet: List<Int>, radius: Int): Set<String> {
        val seen = mutableSetOf(source)
        var frontier = setOf(source)
        repeat(radius) {
            val next = mutableSetOf<String>()
            for (word in frontier) {
                val cps = word.codePoints().toArray().toList()
                fun add(value: List<Int>) { val text = String(value.toIntArray(), 0, value.size); if (seen.add(text)) next.add(text) }
                for (i in cps.indices) {
                    add(cps.filterIndexed { index, _ -> index != i })
                    for (cp in alphabet) add(cps.toMutableList().also { it[i] = cp })
                    if (i + 1 < cps.size) add(cps.toMutableList().also { val cp = it[i]; it[i] = it[i + 1]; it[i + 1] = cp })
                }
                for (i in 0..cps.size) for (cp in alphabet) add(cps.toMutableList().also { it.add(i, cp) })
            }
            frontier = next
        }
        return seen
    }
}
