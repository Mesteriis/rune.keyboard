package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.util.Locale
import java.util.PriorityQueue
import org.junit.Assert.*
import org.junit.Test

/** Independent finite edit-graph oracle: no production DP, routing, case or ranking functions. */
class CandidateGeneratorOracleTest {
    private val en = KeyboardLanguage.ENGLISH
    private val es = KeyboardLanguage.SPANISH
    private val ru = KeyboardLanguage.RUSSIAN

    @Test
    fun `complete outputs match full weighted routing oracle in either enumeration order`() {
        val corpus = words("asd", 3)
        var comparisons = 0
        for ((queryIndex, query) in corpus.withIndex()) {
            val unit = shortestEdits(query, "asd", 4, weighted = false)
            val weighted = shortestEdits(query, "asd", 5, weighted = true)
            val dictionaries = mapOf(
                en to corpus.filterIndexed { index, word -> word != query && index % 3 != 0 }
                    .mapIndexed { index, word -> Entry(word, index % 5 + 1) },
                es to corpus.filterIndexed { index, word -> word != query && index % 4 != 0 }
                    .mapIndexed { index, word -> Entry(word, (index + 2) % 5 + 1) },
            )
            for (active in listOf(en, es, ru)) {
                // Lower, title and one-letter uppercase exercise independent case restoration.
                val input = when (queryIndex % 3) {
                    0 -> query
                    1 -> query.replaceFirstChar { it.uppercaseChar() }
                    else -> if (query.length == 1) query.uppercase(Locale.ROOT) else query
                }
                for (reverse in listOf(false, true)) {
                    val ordered = dictionaries.mapValues { (_, entries) -> if (reverse) entries.reversed() else entries }
                    val expected = fullOracle(input, active, dictionaries, unit, weighted, 1)
                    for (reader in listOf(ScriptedLexicon(ordered), packed(ordered))) {
                        val result = CandidateGenerator(reader).generate(input, active)
                        assertEquals(CandidateCompletion.COMPLETE, result.completion)
                        assertFalse(result.prohibitsAutoReplace) // Retrieval veto only, never permission.
                        assertEquals(input, result.original)
                        assertEquals(expected, result.alternatives.map(::signature))
                        assertTrue(result.alternatives.size <= 7)
                        assertTrue(result.alternatives.count { it.isFallback } <= 2)
                        comparisons++
                    }
                }
            }
        }
        assertEquals(468, comparisons)
    }

    @Test
    fun `radius two completion matches whole weighted edit graph rather than unit ordered prefix`() {
        val query = "asdas"
        val corpus = buildList {
            for (i in query.indices) {
                for (letter in "asd") if (letter != query[i]) add(query.replaceRange(i, i + 1, letter.toString()))
                add(query.removeRange(i, i + 1))
                if (i + 1 < query.length) add(query.substring(0, i) + query[i + 1] + query[i] + query.substring(i + 2))
            }
            for (letter in "asd") {
                add(query + letter)
                add(letter + query)
            }
            add("sdasd") // Two edits; full graph also considers alternate weighted paths.
            add("ssdss") // Two adjacent substitutions cost 1.5, independent of unit admission.
            add("sssss") // Three edits may be cheap but cannot enter radius two.
        }.distinct().filter { it != query }
        val dictionaries = mapOf(
            en to corpus.filterIndexed { index, _ -> index % 4 != 0 }.map { Entry(it, 9) },
            es to corpus.filterIndexed { index, _ -> index % 3 != 0 }.map { Entry(it, 1) },
        )
        val unit = shortestEdits(query, "asd", 8, weighted = false)
        val weighted = shortestEdits(query, "asd", 10, weighted = true)
        for (active in listOf(en, es)) {
            for (reader in listOf(ScriptedLexicon(dictionaries), packed(dictionaries))) {
                val result = CandidateGenerator(reader).generate(query, active)
                assertEquals(CandidateCompletion.COMPLETE, result.completion)
                assertEquals(fullOracle(query, active, dictionaries, unit, weighted, 2), result.alternatives.map(::signature))
                assertFalse(result.alternatives.any { it.text == "sssss" })
            }
        }
    }

    private fun packed(dictionaries: Map<KeyboardLanguage, List<Entry>>): CandidateLexicon =
        PackedCandidateLexicon(dictionaries.map { (language, entries) ->
            val fixture = PackedFixture.build(entries.map { it.word }, language)
            val ranks = entries.associate { it.word to it.rank }
            fixture.words.forEachIndexed { i, word -> fixture.put(fixture.ranks, 20 + 4 * i, ranks.getValue(word)) }
            fixture.ready()
        })

    private data class Signature(
        val text: String,
        val language: KeyboardLanguage,
        val fallback: Boolean,
        val prior: Int,
        val frequency: Int,
        val unitDistance: Int,
        val quarterCost: Int,
    )

    private fun signature(candidate: GeneratedCandidate) = Signature(
        candidate.text, candidate.language, candidate.isFallback, candidate.languagePrior,
        candidate.frequencyRank, candidate.unitDistance, (candidate.editFeatures.editCost * 4).toInt(),
    )

    private fun fullOracle(
        input: String,
        active: KeyboardLanguage,
        dictionaries: Map<KeyboardLanguage, List<Entry>>,
        unit: Map<String, Int>,
        weighted: Map<String, Int>,
        radius: Int,
    ): List<Signature> {
        // The declared oracle alphabet is plain Latin. RU layout must choose EN primary + ES fallback.
        val primary = if (active == es) es else en
        val all = dictionaries.flatMap { (language, entries) ->
            entries.mapNotNull { entry ->
                val steps = unit[entry.word]?.div(4) ?: return@mapNotNull null
                if (steps !in 1..radius) return@mapNotNull null
                val display = when {
                    input.all { it.isUpperCase() } -> entry.word.uppercase(Locale.ROOT)
                    input.first().isUpperCase() -> entry.word.replaceFirstChar { it.uppercaseChar() }
                    else -> entry.word
                }
                Signature(display, language, language != primary, if (language == primary) 4 else 1,
                    entry.rank, steps, weighted.getValue(entry.word))
            }
        }
        val order = compareBy<Signature> { it.quarterCost }
            .thenByDescending { it.prior }
            .thenBy { it.frequency }
            .thenBy { it.text.lowercase(Locale.ROOT) }
            .thenBy { it.language.ordinal }
        // Full grouping first is deliberately different from the production sorted-stream selection.
        val unique = all.groupBy { it.text.lowercase(Locale.ROOT) }.values.map { it.minWith(order) }.sortedWith(order)
        val primaryCandidates = unique.filterNot { it.fallback }
        val fallbackCandidates = unique.filter { it.fallback }.take(2)
        return (primaryCandidates + fallbackCandidates).sortedWith(order).take(7)
    }

    private data class Step(val word: String, val cost: Int)

    /**
     * Dijkstra explores ordinary insert/delete/substitute/adjacent-swap edges, not a DP recurrence.
     * The fixture alphabet a/s/d has exactly adjacent pairs a-s and s-d in EN and ES. A useful
     * shortest path needs no outside alphabet (substitution is metric; outside insertion costs >=4).
     * Cost cap is the worst admitted path: one/two unit edits, each weighted cost <=5 quarters.
     * Every edge costs >=3; insertions cost 4. The cap bounds length and makes exploration finite.
     */
    private fun shortestEdits(source: String, alphabet: String, cap: Int, weighted: Boolean): Map<String, Int> {
        val best = mutableMapOf(source to 0)
        val pending = PriorityQueue<Step>(compareBy { it.cost })
        pending.add(Step(source, 0))
        while (pending.isNotEmpty()) {
            val current = pending.remove()
            if (current.cost != best[current.word]) continue
            fun offer(next: String, edge: Int) {
                val cost = current.cost + edge
                if (cost <= cap && cost < best.getOrDefault(next, Int.MAX_VALUE)) {
                    best[next] = cost
                    pending.add(Step(next, cost))
                }
            }
            val word = current.word
            for (i in word.indices) {
                offer(word.removeRange(i, i + 1), 4)
                for (letter in alphabet) if (letter != word[i]) {
                    val adjacent = (word[i] == 's' && letter in "ad") || (letter == 's' && word[i] in "ad")
                    offer(word.replaceRange(i, i + 1, letter.toString()), if (weighted && adjacent) 3 else 4)
                }
                if (i + 1 < word.length && word[i] != word[i + 1]) {
                    offer(word.substring(0, i) + word[i + 1] + word[i] + word.substring(i + 2), if (weighted) 5 else 4)
                }
            }
            if (current.cost + 4 <= cap) for (i in 0..word.length) for (letter in alphabet) {
                offer(word.substring(0, i) + letter + word.substring(i), 4)
            }
        }
        return best
    }

    private fun words(alphabet: String, maximum: Int): List<String> {
        val all = mutableListOf<String>()
        var level = listOf("")
        repeat(maximum) {
            level = level.flatMap { prefix -> alphabet.map { prefix + it } }
            all += level
        }
        return all
    }
}
