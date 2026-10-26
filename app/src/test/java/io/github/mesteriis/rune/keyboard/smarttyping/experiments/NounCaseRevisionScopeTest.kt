package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyMembership
import java.io.File
import java.nio.ByteBuffer
import org.junit.Assert.*
import org.junit.Test

class NounCaseRevisionScopeTest {
    private val scope = NounCaseRevisionScope(dictionary)
    private val sameLemma = MorphologyLexicon { _, _ -> MorphologyMembership(true, true, 100) }

    @Test fun unambiguousSingularNounsAfterAnObjectCueCanBeReconsidered() {
        for (context in listOf("Том показал мне ", "я вижу ", "он показал тебе ", "том\tпоказал\tмне\t")) {
            assertNull(scope.preconditionRefusal(context, "фотографией", sameLemma))
            assertNull(scope.refusal(context, "фотографией", "фотографию", sameLemma))
        }
    }

    @Test fun punctuationPrepositionsAndOtherInterveningWordsDoNotInventAnObjectCue() {
        for (context in listOf("с ", "показал, ", "показал\n ", "он ", "он показал книгу ")) {
            assertEquals(NounCaseRevisionRefusal.NO_ACCUSATIVE_CUE,
                scope.preconditionRefusal(context, "фотографией", sameLemma))
            assertEquals(NounCaseRevisionRefusal.NO_ACCUSATIVE_CUE,
                scope.refusal(context, "фотографией", "фотографию", sameLemma))
        }
    }

    @Test fun everyPartCaseAndNumberMustMatchInsteadOfSelectingOneConvenientAnalysis() {
        for (previous in listOf("фотографию", "фотографиями", "мыла", "неттакогослова"))
            assertEquals(NounCaseRevisionRefusal.PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL,
                scope.refusal("я вижу ", previous, "книгу", sameLemma))
        for (proposed in listOf("фотография", "фотографии", "научиться", "стали", "неттакогослова"))
            assertEquals(NounCaseRevisionRefusal.PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE,
                scope.refusal("я вижу ", "фотографией", proposed, sameLemma))
        assertEquals(NounCaseRevisionRefusal.UNCHANGED,
            scope.refusal("я вижу ", "фотографией", "фотографией", sameLemma))
    }

    @Test fun bothNounsNeedTheSameAvailablePositivePackedLemmaId() {
        for (failure in listOf(MorphologyMembership.UNAVAILABLE, MorphologyMembership.ABSENT,
            MorphologyMembership(true, true), MorphologyMembership(true, true, 0), MorphologyMembership(true, true, -1))) {
            for (missingWord in listOf("фотографией", "фотографию")) {
                val evidence = MorphologyLexicon { _, word ->
                    if (word == missingWord) failure else MorphologyMembership(true, true, 100)
                }
                assertEquals(NounCaseRevisionRefusal.LEMMA_UNAVAILABLE,
                    scope.refusal("я вижу ", "фотографией", "фотографию", evidence))
            }
        }
        assertEquals(NounCaseRevisionRefusal.DIFFERENT_LEMMA,
            scope.refusal("я вижу ", "фотографией", "фотографию", MorphologyLexicon { _, word ->
                MorphologyMembership(true, true, if (word == "фотографией") 100 else 101)
            }))
    }

    companion object {
        private val dictionary by lazy {
            GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
                "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()),
                FrozenContextualAssets.GRAMMAR_SHA256)!!
        }
    }
}
