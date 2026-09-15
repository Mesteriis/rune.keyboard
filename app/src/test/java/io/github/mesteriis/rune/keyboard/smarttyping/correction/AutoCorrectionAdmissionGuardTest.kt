package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalSearchEvidence
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyMembership
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AutoCorrectionAdmissionGuardTest {
    private fun candidate(word: String, cost: Double = 1.0) = GeneratedCandidate(
        word, word, word, KeyboardLanguage.RUSSIAN, false, 4, 10, 1,
        EditFeatures(cost, 0, 0.0), 0, CasePattern.LOWER)

    private fun generation(original: String, candidates: List<GeneratedCandidate>) = CandidateGeneration(
        original, candidates.take(1), CandidateCompletion.COMPLETE, false, null, 10, candidates.size,
        LocalSearchEvidence(CandidateCompletion.COMPLETE, candidates, 10, candidates.size))

    private fun guard(vararg rows: Pair<String, Int?>) = AutoCorrectionAdmissionGuard(
        MorphologyLexicon { _, key ->
            val record = rows.firstOrNull { it.first == key }
            if (record == null) MorphologyMembership.ABSENT else MorphologyMembership(true, true, record.second)
        })

    @Test fun `rare correct word absent from ranked dictionary is protected`() {
        val winner = candidate("почтение")
        assertFalse(guard("почтений" to 1, "почтение" to 1).allows(generation("почтений", listOf(winner)), winner))
    }

    @Test fun `complete competing set across lemmas vetoes despite omitted display alternative`() {
        val winner = candidate("нужен")
        val rival = candidate("нужно", 1.25).copy(frequencyRank = 1_000_000)
        assertFalse(guard("нужен" to 1, "нужно" to 2).allows(generation("нужнн", listOf(winner, rival)), winner))
    }

    @Test fun `clearly worse other lemma does not veto`() {
        val winner = candidate("нужен")
        assertTrue(guard("нужен" to 1, "нужно" to 2).allows(
            generation("нужнн", listOf(winner, candidate("нужно", 1.26))), winner))
    }

    @Test fun `same lemma may clear this veto without granting automatic permission`() {
        val winner = candidate("слово")
        assertTrue(guard("слово" to 1, "слова" to 1).allows(
            generation("словаа", listOf(winner, candidate("слова"))), winner))
    }

    @Test fun `missing dictionary and unknown or ambiguous analysis veto`() {
        val winner = candidate("слово")
        val generation = generation("словоо", listOf(winner))
        assertFalse(AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE).allows(generation, winner))
        assertFalse(guard().allows(generation, winner))
        assertFalse(guard("слово" to null).allows(generation, winner))
        assertFalse(guard("слово" to 1).allows(generation("словоо", listOf(winner, candidate("слова"))), winner))
    }

    @Test fun `unknown analysis of plausible rival vetoes`() {
        val winner = candidate("слово")
        assertFalse(guard("слово" to 1, "слова" to null).allows(
            generation("словоо", listOf(winner, candidate("слова"))), winner))
    }

    @Test fun `case identity and other languages retain existing policy ownership`() {
        val case = candidate("Москва").copy(terminalKey = "москва", kind = GeneratedCandidateKind.CANONICAL_CASE)
        val unavailable = AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE)
        assertTrue(unavailable.allows(generation("москва", listOf(case)), case))
        val english = candidate("hello").copy(language = KeyboardLanguage.ENGLISH)
        assertTrue(unavailable.allows(generation("helloo", listOf(english)), english))
    }
}
