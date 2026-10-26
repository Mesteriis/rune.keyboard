package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PublicCandidateAugmenterTest {
    private val russian = KeyboardLanguage.RUSSIAN

    @Test fun `retrieves direct morphology and rare unit edits`() {
        val morphology = MorphologyLexicon { _, word ->
            if (word == "кармен") MorphologyMembership(true, true, 12) else MorphologyMembership.ABSENT
        }
        val rare = RareWordLexicon { word ->
            if (word == "мигеля") RareWordMembership(true, true, 7) else RareWordMembership.ABSENT
        }
        val augmenter = PublicCandidateAugmenter(morphology, rare)
        val carmen = augmenter.augment("кармн", emptyList(), russian, 2, CasePattern.LOWER,
            CandidateCancellation { false })!!
        val miguel = augmenter.augment("миеля", emptyList(), russian, 2, CasePattern.LOWER,
            CandidateCancellation { false })!!
        assertTrue(carmen.any { it.text == "кармен" && it.kind == GeneratedCandidateKind.PUBLIC_AUGMENTED })
        assertTrue(miguel.any { it.text == "мигеля" && it.frequencyRank == 50_007 })
    }

    @Test fun `protects exact public source and fails closed when unavailable`() {
        val present = MorphologyLexicon { _, _ -> MorphologyMembership(true, true, 1) }
        val absent = RareWordLexicon { RareWordMembership.ABSENT }
        assertNull(PublicCandidateAugmenter(present, absent).augment("кармен", emptyList(), russian,
            2, CasePattern.LOWER, CandidateCancellation { false }))
        assertNull(PublicCandidateAugmenter(MorphologyLexicon.UNAVAILABLE, absent).augment(
            "кармн", emptyList(), russian, 2, CasePattern.LOWER, CandidateCancellation { false }))
    }

    @Test fun `short word public expansion is manual only and preserves every baseline field`() {
        val lexicon = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("кот"), russian).ready()))
        val morphology = MorphologyLexicon { _, word ->
            if (word == "конь") MorphologyMembership(true, true, 12) else MorphologyMembership.ABSENT
        }
        val rare = RareWordLexicon { RareWordMembership.ABSENT }
        val generator = CandidateGenerator(lexicon, 3, morphologyLexicon = morphology, rareWordLexicon = rare)
        for (typed in listOf("кнь", "конб", "Кнь")) {
            val baseline = generator.generate(typed, russian)
            val before = baseline.copy()
            val manual = generator.generateManualPool(typed, russian, baseline, true)!!
            assertEquals(before, baseline)
            assertTrue(baseline.compactAlternatives.isEmpty())
            assertTrue(baseline.alternatives.none { it.terminalKey == "конь" })
            assertTrue(manual.alternatives.any { it.terminalKey == "конь" && it.kind == GeneratedCandidateKind.PUBLIC_AUGMENTED })
            assertEquals(LocalSearchEvidence.NONE, manual.localSearch)
            assertNull(generator.generateManualPool(typed, russian, baseline, false))
            assertNull(generator.generateManualPool(typed, russian, baseline, true, CandidateCancellation { true }))
        }
        val valid = generator.generate("кот", russian)
        assertNull(generator.generateManualPool("кот", russian, valid, true))
    }

    @Test fun `valid word neighbours are opt in display only and preserve original certificate`() {
        val lexicon = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("нуден"), russian).ready()))
        val morphology = MorphologyLexicon { _, word -> if (word in listOf("нуден", "нужен", "гуден", "руден", "уден", "буден", "дуден", "ноден",
                "нунен", "вуден", "нудей", "наден", "нурен", "нуде", "суден", "чуден"))
            MorphologyMembership(true, true, 12) else MorphologyMembership.ABSENT }
        val generator = CandidateGenerator(lexicon, 3, morphologyLexicon = morphology,
            rareWordLexicon = RareWordLexicon { RareWordMembership.ABSENT })
        val baseline = generator.generate("нуден", russian)
        assertTrue(baseline.isValidWord)
        val before = baseline.copy()
        val manual = generator.generateManualPool("нуден", russian, baseline, true)!!
        assertEquals(before, baseline)
        assertEquals(CandidateCompletion.VALID_WORD, baseline.completion)
        assertTrue(manual.alternatives.any { it.text == "нужен" })
        assertEquals(CandidateGenerator.MAX_ALTERNATIVES, manual.alternatives.size)
        assertTrue(manual.verifiedTerminals > manual.alternatives.size)
        assertTrue(manual.alternatives.all { it.kind == GeneratedCandidateKind.PUBLIC_AUGMENTED })
        assertEquals(LocalSearchEvidence.NONE, manual.localSearch)
        assertEquals(LocalSearchEvidence.NONE, manual.jointSearch)
        assertTrue(!manual.jointEvaluated)
        assertNull(generator.generateManualPool("нуден", russian, baseline, false))
        assertNull(generator.generateManualPool("нуден", russian, baseline, true, CandidateCancellation { true }))
    }

    @Test fun `joint short pool is complete separate evidence and protects valid originals`() {
        val lexicon = PackedCandidateLexicon(listOf(PackedFixture.build(listOf("кот", "кит", "код"), russian).ready()))
        val morphology = MorphologyLexicon { _, word ->
            if (word == "конь") MorphologyMembership(true, true, 12) else MorphologyMembership.ABSENT
        }
        val rare = RareWordLexicon { word -> if (word == "конб") RareWordMembership(true, true, 1) else RareWordMembership.ABSENT }
        val generator = CandidateGenerator(lexicon, 3, morphologyLexicon = morphology, rareWordLexicon = rare)
        val baseline = generator.generate("кнь", russian)
        val joint = generator.generateJointPool("кнь", russian, baseline)
        assertEquals(CandidateCompletion.COMPLETE, joint.completion)
        assertTrue(joint.alternatives.any { it.text == "конь" })
        assertEquals(LocalSearchEvidence.NONE, baseline.localSearch)
        assertTrue(baseline.jointSearch.alternatives.isEmpty())
        val protected = generator.generate("конб", russian)
        assertEquals(CandidateCompletion.VALID_WORD, generator.generateJointPool("конб", russian, protected).completion)
        val unavailable = CandidateGenerator(lexicon)
        assertTrue(!unavailable.generateJointPool("кнь", russian, baseline).isComplete)
        assertEquals(CandidateCompletion.CANCELLED,
            generator.generateJointPool("кнь", russian, baseline, CandidateCancellation { true }).completion)
        val broken = CandidateGenerator(lexicon, morphologyLexicon = MorphologyLexicon { _, _ ->
            error("reader unavailable") }, rareWordLexicon = rare)
        val refused = broken.generateJointPool("кнь", russian, baseline)
        assertEquals(CandidateCompletion.READER_FAILURE, refused.completion)
        assertTrue(refused.alternatives.isEmpty())
    }

    @Test fun `keeps existing candidate identity`() {
        val absentMorph = MorphologyLexicon { _, _ -> MorphologyMembership.ABSENT }
        val absentRare = RareWordLexicon { RareWordMembership.ABSENT }
        val existing = emptyList<GeneratedCandidate>()
        assertEquals(existing, PublicCandidateAugmenter(absentMorph, absentRare).augment(
            "кармн", existing, russian, 2, CasePattern.LOWER, CandidateCancellation { false }))
    }
}
