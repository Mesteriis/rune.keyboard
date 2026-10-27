package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import org.junit.Assert.*
import org.junit.Test

class LearningEvaluatorTest {
    @Test fun progressUsesTheSameVetoAndConflictFilteringAsReplay() {
        val word = words.first { LearningModel.holdout(en, it) }
        val model = LearningModel().apply { configure(true, true, true) }
        model.record(word, word, en, FeedbackSource.CONFIRMED)
        model.record(word + "z", word, en, FeedbackSource.ACCEPTED)
        model.record(word + "y", word, en, FeedbackSource.ACCEPTED)
        assertEquals(LearningHoldoutProgress(3, 2, 1), LearningEvaluator.holdoutProgress(model.snapshot()))
        model.record(word + "z", word, en, FeedbackSource.REJECTED)
        assertEquals(LearningHoldoutProgress(2, 1, 1), LearningEvaluator.holdoutProgress(model.snapshot()))
        model.record(word + "y", "different", en, FeedbackSource.ACCEPTED)
        assertEquals(LearningHoldoutProgress(1, 0, 1), LearningEvaluator.holdoutProgress(model.snapshot()))
    }

    @Test fun sampleProgressRequiresAllThreeIndependentMinimums() {
        assertFalse(LearningHoldoutProgress(19, 14, 5).hasMinimumSamples)
        assertFalse(LearningHoldoutProgress(20, 9, 11).hasMinimumSamples)
        assertFalse(LearningHoldoutProgress(20, 16, 4).hasMinimumSamples)
        assertTrue(LearningHoldoutProgress(20, 15, 5).hasMinimumSamples)
        assertFalse(LearningEvaluator.holdoutProgress(LearningSnapshot()).hasMinimumSamples)
    }

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

    @Test fun rollbackReplayChallengesActivePolicyAgainstRetainedBaseline() {
        val model = LearningModel().apply { configure(true, true, true) }
        words.filterNot { LearningModel.holdout(en, it) }.take(3).forEach {
            model.record(it + "z", it, en, FeedbackSource.ACCEPTED)
        }
        assertTrue(model.promoteCandidate(model.snapshot()))
        val expected = words.first { LearningModel.holdout(en, it) }
        val original = expected.dropLast(1) + if (expected.last() == 'x') 'y' else 'x'
        assertTrue(model.record(original, expected, en, FeedbackSource.ACCEPTED))
        val wrongDeletion = original.dropLast(1)
        val evaluation = checkNotNull(LearningEvaluator.evaluateRollback(model.snapshot(), { word, _ ->
            assertEquals(original, word)
            result(word, listOf(candidate(expected), candidate(wrongDeletion)))
        }))
        assertEquals(1, evaluation.regressions)
        assertEquals(0, evaluation.improvements)
        assertTrue(evaluation.promotion.rollbackRequired)
    }

    @Test fun promotionRequiresEnoughEvidenceImprovementAndZeroRegressions() {
        val improvement = LearningEvaluator.promotionDecision(
            evaluated = 20, correctionRows = 15, identities = 5,
            baselineTop = 10, learnedTop = 11, baselinePreserved = 5,
            learnedPreserved = 5, improvements = 1, regressions = 0,
            unavailable = 0, cancelled = false, candidateChanged = true,
        )
        assertTrue(improvement.promotionApproved)
        assertFalse(improvement.rollbackRequired)

        val regression = LearningEvaluator.promotionDecision(
            evaluated = 20, correctionRows = 15, identities = 5,
            baselineTop = 10, learnedTop = 10, baselinePreserved = 5,
            learnedPreserved = 5, improvements = 1, regressions = 1,
            unavailable = 0, cancelled = false, candidateChanged = true,
        )
        assertFalse(regression.promotionApproved)
        assertTrue(regression.rollbackRequired)
        assertTrue(regression.reasons.contains("NEW_REGRESSION"))

        val small = LearningEvaluator.promotionDecision(
            evaluated = 19, correctionRows = 14, identities = 5,
            baselineTop = 10, learnedTop = 11, baselinePreserved = 5,
            learnedPreserved = 5, improvements = 1, regressions = 0,
            unavailable = 0, cancelled = false, candidateChanged = true,
        )
        assertFalse(small.promotionApproved)
        assertFalse(small.rollbackRequired)
        assertTrue(small.reasons.contains("INSUFFICIENT_HOLDOUT"))
    }

    @Test fun rollbackRequiresCompleteSufficientEvidenceOfRegression() {
        fun evaluation(evaluated: Int = 20, identities: Int = 5, unavailable: Int = 0,
            cancelled: Boolean = false, rollback: Boolean = true) = LearningEvaluation(
            heldOut = evaluated, evaluated = evaluated, unavailable = unavailable,
            missingCandidates = 0, baselineTop = 12, learnedTop = if (rollback) 11 else 13,
            identities = identities, baselinePreserved = identities,
            learnedPreserved = if (rollback) identities - 1 else identities,
            policyMatches = 0, improvements = if (rollback) 0 else 1,
            regressions = if (rollback) 1 else 0, cancelled = cancelled,
            promotion = LearningPromotionDecision(!rollback, rollback, emptyList()),
        )
        assertTrue(LearningEvaluator.rollbackQualified(evaluation()))
        assertTrue(LearningEvaluator.completePolicyEvidence(evaluation(rollback = false)))
        assertFalse(LearningEvaluator.rollbackQualified(evaluation(evaluated = 19)))
        assertFalse(LearningEvaluator.completePolicyEvidence(evaluation(evaluated = 19)))
        assertFalse(LearningEvaluator.rollbackQualified(evaluation(identities = 4)))
        assertFalse(LearningEvaluator.rollbackQualified(evaluation(unavailable = 1)))
        assertFalse(LearningEvaluator.rollbackQualified(evaluation(cancelled = true)))
        assertFalse(LearningEvaluator.rollbackQualified(evaluation(rollback = false)))
    }
}
