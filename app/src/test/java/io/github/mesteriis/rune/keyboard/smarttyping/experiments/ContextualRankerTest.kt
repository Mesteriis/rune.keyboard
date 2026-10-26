package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Properties
import kotlin.math.abs
import kotlin.math.tanh
import org.junit.Assert.*
import org.junit.Test

class ContextualRankerTest {
    private fun tree(features: Int = 146, split: Int = 145, left: Float = -1f, right: Float = 2f): ByteArray =
        ByteBuffer.allocate(40).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RET2".toByteArray()).putInt(features).putInt(1).putFloat(1f).putFloat(0f)
            putInt(1).putInt(split).putFloat(0f).putFloat(left).putFloat(right)
        }.array()
    private fun resource(name: String) = javaClass.classLoader!!
        .getResourceAsStream("context-feature-parity/$name")!!.use { it.readBytes() }
    private fun contextual(bytes: ByteArray): ContextualRanker? {
        val hashes = Properties().apply { resource("hashes.properties").inputStream().use(::load) }
        return ContextualRanker.create(bytes,
            WordPairFeatures.open(ByteBuffer.wrap(resource("wiki.bin")), hashes.getProperty("wiki"))!!,
            WordPairFeatures.open(ByteBuffer.wrap(resource("conversation.bin")), hashes.getProperty("conversation"))!!,
            GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("grammar.bin")), hashes.getProperty("grammar"))!!)
    }
    private fun candidate() = GeneratedCandidate("научиться", "научиться", "научиться",
        KeyboardLanguage.RUSSIAN, false, 0, 300, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER)

    @Test fun featureSchemaMustBeExplicitAndVectorsMustBeFiniteAndExactSize() {
        assertEquals(146, ContextualRanker.FEATURES)
        assertNull(ObliviousTreeRanker.decode(tree()))
        assertNull(ObliviousTreeRanker.decode(tree(95, 94), 146))
        assertNull(ObliviousTreeRanker.decode(tree(), 147))
        assertNull(ObliviousTreeRanker.decode(tree(split = 146), 146))
        val weights = ObliviousTreeRanker.decode(tree(), 146)!!
        val values = DoubleArray(146)
        assertEquals(-1.0, weights.score(values), 0.0)
        values[145] = 1.0
        assertEquals(2.0, weights.score(values), 0.0)
        assertTrue(weights.score(DoubleArray(145)).isNaN())
        values[0] = Double.NaN
        assertTrue(weights.score(values).isNaN())
        values[0] = Double.POSITIVE_INFINITY
        assertTrue(weights.score(values).isNaN())
    }

    @Test fun characterScoreIsNotAddedAgainOutsideTheUnifiedTree() {
        val ranker = contextual(tree(split = 107, left = 2f, right = 2f))!!
        val models = ExperimentModels().apply {
            loadContext(File("src/main/assets/smarttyping/experiments/ru-ranking-context.bin").readBytes())
        }
        assertTrue(models.contextReady)
        assertTrue(abs(models.contextScore("тебе надо ", "научиться", KeyboardLanguage.RUSSIAN)) > 1e-6)
        val expected = 0.8 * tanh(0.5)
        assertEquals(expected, ranker.score(models, "тебе надо ", "научищься", candidate()), 1e-12)
        assertEquals(expected, ranker.originalScore(models, "тебе надо ", "научищься"), 1e-12)
        assertTrue(ranker.score(ExperimentModels(), "тебе надо ", "научищься", candidate()).isNaN())
        assertTrue(ranker.score(models, "", "научищься", candidate().copy(language = KeyboardLanguage.ENGLISH)).isNaN())
        assertNull(contextual(tree(95, 94)))
    }

    @Test fun secondaryWeightsRetainTheInstalledScorerAndFailClosedWhenUnavailable() {
        val models = ExperimentModels().apply {
            loadContext(File("src/main/assets/smarttyping/experiments/ru-ranking-context.bin").readBytes())
        }
        models.loadGrammarRevisionRanker(tree())
        assertFalse(models.grammarRevisionReady)
        assertTrue(models.grammarRevisionScore("надо ", "научищься", candidate()).isNaN())
        models.loadContextualRanker(contextual(tree(left = 2f, right = 2f))!!)
        assertFalse(models.grammarRevisionReady)
        val installed = models.contextualScore("надо ", "научищься", candidate())
        models.loadGrammarRevisionRanker(tree(left = 1f, right = 1f))
        assertTrue(models.grammarRevisionReady)
        assertEquals(0.8 * tanh(0.25), models.grammarRevisionScore("надо ", "научищься", candidate()), 1e-12)
        assertEquals(installed, models.contextualScore("надо ", "научищься", candidate()), 0.0)
        val morphology = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon { _, _ ->
            io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyMembership(true, true, 100)
        }
        assertTrue(models.allowsInfinitiveRevision("тебе надо ", "научишься", "научиться", morphology))
        assertFalse(models.allowsInfinitiveRevision("ты ", "научишься", "научиться", morphology))
        models.loadGrammarRevisionRanker(tree(95, 94))
        assertFalse(models.grammarRevisionReady)
        assertTrue(models.grammarRevisionOriginalScore("надо ", "научищься").isNaN())
        assertEquals(installed, models.contextualScore("надо ", "научищься", candidate()), 0.0)
        assertFalse(models.allowsInfinitiveRevision("надо ", "научишься", "научиться", morphology))
        models.loadGrammarRevisionRanker(tree(left = 1f, right = 1f))
        assertTrue(models.grammarRevisionReady)
        models.loadContextualRanker(contextual(tree(left = 2f, right = 2f))!!)
        assertFalse(models.grammarRevisionReady)
    }
}
