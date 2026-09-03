package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import java.security.MessageDigest
import java.util.zip.GZIPInputStream
import org.junit.Assert.*
import org.junit.Test

class CandidateRankerTest {
    private fun candidate(id: Int, rank: Int = 1, quarters: Int = 4, repeats: Int = 0,
        fallback: Boolean = false, difference: Int = 0) = GeneratedCandidate(
        "candidate$id", "candidate$id", "candidate$id", KeyboardLanguage.ENGLISH,
        fallback, 4, rank, 1, EditFeatures(quarters / 4.0, repeats, repeats * .25), difference, CasePattern.LOWER)

    private fun generation(candidates: List<GeneratedCandidate>, original: String = "czt", veto: Boolean = false) =
        CandidateGeneration(original, candidates, if (veto) CandidateCompletion.PROTECTED else CandidateCompletion.COMPLETE,
            false, null, 0, candidates.size)

    @Test fun `independent calibration oracle matches every deterministic and combined decision`() {
        val raw = GZIPInputStream(checkNotNull(javaClass.getResourceAsStream("/smarttyping/ranker/calibration.tsv.gz"))).use { it.readBytes() }
        val digest = MessageDigest.getInstance("SHA-256").digest(raw).joinToString("") { "%02x".format(it.toInt() and 255) }
        assertEquals(FIXTURE_SHA, digest)
        val policies = HashMap<Pair<String, Int>, Triple<RankingWeights, RankingThresholds, Int>>()
        var requests = 0
        for (line in raw.toString(Charsets.US_ASCII).lineSequence().filter { it.isNotEmpty() }) {
            val f = line.split('\t')
            if (f[0] == "P") {
                val n = f.drop(3).map(String::toInt)
                policies[f[1] to f[2].toInt()] = Triple(RankingWeights(n[0], n[1], n[2], n[3], n[4]),
                    RankingThresholds(n[5], n[6], n[7]), n[8])
                val selected = CalibratedSpellingPolicy.coefficients(language(f[1]), f[2] == "1")
                assertEquals(selected.weights, policies.getValue(f[1] to f[2].toInt()).first)
                assertEquals(selected.thresholds, policies.getValue(f[1] to f[2].toInt()).second)
                assertEquals(selected.modelWeight, n[8])
                continue
            }
            assertEquals("R", f[0]); assertEquals(requests++, f[1].toInt())
            val candidates = if (f[5] == "-") emptyList() else f[5].split(';').mapIndexed { index, fields ->
                val n = fields.split(',').map(String::toInt)
                assertEquals(index + 1, n[0])
                candidate(n[0], n[2], n[1], n[3], n[4] == 1, n[5])
            }
            val scores = if (f[6] == "-") null else f[6].split(';').map {
                val n = it.split(','); RankingModelScore(n[0].toInt(), n[1].toDouble(), n[2].toInt())
            }
            val input = generation(candidates, "z".repeat(f[3].toInt()), f[4] == "1")
            val det = policies.getValue(f[2] to 0)
            val model = policies.getValue(f[2] to 1)
            val fallback = CandidateRanker.choose(CandidateRanker.propose(input, det.first), det.second)
            val proposal = CandidateRanker.propose(input, model.first, model.third, scores)
            assertEquals("model availability ${f[1]}", f[9] == "1", proposal != null)
            val combined = if (proposal == null) fallback else CandidateRanker.choose(proposal, model.second)
            assertEquals("deterministic ${f[1]}", f[7].toInt(), fallback)
            assertEquals("combined ${f[1]}", f[8].toInt(), combined)
            assertEquals("production deterministic ${f[1]}", fallback,
                CalibratedSpellingPolicy.rank(input, language(f[2]))?.preferredId ?: 0)
            assertEquals("production combined ${f[1]}", combined,
                CalibratedSpellingPolicy.rank(input, language(f[2]), scores)?.preferredId ?: 0)
        }
        assertEquals(6, policies.size); assertEquals(6000, requests)
    }

    @Test fun `averages combine with edit frequency and both rival margins`() {
        val input = generation(listOf(candidate(1), candidate(2, rank = 8)))
        val weights = RankingWeights(2, 1, 0, 0, 0)
        val scores = listOf(RankingModelScore(0, -20.0, 2), RankingModelScore(1, -7.0, 1), RankingModelScore(2, -3.0, 3))
        val proposal = CandidateRanker.propose(input, weights, 2, scores)!!
        assertEquals(RankingProposal(2, -7.0, 2.0, 3), proposal)
        assertEquals(2, CandidateRanker.choose(proposal, RankingThresholds(6, 4, 1)))
        assertEquals(0, CandidateRanker.choose(proposal, RankingThresholds(6, 10, 1)))
        assertEquals(RankingProposal(1, 8.0, 11.0, 3), CandidateRanker.propose(input, weights, 0, scores))
    }

    @Test fun `malformed model evidence overflow and veto fail closed with immediate reuse`() {
        val input = generation(listOf(candidate(1)))
        val weights = RankingWeights(2, 1, 0, 0, 0)
        val good = listOf(RankingModelScore(0, -2.0, 1), RankingModelScore(1, -1.0, 1))
        val malformed = listOf(null, emptyList(), listOf(good[1]), listOf(good[0], good[0]),
            listOf(good[0], good[1].copy(candidateId = 2)), listOf(good[0], good[1].copy(tokenCount = 0)),
            listOf(good[0], good[1].copy(tokenCount = 257)), listOf(good[0], good[1].copy(sumLogProbability = Double.NaN)),
            listOf(good[0], good[1].copy(sumLogProbability = 1.0)),
            listOf(good[0].copy(sumLogProbability = -1.7e308), good[1].copy(sumLogProbability = 0.0)))
        for (bad in malformed) {
            assertNull(CandidateRanker.propose(input, weights, 8, bad))
            assertNotNull(CandidateRanker.propose(input, weights, 8, good))
        }
        assertNull(CandidateRanker.propose(input.copy(completion = CandidateCompletion.STATES_EXHAUSTED), weights))
        assertNull(CandidateRanker.propose(input.copy(completion = CandidateCompletion.VERIFIED_EXHAUSTED), weights))
        assertNull(CandidateRanker.propose(input.copy(isValidWord = true), weights))
        assertNull(CandidateRanker.propose(generation((1..8).map { candidate(it) }), weights))
    }

    @Test fun `ties keep original and word length counts code points`() {
        val weights = RankingWeights(2, 1, 0, 0, 0)
        val tie = CandidateRanker.propose(generation(listOf(candidate(1), candidate(2))), weights)
        assertEquals(0, CandidateRanker.choose(tie, RankingThresholds(20, 1, 1)))
        val scalar = CandidateRanker.propose(generation(listOf(candidate(1)), "😀"), weights)!!
        assertEquals(1, scalar.tokenLength)
        assertEquals(0, CandidateRanker.choose(scalar, RankingThresholds(20, 1, 2)))
        assertThrows(IllegalArgumentException::class.java) { RankingThresholds(20, 0, 1) }
        assertThrows(IllegalArgumentException::class.java) { RankingWeights(Int.MAX_VALUE, 1, 0, 0, 0) }
        assertThrows(IllegalArgumentException::class.java) { RankingProposal(1, Double.NEGATIVE_INFINITY, null, 3) }
    }

    @Test fun `unusable model falls back and oversized returned sets do not inherit confidence`() {
        val input = generation(listOf(candidate(1)))
        val deterministic = CalibratedSpellingPolicy.rank(input, KeyboardLanguage.ENGLISH)!!
        assertEquals(1, deterministic.preferredId)
        val malformed = listOf(RankingModelScore(0, -2.0, 1), RankingModelScore(1, Double.NaN, 1))
        assertEquals(deterministic, CalibratedSpellingPolicy.rank(input, KeyboardLanguage.ENGLISH, malformed))
        val wide = generation((1..7).map { candidate(it, quarters = if (it == 1) 1 else 8) })
        val ranked = CalibratedSpellingPolicy.rank(wide, KeyboardLanguage.ENGLISH)!!
        assertEquals(7, ranked.candidateIds.size)
        assertEquals(0, ranked.preferredId)
    }

    companion object { private const val FIXTURE_SHA = "bfc1dfd94aea987ee0624d30e5a1c5defa032286e771606c5d2a4ee09bdd9f79" }

    private fun language(value: String) = when (value) {
        "en" -> KeyboardLanguage.ENGLISH
        "ru" -> KeyboardLanguage.RUSSIAN
        "es" -> KeyboardLanguage.SPANISH
        else -> error("Unknown fixture language")
    }
}
