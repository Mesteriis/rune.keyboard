package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyMembership
import java.io.File
import java.nio.ByteBuffer
import org.junit.Assert.*
import org.junit.Test

class InfinitiveRevisionScopeTest {
    private val scope = InfinitiveRevisionScope(dictionary)
    private val sameLemma = MorphologyLexicon { _, _ -> MorphologyMembership(true, true, 100) }

    @Test fun dictionaryInfinitivesAfterModalAndTransparentContextCanBeReconsidered() {
        for ((context, previous, proposed) in listOf(
            Triple("тебе надо ", "научишься", "научиться"),
            Triple("Том начал немного ", "злишься", "злиться"),
            Triple("я не могу тебе ", "заплатишь", "заплатить"),
            Triple("тебе\tнадо\t", "научишься", "научиться"),
        )) assertNull(scope.refusal(context, previous, proposed, sameLemma))
    }

    @Test fun punctuationAndOtherInterveningWordsStopTheCue() {
        for (context in listOf("надо, ", "надо. ты ", "надо\nты ", "ты ", "он начал книгу "))
            assertEquals(InfinitiveRevisionRefusal.NO_INFINITIVE_CUE,
                scope.refusal(context, "научишься", "научиться", sameLemma))
    }

    @Test fun allDictionaryPartsAreCheckedRatherThanGuessingTheIntendedAnalysis() {
        assertTrue(dictionary.analyses("мыла").analyses.any { it.pos == "NOUN" })
        assertTrue(dictionary.analyses("мыла").analyses.any { it.pos == "VERB" })
        assertEquals(InfinitiveRevisionRefusal.PREVIOUS_NOT_UNAMBIGUOUS_FINITE,
            scope.refusal("надо ", "мыла", "мыть", sameLemma))
        assertTrue(dictionary.analyses("печь").analyses.any { it.pos == "NOUN" })
        assertTrue(dictionary.analyses("печь").analyses.any { it.pos == "INFN" })
        assertEquals(InfinitiveRevisionRefusal.PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE,
            scope.refusal("надо ", "печёшь", "печь", sameLemma))
    }

    @Test fun missingAmbiguousAndDifferentLemmaEvidenceAllDecline() {
        for (evidence in listOf(MorphologyMembership.UNAVAILABLE, MorphologyMembership.ABSENT,
            MorphologyMembership(true, true))) {
            assertEquals(InfinitiveRevisionRefusal.LEMMA_UNAVAILABLE,
                scope.refusal("надо ", "научишься", "научиться", MorphologyLexicon { _, _ -> evidence }))
        }
        val different = MorphologyLexicon { _, key -> MorphologyMembership(true, true,
            if (key == "научишься") 100 else 101) }
        assertEquals(InfinitiveRevisionRefusal.DIFFERENT_LEMMA,
            scope.refusal("надо ", "научишься", "научиться", different))
        assertEquals(InfinitiveRevisionRefusal.UNCHANGED,
            scope.refusal("надо ", "научишься", "научишься", sameLemma))
    }

    companion object {
        private val dictionary by lazy {
            GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
                "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()),
                FrozenContextualAssets.GRAMMAR_SHA256)!!
        }
    }
}
