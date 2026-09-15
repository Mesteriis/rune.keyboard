package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test

class LearningModelTest {
    private val en = KeyboardLanguage.ENGLISH
    private fun enabled(collect: Boolean = true) = LearningModel().apply { configure(collect, true, true) }
    @Test fun defaultOffEligibilityAndIndependentToggles() {
        val model = LearningModel()
        assertFalse(model.record("caat", "cat", en, FeedbackSource.ACCEPTED))
        model.configure(true, true, false)
        assertFalse(model.record("caat", "cat", en, FeedbackSource.ACCEPTED))
        model.configure(true, false, true)
        assertTrue(model.record("caat", "cat", en, FeedbackSource.ACCEPTED))
        assertTrue(model.snapshot().counts().isEmpty())
        model.configure(false, true, true)
        assertTrue(model.record("doog", "dog", en, FeedbackSource.ACCEPTED))
        assertEquals(1, model.snapshot().examples.size)
        model.configure(false, false, true)
        assertFalse(model.record("biird", "bird", en, FeedbackSource.ACCEPTED))
    }
    @Test fun explicitIdentityAndConservativeRetype() {
        val model = enabled()
        assertTrue(model.record("word", "word", en, FeedbackSource.CONFIRMED))
        assertFalse(model.record("word", "ward", en, FeedbackSource.CONFIRMED))
        assertFalse(model.record("caat", "cat", en, FeedbackSource.MANUAL_RETYPE))
        assertTrue(model.record("caat", "cat", en, FeedbackSource.MANUAL_RETYPE) { _, _ -> true })
        assertFalse(model.record("password123", "password", en, FeedbackSource.ACCEPTED))
        assertFalse(model.record("hello world", "hello", en, FeedbackSource.ACCEPTED))
        assertFalse(model.record("a".repeat(49), "a", en, FeedbackSource.ACCEPTED))
    }
    @Test fun fixedSplitAndDuplicateNeverTrainHoldoutEvenWithoutRawCollection() {
        val words = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green", "table", "word", "house")
        val held = words.first { LearningModel.holdout(en, it) }
        val model = enabled(false)
        assertTrue(model.record(held + "z", held, en, FeedbackSource.ACCEPTED))
        assertTrue(model.record(held + "x", held, en, FeedbackSource.ACCEPTED))
        repeat(10) { assertFalse(model.record(held + "z", held, en, FeedbackSource.MANUAL_RETYPE) { _, _ -> true }) }
        assertEquals(2, model.snapshot().evidence.size)
        assertTrue(model.snapshot().evidence.all { it.holdout && !it.trains })
        assertTrue(model.snapshot().counts().isEmpty())
        assertTrue(model.snapshot().examples.isEmpty())
    }
    @Test fun finitePatternsGeneralizeWithMinimumDistinctWordsAndRetractContradictions() {
        val model = enabled()
        val training = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green", "table", "word", "house").filterNot { LearningModel.holdout(en, it) }.take(3)
        training.take(2).forEach { model.record(it + "z", it, en, FeedbackSource.ACCEPTED) }
        assertEquals(0.0, model.preference("plantz", "plant", en), 0.0)
        model.record(training[2] + "z", training[2], en, FeedbackSource.ACCEPTED)
        assertTrue(model.preference("plantz", "plant", en) > 0.0)
        assertEquals(0.0, model.preference("plantz", "plant", KeyboardLanguage.RUSSIAN), 0.0)
        model.record(training[0] + "z", training[0], en, FeedbackSource.REJECTED)
        assertEquals(0.0, model.preference("plantz", "plant", en), 0.0)
        model.configure(true, true, false)
        assertEquals(0.0, model.preference("plantz", "plant", en), 0.0)
    }
    @Test fun classifierAbstainsAndRecognizesFiveCategories() {
        assertEquals(TypoPattern.INSERTION, LearningModel.classify("ct", "cat"))
        assertEquals(TypoPattern.DELETION, LearningModel.classify("cart", "cat"))
        assertEquals(TypoPattern.SUBSTITUTION, LearningModel.classify("cot", "cat"))
        assertEquals(TypoPattern.TRANSPOSITION, LearningModel.classify("cta", "cat"))
        assertEquals(TypoPattern.REPETITION, LearningModel.classify("caat", "cat"))
        assertNull(LearningModel.classify("cat", "cat"))
        assertNull(LearningModel.classify("bored", "apple"))
    }
    @Test fun conflictingExpectedWordsRetractAndRetypeReaderFailureAbstains() {
        val model = enabled()
        val training = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green").filterNot { LearningModel.holdout(en, it) }.take(3)
        training.forEach { model.record(it + "z", it, en, FeedbackSource.ACCEPTED) }
        assertTrue(model.preference("plantz", "plant", en) > 0.0)
        model.record(training[0] + "z", "different", en, FeedbackSource.ACCEPTED)
        assertEquals(0.0, model.preference("plantz", "plant", en), 0.0)
        assertFalse(model.record("worrd", "word", en, FeedbackSource.MANUAL_RETYPE) { _, _ -> error("Unavailable") })
    }
    @Test fun repeatedVariantsOfOneExpectedWordAreOnlyOnePatternEvidence() {
        val expected = listOf("cat", "dog", "bird").first { !LearningModel.holdout(en, it) }
        val model = enabled(false)
        listOf("x", "y", "z").forEach { model.record(expected + it, expected, en, FeedbackSource.ACCEPTED) }
        assertEquals(1, model.snapshot().counts()[en to TypoPattern.DELETION])
        assertEquals(0.0, model.preference("plantz", "plant", en), 0.0)
        assertEquals(model.snapshot(), LearningCodec.decode(LearningCodec.encode(model.snapshot())))
    }
    @Test fun fullLedgerStillRetractsContradictionsWithoutCollectingAdditionalText() {
        val model = enabled()
        repeat(512) { i ->
            val word = "word" + ('a' + i / 26) + ('a' + i % 26)
            model.record(word + "z", word, en, FeedbackSource.ACCEPTED)
        }
        assertTrue(model.record("wordaaz", "different", en, FeedbackSource.ACCEPTED))
        assertEquals(512, model.snapshot().evidence.size)
        assertTrue(model.snapshot().evidence.first().conflicted)
        assertFalse(model.snapshot().evidence.first().trains)
        assertEquals(model.snapshot(), LearningCodec.decode(LearningCodec.encode(model.snapshot())))
    }
    @Test fun saturationDoesNotEvictDedupEvidence() {
        val model = enabled()
        repeat(512) { i ->
            val word = "word" + ('a' + i / 26) + ('a' + i % 26)
            assertTrue(model.record(word, word, en, FeedbackSource.CONFIRMED))
        }
        assertFalse(model.record("extra", "extra", en, FeedbackSource.CONFIRMED))
        assertEquals(512, model.snapshot().evidence.size)
        model.reset(); assertTrue(model.snapshot().evidence.isEmpty())
    }
}
