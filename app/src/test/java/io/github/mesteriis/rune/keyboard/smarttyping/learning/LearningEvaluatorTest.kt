package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import org.junit.Assert.*
import org.junit.Test

class LearningEvaluatorTest {
    private val en = KeyboardLanguage.ENGLISH
    private val words = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green", "table", "word", "house")
    private fun result(original: String, alternatives: List<GeneratedCandidate> = emptyList(), completion: CandidateCompletion = CandidateCompletion.COMPLETE) =
        CandidateGeneration(original, alternatives, completion, false, null, 0, 0)
    private fun candidate(word: String) = GeneratedCandidate(word, word, word, en, false, 1, 1, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
    @Test fun emptyMissingIdentityUnavailableAndCancellationHaveDenominators() {
        val empty = LearningEvaluator.evaluate(LearningSnapshot(), { _, _ -> error("Not called") })
        assertEquals(0, empty.evaluated)
        val held = words.first { LearningModel.holdout(en, it) }
        val model = LearningModel().apply {
            configure(true, true, true)
            record(held, held, en, FeedbackSource.CONFIRMED)
            record(held + "z", held, en, FeedbackSource.ACCEPTED)
        }
        val outcome = LearningEvaluator.evaluate(model.snapshot(), { word, _ -> result(word) })
        assertEquals(2, outcome.evaluated); assertEquals(1, outcome.missingCandidates)
        assertEquals(1, outcome.identities); assertEquals(1, outcome.baselinePreserved)
        assertEquals(1, outcome.learnedPreserved)
        val unavailable = LearningEvaluator.evaluate(model.snapshot(), { word, _ -> result(word, completion = CandidateCompletion.UNAVAILABLE) })
        assertEquals(0, unavailable.evaluated); assertEquals(2, unavailable.unavailable)
        val cancelled = LearningEvaluator.evaluate(model.snapshot(), { _, _ -> error("Not called") }, { true })
        assertTrue(cancelled.cancelled); assertEquals(0, cancelled.evaluated)
    }
    @Test fun stableRerankSameFiniteCandidatesAndRepeatableFrozenBenchmark() {
        val model = LearningModel().apply { configure(true, true, true) }
        words.filterNot { LearningModel.holdout(en, it) }.take(3).forEach { model.record(it + "z", it, en, FeedbackSource.ACCEPTED) }
        val original = "plantz"
        val alternatives = listOf(candidate("planet"), candidate("plant"), candidate("plantr"))
        val ranked = LearningEvaluator.rerank(model.snapshot(), original, en, alternatives)
        assertEquals("plant", ranked.first().text)
        assertEquals(alternatives.toSet(), ranked.toSet())
        assertEquals(listOf("planet", "plantr"), ranked.drop(1).map { it.text })
        val held = words.first { LearningModel.holdout(en, it) }
        model.record(held + "z", held, en, FeedbackSource.ACCEPTED)
        val snapshot = model.snapshot()
        val first = LearningEvaluator.evaluate(snapshot, { word, _ -> result(word, listOf(candidate(held))) })
        assertEquals(first, LearningEvaluator.evaluate(snapshot, { word, _ -> result(word, listOf(candidate(held))) }))
        assertEquals(snapshot, model.snapshot())
    }
    @Test fun contradictoryLabelsNeverBecomeEvaluationTruth() {
        val held = words.first { LearningModel.holdout(en, it) }
        val model = LearningModel().apply { configure(true, true, true) }
        model.record(held + "z", held, en, FeedbackSource.ACCEPTED)
        model.record(held + "z", held, en, FeedbackSource.REJECTED)
        assertEquals(0, LearningEvaluator.evaluate(model.snapshot(), { _, _ -> error("Excluded") }).heldOut)
    }
}
