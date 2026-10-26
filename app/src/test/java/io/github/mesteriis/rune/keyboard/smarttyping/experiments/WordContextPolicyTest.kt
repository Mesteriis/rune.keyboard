package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import org.junit.Assert.*
import org.junit.Test

class WordContextPolicyTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private fun candidate(word: String) = GeneratedCandidate(word, word, word, ru, false, 4, 10, 1,
        EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
    private val masculine = candidate("новый")
    private val feminine = candidate("новой")
    private val generation = CandidateGeneration("новй", listOf(feminine), CandidateCompletion.COMPLETE,
        false, null, 10, 2, LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(masculine, feminine), 10, 2))
        .let { it.copy(jointEvaluated = true, jointSearch = it.localSearch) }
    private fun evaluate(input: CandidateGeneration = generation, context: String = "нужен ") =
        WordContextPolicy.evaluate(context, input, ru)

    @Test fun supplementsOnlyAnActualAbstentionAndPreservesAppliedWinners() {
        assertFalse(WordContextPolicy.maySupplement(JointCorrectionChoice(masculine), null))
        assertFalse(WordContextPolicy.maySupplement(null, "новый"))
        assertTrue(WordContextPolicy.maySupplement(JointCorrectionChoice(null), "новый"))
        assertTrue(WordContextPolicy.maySupplement(null, null))
    }
    @Test fun onlyReviewedWholeContextAndLowercaseTypoCanSelectKnownTarget() {
        for (prefix in listOf("нужен ", "мне нужен ", "Нужен  ", "теперь\nнужен\t")) {
            assertEquals(masculine, evaluate(context = prefix).choice?.candidate)
            assertTrue(evaluate(context = prefix).choice!!.wordContext)
        }
        for (prefix in listOf("", "с ", "о ", "для ", "мой ", "нужен, ", "ненужен ", "@нужен ", "https://нужен ", "нужeн "))
            assertNull(prefix, evaluate(context = prefix).choice)
        for (original in listOf("Новй", "НОВЙ", "новы", "новий", "суел", "брт", "осадое", "кно", "еесли"))
            assertNull(evaluate(generation.copy(original = original)).choice)
    }
    @Test fun reviewedMeetingContextAvoidsTheSlowModelOnlyForTheExactKnownTypo() {
        val target = candidate("завтра")
        val input = generation.copy(original = "завтро", jointSearch = generation.jointSearch.copy(alternatives = listOf(target)))
        assertEquals(target, evaluate(input, "давай встретимся ").choice?.candidate)
        for (prefix in listOf("", "встретимся, ", "невстретимся ", "@встретимся ", "нужен "))
            assertNull(evaluate(input, prefix).choice)
        assertNull(evaluate(input.copy(original = "Завтро"), "встретимся ").choice)
        assertTrue(WordContextPolicy.isReviewedPair("завтро", "завтра"))
        assertFalse(WordContextPolicy.isReviewedPair("завтро", "наутро"))
    }
    @Test fun twoWordSuffixNeverCollapsesToAnUnconditionalAlreadyRule() {
        val target = candidate("домой")
        val input = generation.copy(original = "ддмой", jointSearch = generation.jointSearch.copy(alternatives = listOf(target)))
        for (prefix in listOf("я уже ", "сказал я уже ", "Я\tуже "))
            assertEquals(target, evaluate(input, prefix).choice?.candidate)
        for (prefix in listOf("уже ", "стала уже ", "она уже ", "я, уже ", "этоя уже ", "я уже, "))
            assertNull(evaluate(input, prefix).choice)
    }
    @Test fun incompleteProtectedMissingAndMalformedTargetsCannotAuthorize() {
        assertNull(evaluate(generation.copy(isValidWord = true)).choice)
        assertNull(evaluate(generation.copy(jointEvaluated = false)).choice)
        assertNull(evaluate(generation.copy(jointSearch = LocalSearchEvidence.NONE)).choice)
        for (pool in listOf(emptyList(), listOf(feminine), listOf(masculine, masculine),
            listOf(masculine.copy(frequencyRank = 50001)), listOf(masculine.copy(unitDistance = 2)),
            listOf(masculine.copy(editFeatures = EditFeatures(Double.NaN, 0, 0.0)))))
            assertNull(evaluate(generation.copy(jointSearch = generation.jointSearch.copy(alternatives = pool))).choice)
        assertNull(WordContextPolicy.evaluate("нужен ", generation, KeyboardLanguage.ENGLISH).choice)
    }
}
