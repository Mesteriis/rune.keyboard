package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import org.junit.Assert.*
import org.junit.Test

class PackedTopSevenTest {
    private val en = KeyboardLanguage.ENGLISH
    private val es = KeyboardLanguage.SPANISH
    private fun control() = CandidateSearchControl { false }
    private fun unhex(s: String) = if (s == "-") "" else String(s.split(',').map { it.toInt(16).toChar() }.toCharArray())
    private fun resource(name: String) = checkNotNull(javaClass.getResourceAsStream("/smarttyping/top-seven/$name"))
        .bufferedReader().use { it.readLines().map { line -> line.split('\t') } }
    private fun handle(words: Map<String, Int>, lang: KeyboardLanguage): PackedLexiconData {
        val f = PackedFixture.build(words.keys.toList(), lang)
        f.words.forEachIndexed { i, word -> f.put(f.ranks, 20 + 4 * i, words.getValue(word)) }
        return f.ready()
    }

    @Test fun `all prefix cuts are bounded by independent edit graph distances`() {
        val dp = PrefixDistance()
        var pairs = 0; var cuts = 0
        for (r in resource("bounds.tsv")) {
            val query = unhex(r[0]); val target = unhex(r[1]); val lang = KeyboardLanguage.entries[r[2].toInt()]
            val expectedUnit = r[3].toInt(); val expectedWeighted = r[4].toInt()
            dp.begin(query)
            var lowerUnit = 0; var lowerWeighted = 0
            val gap = kotlin.math.abs(query.codePointCount(0, query.length) - target.codePointCount(0, target.length))
            for (cp in target.codePoints().toArray()) {
                assertTrue(dp.append(cp, lang, control()))
                lowerUnit = maxOf(lowerUnit, dp.unitMinimum, gap)
                lowerWeighted = maxOf(lowerWeighted, dp.weightedMinimum, 3 * lowerUnit, 4 * gap)
                assertTrue(lowerUnit <= expectedUnit)
                assertTrue(lowerWeighted <= expectedWeighted)
                cuts++
            }
            assertEquals(expectedUnit, dp.terminalUnit)
            assertEquals(expectedWeighted, dp.terminalWeighted)
            dp.clear(); assertTrue(dp.isClear()); pairs++
        }
        assertEquals(3209, pairs); assertEquals(8218, cuts)
    }

    @Test fun `production generator matches independently frozen full policy cases`() {
        val dictionaries = resource("dictionaries.tsv").groupBy { it[0].toInt() }
        val expected = resource("expected.tsv").groupBy { it[0].toInt() }
        var cases = 0
        for (r in resource("requests.tsv")) {
            val id = r[0].toInt(); val token = unhex(r[1]); val lang = KeyboardLanguage.entries[r[2].toInt()]
            val handles = dictionaries.getValue(id).groupBy { it[1].toInt() }.map { (language, words) ->
                handle(words.associate { unhex(it[2]) to it[3].toInt() }, KeyboardLanguage.entries[language])
            }
            val actual = CandidateGenerator(PackedCandidateLexicon(handles)).generate(token, lang)
            assertEquals("case $id", r[3].toInt(), actual.completion.ordinal)
            assertEquals(token, actual.original)
            assertEquals(r[4].toInt(), actual.protectedReason?.ordinal ?: -1)
            assertEquals(r[5].toInt(), actual.alternatives.size)
            val want = expected[id] ?: emptyList()
            assertEquals(want.size, actual.alternatives.size)
            actual.alternatives.zip(want).forEach { (a, e) ->
                assertEquals(e[2].toInt(), a.language.ordinal)
                assertEquals(unhex(e[3]), a.terminalKey); assertEquals(unhex(e[4]), a.text)
                assertEquals(unhex(e[5]), a.canonicalKey); assertEquals(e[6].toInt(), a.frequencyRank)
                assertEquals(e[7].toInt(), a.languagePrior); assertEquals(e[8] == "1", a.isFallback)
                assertEquals(e[9].toInt(), a.unitDistance); assertEquals(e[10].toInt(), (a.editFeatures.editCost * 4).toInt())
                assertEquals(e[11].toInt(), a.editFeatures.repeatedCharacterEdits)
                assertEquals(e[11].toInt() * 0.25, a.editFeatures.repetitionBonus, 0.0)
                assertEquals(e[12].toInt(), a.lengthDifference); assertEquals(e[13].toInt(), a.casePattern.ordinal)
            }
            cases++
        }
        assertEquals(94, cases)
    }

    @Test fun `last state can finish but unfinished child expansion cannot certify`() {
        val handles = listOf(handle(mapOf("a" to 1), en), handle(mapOf("b" to 1), es)).associateBy { it.language }
        val engine = PackedTopSeven(handles::get)
        for (available in 1..2) {
            val control = control()
            repeat(8192 - available) { assertTrue(control.inspectState()) }
            val result = engine.select("c", LanguageRouter.route("c", en), CasePattern.LOWER, control)
            assertEquals(8192, control.inspectedStates)
            assertEquals(if (available == 2) CandidateCompletion.COMPLETE else CandidateCompletion.STATES_EXHAUSTED, result.completion)
            assertEquals(if (available == 2) TopCandidateProof.FRONTIER_EXHAUSTED else TopCandidateProof.NONE, result.proof)
            assertTrue(engine.isClear())
        }
    }

    @Test fun `verification cap is shared and cannot be hidden by early certification`() {
        val words = (0..3).flatMap { pos -> "bcdefghijklmnoprtuvxy".map { "aaaaa".replaceRange(pos, pos + 1, it.toString()) } }
        for (split in listOf(0, 5)) for (count in 64..65) {
            val primary = if (split == 0) words.take(count) else words.take(split)
            val fallback = if (split == 0) listOf("zzzzzzzz") else words.take(count - split)
            val handles = listOf(handle(primary.associateWith { 1 }, en), handle(fallback.associateWith { 1 }, es))
            val result = CandidateGenerator(PackedCandidateLexicon(handles)).generate("aaaaa", en)
            assertEquals(64, result.verifiedTerminals)
            assertEquals(if (count == 64) CandidateCompletion.COMPLETE else CandidateCompletion.VERIFIED_EXHAUSTED, result.completion)
            assertEquals(count == 65, result.prohibitsAutoReplace)
        }
    }

    @Test fun `every cancellation checkpoint discards payload and permits immediate reuse`() {
        val handles = listOf(handle(mapOf("cat" to 1, "cot" to 2, "cit" to 3), en), handle(mapOf("zzzzz" to 1), es))
            .associateBy { it.language }
        val engine = PackedTopSeven(handles::get)
        val route = LanguageRouter.route("cut", en)
        var calls = 0
        val baseline = engine.select("cut", route, CasePattern.LOWER, CandidateSearchControl { calls++; false })
        assertEquals(CandidateCompletion.COMPLETE, baseline.completion)
        assertTrue(calls > 20)
        for (cancelAt in 1..calls) {
            var current = 0
            val result = engine.select("cut", route, CasePattern.LOWER, CandidateSearchControl { ++current >= cancelAt })
            assertEquals(CandidateCompletion.CANCELLED, result.completion)
            assertTrue(result.alternatives.isEmpty()); assertTrue(engine.isClear())
            assertEquals(baseline, engine.select("cut", route, CasePattern.LOWER, control()))
        }
    }

    @Test fun `strict cost prior bound cannot certify equality regardless of frequency`() {
        val reader = PackedCandidateLexicon(listOf(handle(mapOf("cat" to 1), en), handle(mapOf("zzzzz" to 1), es)))
        val candidate = CandidateGenerator(reader).generate("cut", en).alternatives.single()
        val quarters = (candidate.editFeatures.editCost * 4).toInt()
        assertFalse(PackedTopSeven.precedesBound(candidate, quarters, candidate.languagePrior))
        assertTrue(PackedTopSeven.precedesBound(candidate, quarters + 1, candidate.languagePrior))
        assertTrue(PackedTopSeven.precedesBound(candidate, quarters, candidate.languagePrior - 1))
    }

    @Test fun `unavailable selection does not expose earlier candidate payload`() {
        val engine = PackedTopSeven { null }
        assertEquals(TopCandidateSelection(CandidateCompletion.UNAVAILABLE),
            engine.select("cut", LanguageRouter.route("cut", en), CasePattern.LOWER, control()))
        assertTrue(engine.isClear())
    }
}
