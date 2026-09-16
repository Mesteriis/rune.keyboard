package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalSearchEvidence
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LocalCorrectionPolicyTest {
    private fun candidate(text: String, rank: Int) = GeneratedCandidate(
        text, text, text, KeyboardLanguage.RUSSIAN, false, 4, rank, 1,
        EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)

    private fun generation(original: String, candidates: List<GeneratedCandidate>,
        completion: CandidateCompletion = CandidateCompletion.COMPLETE) = CandidateGeneration(
        original, candidates.take(3), CandidateCompletion.STATES_EXHAUSTED, false, null, 8_192,
        candidates.size, LocalSearchEvidence(completion, candidates, 20, candidates.size))

    @Test fun `qualified complete local search can decide despite extended exhaustion`() {
        val winner = candidate("несколько", 20)
        val decision = LocalCorrectionPolicy.decide(
            generation("нескрлько", listOf(winner, candidate("насколько", 1_000_000))),
            KeyboardLanguage.RUSSIAN)
        assertEquals(winner.canonicalKey, decision?.canonicalKey)
    }

    @Test fun `incomplete short and ambiguous searches abstain`() {
        val candidates = listOf(candidate("нужен", 10), candidate("нужно", 11))
        assertNull(LocalCorrectionPolicy.decide(generation("нужнн", candidates), KeyboardLanguage.RUSSIAN))
        assertNull(LocalCorrectionPolicy.decide(generation("твм", candidates), KeyboardLanguage.RUSSIAN))
        assertNull(LocalCorrectionPolicy.decide(
            generation("нужнн", candidates, CandidateCompletion.STATES_EXHAUSTED),
            KeyboardLanguage.RUSSIAN))
    }

    @Test fun `explained policy preserves decisions and first known refusal`() {
        val winner = candidate("несколько", 20)
        val inputs = listOf(
            generation("нескрлько", listOf(winner)),
            generation("нескрлько", listOf(winner), CandidateCompletion.STATES_EXHAUSTED),
            generation("мало", listOf(winner)),
            generation("нескрлько", emptyList()),
        )
        for (input in inputs) {
            assertEquals(LocalCorrectionPolicy.decide(input, KeyboardLanguage.RUSSIAN),
                LocalCorrectionPolicy.evaluate(input, KeyboardLanguage.RUSSIAN).decision)
        }
        assertNull(LocalCorrectionPolicy.evaluate(inputs[0], KeyboardLanguage.RUSSIAN).refusal)
        assertEquals(LocalCorrectionRefusal.SEARCH_INCOMPLETE,
            LocalCorrectionPolicy.evaluate(inputs[1], KeyboardLanguage.RUSSIAN).refusal)
        assertEquals(LocalCorrectionRefusal.TOO_SHORT,
            LocalCorrectionPolicy.evaluate(inputs[2], KeyboardLanguage.RUSSIAN).refusal)
        assertEquals(LocalCorrectionRefusal.NO_CANDIDATES,
            LocalCorrectionPolicy.evaluate(inputs[3], KeyboardLanguage.RUSSIAN).refusal)
    }

    @Test fun `title case is limited to qualified Russian branch`() {
        val russian = candidate("несколько", 20)
        val title = russian.copy(text = "Несколько", casePattern = CasePattern.TITLE)
        assertEquals(russian.canonicalKey, LocalCorrectionPolicy.decide(
            generation("Нескрлько", listOf(title)), KeyboardLanguage.RUSSIAN)?.canonicalKey)
        val spanish = candidate("victoria", 20).copy(
            language = KeyboardLanguage.SPANISH,
            casePattern = CasePattern.LOWER,
        )
        assertNull(LocalCorrectionPolicy.decide(
            generation("Victoria", listOf(spanish)),
            KeyboardLanguage.SPANISH,
        ))
    }

}
