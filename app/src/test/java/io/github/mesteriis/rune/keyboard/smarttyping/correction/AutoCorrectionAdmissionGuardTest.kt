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
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AutoCorrectionAdmissionGuardTest {
    @Test fun wordContextRequiresItsOwnCompleteKnownInternalEdit() {
        val word = candidate("новый")
        val input = generation("новй", listOf(word)).copy(jointEvaluated = true,
            jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(word), 10, 1))
        val admission = guard("новый" to null)
        assertTrue(admission.evaluateWordContext(input, word).allowed)
        assertFalse(admission.evaluateRescue(input, word).allowed)
        assertFalse(guard("новй" to 1, "новый" to null).evaluateWordContext(input, word).allowed)
        assertFalse(guard().evaluateWordContext(input, word).allowed)
        assertFalse(admission.evaluateWordContext(input.copy(isValidWord = true), word).allowed)
        assertFalse(admission.evaluateWordContext(input.copy(jointSearch = LocalSearchEvidence.NONE), word).allowed)
        assertFalse(admission.evaluateWordContext(input.copy(original = "новы"), word).allowed)
        assertFalse(admission.evaluateWordContext(input, word.copy(frequencyRank = 50001)).allowed)
        assertFalse(admission.evaluateWordContext(input, candidate("новой")).allowed)
    }

    @Test fun rescueNeedsCompleteKnownTargetAndProtectsKnownOriginal() {
        val word = candidate("словарь")
        val input = generation("сдоварь", listOf(word)).copy(jointEvaluated = true,
            jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(word), 10, 1))
        val admission = guard("словарь" to null)
        assertTrue(admission.evaluateRescue(input, word).allowed)
        assertFalse(guard("сдоварь" to 1, "словарь" to 2).evaluateRescue(input, word).allowed)
        assertFalse(guard().evaluateRescue(input, word).allowed)
        assertFalse(admission.evaluateRescue(input.copy(jointEvaluated = false), word).allowed)
        assertFalse(admission.evaluateRescue(input.copy(jointSearch = LocalSearchEvidence.NONE), word).allowed)
        assertFalse(admission.evaluateRescue(input, word.copy(frequencyRank = 50_001)).allowed)
    }
    @Test fun rareShortOriginalCanOfferFrequentManualWordsWithoutChangingProtection() {
        val rare = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon {
            io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordMembership(true, it == "тпо", 100_000)
        }
        val morphology = MorphologyLexicon { _, _ -> MorphologyMembership.ABSENT }
        val common = candidate("топ").copy(frequencyRank = 100)
        val unusual = candidate("тпа").copy(frequencyRank = 30_000)
        assertTrue(PublicOriginalProtection.manualPreference("тпо", common, morphology, rare) >
            PublicOriginalProtection.manualPreference("тпо", unusual, morphology, rare))
        assertEquals(0.0, PublicOriginalProtection.manualPreference("Тпо", common, morphology, rare), 0.0)
        assertEquals(0.0, PublicOriginalProtection.manualPreference("тпо", common,
            MorphologyLexicon { _, _ -> MorphologyMembership(true, true, 1) }, rare), 0.0)
        assertEquals(0.0, PublicOriginalProtection.manualPreference("тпо", common, MorphologyLexicon.UNAVAILABLE, rare), 0.0)
        assertFalse(PublicOriginalProtection.evaluate(generation("тпо", listOf(common)), common, rare).allowed)
    }

    @Test fun `qualified joint comparison may admit a known ambiguous unique local winner`() {
        val winner = candidate("стола")
        val input = generation("стлла", listOf(winner)).copy(jointEvaluated = true,
            jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(winner), 10, 1))
        val admission = guard("стола" to null)
        assertFalse(admission.evaluateRefinement(input, winner, listOf("стлла", "стола")).allowed)
        assertFalse(admission.evaluateJoint(input, winner, false).allowed)
        assertTrue(admission.evaluateJoint(input, winner, true).allowed)
        assertFalse(guard("стлла" to 2, "стола" to null).evaluateJoint(input, winner, true).allowed)
        assertFalse(guard().evaluateJoint(input, winner, true).allowed)
        for (cost in listOf(Double.NaN, Double.POSITIVE_INFINITY, -1.0)) {
            val invalid = candidate("стола", cost)
            val bad = input.copy(localSearch = input.localSearch.copy(alternatives = listOf(invalid)),
                jointSearch = input.jointSearch.copy(alternatives = listOf(invalid)))
            assertFalse(admission.evaluateJoint(bad, invalid, true).allowed)
        }
        assertFalse(AutoCorrectionAdmissionGuard(MorphologyLexicon { _, _ -> MorphologyMembership.UNAVAILABLE })
            .evaluateJoint(input, winner, true).allowed)
        for (unqualified in listOf(input.copy(jointEvaluated = false),
            input.copy(jointSearch = LocalSearchEvidence.NONE),
            input.copy(localSearch = LocalSearchEvidence.NONE),
            input.copy(localSearch = input.localSearch.copy(alternatives = listOf(winner, candidate("стила")))),
            input.copy(jointSearch = input.jointSearch.copy(alternatives = listOf(candidate("стила")))))) {
            assertFalse(admission.evaluateJoint(unqualified, winner, true).allowed)
        }
    }

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

    @Test fun `refinement resolves only known rivals included in the same request`() {
        val winner = candidate("нужен")
        val rival = candidate("нужно")
        val input = generation("нужнн", listOf(winner, rival))
        val admission = guard("нужен" to 1, "нужно" to 2)
        assertFalse(admission.evaluateRefinement(input, winner, listOf("нужен")).allowed)
        assertTrue(admission.evaluateRefinement(input, winner, listOf("нужен", "нужно")).allowed)
        assertFalse(guard("нужен" to 1, "нужно" to null)
            .evaluateRefinement(input, winner, listOf("нужен", "нужно")).allowed)
        assertFalse(admission.evaluateRefinement(input, winner, listOf("нужно")).allowed)
        assertFalse(guard("нужнн" to 3, "нужен" to 1, "нужно" to 2)
            .evaluateRefinement(input, winner, listOf("нужен", "нужно")).allowed)
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

    @Test fun `independently qualified local winner is not vetoed by incomplete morphology`() {
        val winner = candidate("повременить").copy(frequencyRank = 42_858)
        val rival = candidate("переменить").copy(frequencyRank = Int.MAX_VALUE)
        val input = generation("пвременить", listOf(winner, rival))
        assertEquals(winner.canonicalKey,
            LocalCorrectionPolicy.decide(input, KeyboardLanguage.RUSSIAN)?.canonicalKey)
        assertTrue(guard(winner.terminalKey to 1, rival.terminalKey to 2).allows(input, winner))

        val unknownWinner = candidate("терминатор").copy(frequencyRank = 41_100)
        val singleton = generation("ерминатор", listOf(unknownWinner))
        assertEquals(unknownWinner.canonicalKey,
            LocalCorrectionPolicy.decide(singleton, KeyboardLanguage.RUSSIAN)?.canonicalKey)
        assertTrue(guard(unknownWinner.terminalKey to null).allows(singleton, unknownWinner))
    }

    @Test fun `missing dictionary and unknown or ambiguous analysis veto`() {
        val winner = candidate("слово")
        val generation = generation("словоо", listOf(winner))
        assertFalse(AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE).allows(generation, winner))
        assertFalse(guard().allows(generation, winner))
        assertFalse(guard("слово" to null).allows(generation, winner))
        assertFalse(guard("слово" to 1).allows(generation("словоо", listOf(winner, candidate("слова"))), winner))
    }

    @Test fun `public rare original vetoes ordinary correction and unavailable evidence fails closed`() {
        val winner = candidate("пантера")
        val input = generation("хантера", listOf(winner))
        val present = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon {
            io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordMembership(true, true, 1)
        }
        val absent = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon {
            io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordMembership.ABSENT
        }
        assertEquals(AutomaticAdmissionRefusal.ORIGINAL_VALID,
            PublicOriginalProtection.evaluate(input, winner, present).refusal)
        assertEquals(AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE,
            PublicOriginalProtection.evaluate(input, winner,
                io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon.UNAVAILABLE).refusal)
        assertTrue(PublicOriginalProtection.evaluate(input, winner, absent).allowed)
        // Passing this veto never replaces the existing morphology/qualification policy.
        assertFalse(AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE).evaluate(input, winner).allowed)
        val reviewed = candidate("хочу").copy(kind = GeneratedCandidateKind.COMMON_CONFUSION)
        assertTrue(PublicOriginalProtection.evaluate(generation("зочу", listOf(reviewed)), reviewed, present).allowed)
        assertTrue(AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE)
            .evaluate(generation("зочу", listOf(reviewed)), reviewed).allowed)
        val fake = reviewed.copy(text = "пантера", terminalKey = "пантера")
        assertFalse(AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE)
            .evaluate(generation("зочу", listOf(fake)), fake).allowed)
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

    @Test fun `verified finite confusion retains its dedicated policy ownership`() {
        val reviewed = candidate("забирай").copy(kind = GeneratedCandidateKind.COMMON_CONFUSION)
        val rival = candidate("забегай")
        assertTrue(AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE)
            .allows(generation("заберай", listOf(reviewed, rival)), reviewed))

        val mislabeled = candidate("забегай").copy(kind = GeneratedCandidateKind.COMMON_CONFUSION)
        val rejected = AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE)
            .evaluate(generation("заберай", listOf(mislabeled)), mislabeled)
        assertFalse(rejected.allowed)
        assertEquals(AutomaticAdmissionRefusal.NOT_QUALIFIED, rejected.refusal)
    }

    @Test fun `explained admission is decision equivalent and reports only observed evidence`() {
        val winner = candidate("нужен")
        val rival = candidate("нужно", 1.25)
        val input = generation("нужнн", listOf(winner, rival))
        val unavailable = AutoCorrectionAdmissionGuard(MorphologyLexicon.UNAVAILABLE)
        assertEquals(unavailable.allows(input, winner), unavailable.evaluate(input, winner).allowed)
        assertEquals(AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE,
            unavailable.evaluate(input, winner).refusal)

        val competing = guard("нужен" to 1, "нужно" to 2)
        assertEquals(competing.allows(input, winner), competing.evaluate(input, winner).allowed)
        assertEquals(AutomaticAdmissionRefusal.RIVAL_OTHER_LEMMA,
            competing.evaluate(input, winner).refusal)

        val admitted = guard("нужен" to 1, "нужно" to 1).evaluate(input, winner)
        assertTrue(admitted.allowed)
        assertNull(admitted.refusal)
    }
}
