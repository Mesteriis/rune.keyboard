package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.util.Base64
import java.util.Properties
import org.junit.Assert.*
import org.junit.Test

class RightContextRevisionFeaturesTest {
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream("right-context-model-parity/$name")!!
    private val hashes by lazy { Properties().apply { resource("hashes.properties").use(::load) } }
    private fun modelBytes(): ByteArray = resource("model.bin").use { it.readBytes() }.also { bytes ->
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
        assertEquals(hashes.getProperty("model"), digest)
    }
    private fun model() = ObliviousTreeRanker.decode(modelBytes(), RightContextRevisionFeatures.COUNT)!!
    private val dictionary by lazy { GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
        "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()), FrozenContextualAssets.GRAMMAR_SHA256)!! }
    private val past by lazy {
        val root = "right-context-role-parity/"
        val loader = javaClass.classLoader!!
        val properties = Properties().apply { loader.getResourceAsStream(root + "hashes.properties")!!.use(::load) }
        GrammarFeatureDictionary.open(ByteBuffer.wrap(loader.getResourceAsStream(root + "full-past.gram")!!.use { it.readBytes() }),
            properties.getProperty("fullPast"))!!
    }
    private fun bridge() = RightContextRevisionFeatures(dictionary, past)

    @Test fun installedFeatureProviderAndCompleteRevisionVectorsMatchPython() {
        val assets = File("src/main/assets/smarttyping/experiments")
        fun pairs(name: String, hash: String) = WordPairFeatures.open(ByteBuffer.wrap(File(assets, name).readBytes()), hash)!!
        val baseRanker = ContextualRanker.create(File(assets, "ru-contextual-ranker.bin").readBytes(),
            pairs("ru-wiki.ctx", FrozenContextualAssets.WIKI_SHA256),
            pairs("ru-conversation.ctx", FrozenContextualAssets.CONVERSATION_SHA256), dictionary)!!
        val models = ExperimentModels().apply { loadContext(File(assets, "ru-ranking-context.bin").readBytes()) }
        val bridge = bridge(); val model = model(); var count = 0
        val following = RightContextRanker.create(modelBytes(), baseRanker, dictionary, past)!!
        resource("runtime-vectors.tsv").bufferedReader().useLines { lines -> lines.forEach { line ->
            val f = line.split('\t')
            fun decode(index: Int) = String(Base64.getDecoder().decode(f[index]), Charsets.UTF_8)
            val context = decode(0); val original = decode(2); val word = decode(4)
            val candidate = GeneratedCandidate(word, word, word, KeyboardLanguage.RUSSIAN, f[9] == "1", 0,
                f[7].toInt(), f[6].toInt(), EditFeatures(f[8].toDouble(), 0, 0.0), 1, CasePattern.analyze(word))
            val base = if (f[5] == "original") baseRanker.originalFeatures(models, context, original)!!
                else baseRanker.candidateFeatures(models, context, original, candidate)!!
            assertArrayEquals("Installed base $count", f[10].split(',').map(String::toDouble).toDoubleArray(), base, 1e-12)
            val vector = bridge.build(base, context, decode(1), decode(3), word)!!
            assertArrayEquals("Installed revision $count", f[11].split(',').map(String::toDouble).toDoubleArray(), vector, 1e-12)
            assertEquals("Installed revision score $count", f[12].toDouble(), model.score(vector), 0.0)
            val bounded = if (f[5] == "original") following.originalScore(models, context, original, decode(1), decode(3))
                else following.score(models, context, original, decode(1), decode(3), candidate)
            assertEquals("Bounded revision score $count", f[13].toDouble(), bounded, 1e-12)
            count++
        } }
        assertEquals(hashes.getProperty("runtimeCases").toInt(), count)
        val c = GeneratedCandidate("готовы", "готовы", "готовы", KeyboardLanguage.RUSSIAN, false, 0,
            300, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER)
        assertTrue(following.score(ExperimentModels(), "", "готв", " будут ", "готв", c).isNaN())
        assertTrue(following.score(models, "", "готв", " будут ", "готв", c.copy(language = KeyboardLanguage.ENGLISH)).isNaN())
        assertTrue(following.originalScore(models, "", "", " будут ", "готв").isNaN())
        assertNull(RightContextRanker.create(File(assets, "ru-contextual-ranker.bin").readBytes(), baseRanker, dictionary, past))
    }

    @Test fun composedVectorsAndRealModelScoresMatchPythonExactly() {
        val bridge = bridge(); val model = model(); var count = 0
        resource("vectors.tsv").bufferedReader().useLines { lines -> lines.forEach { line ->
            val f = line.split('\t')
            fun decode(index: Int) = String(Base64.getDecoder().decode(f[index]), Charsets.UTF_8)
            val base = f[4].split(',').map(String::toDouble).toDoubleArray()
            val vector = bridge.build(base, decode(0), decode(1), decode(2), decode(3))!!
            assertArrayEquals("Bridge vector $count", f[5].split(',').map(String::toDouble).toDoubleArray(), vector, 0.0)
            assertEquals("Bridge score $count", f[6].toDouble(), model.score(vector), 0.0)
            count++
        } }
        assertEquals(hashes.getProperty("cases").toInt(), count)
        assertEquals(178, RightContextRevisionFeatures.COUNT)
        assertEquals(ObliviousTreeRanker.RIGHT_CONTEXT_FEATURES, RightContextRevisionFeatures.COUNT)
    }

    @Test fun everyActualSplitBoundaryUsesFloat32AndStrictGreaterThan() {
        val model = model(); var count = 0
        resource("probes.tsv").bufferedReader().useLines { lines -> lines.forEach { line ->
            val f = line.split('\t'); val vector = DoubleArray(RightContextRevisionFeatures.COUNT)
            vector[f[0].toInt()] = f[1].toDouble()
            assertEquals("Boundary probe $count", f[2].toDouble(), model.score(vector), 0.0)
            count++
        } }
        assertEquals(hashes.getProperty("probes").toInt(), count)
    }

    @Test fun newLayoutRequiresAnExplicitMatchingRequestAndIsNotADefaultModel() {
        val bytes = modelBytes()
        assertNull(ObliviousTreeRanker.decode(bytes))
        for (count in listOf(146, 147, 163, 177, 179, 1024)) assertNull(ObliviousTreeRanker.decode(bytes, count))
        assertNotNull(ObliviousTreeRanker.decode(bytes, 178))
        assertNull(ObliviousTreeRanker.decode(bytes.clone().apply {
            ByteBuffer.wrap(this).order(ByteOrder.LITTLE_ENDIAN).putInt(4, 177)
        }, 178))
    }

    @Test fun malformedNewLayoutWeightsKeepAllExistingDecoderBounds() {
        val bytes = modelBytes(); val depth = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).getInt(20)
        val mutations = listOf<Pair<Int, Int>>(8 to 129, 20 to 7, 24 to 178, 24 to -1,
            12 to Float.NaN.toRawBits(), 28 to Float.POSITIVE_INFINITY.toRawBits(),
            (24 + depth * 8) to 33f.toRawBits())
        for ((offset, value) in mutations) assertNull(ObliviousTreeRanker.decode(bytes.clone().apply {
            ByteBuffer.wrap(this).order(ByteOrder.LITTLE_ENDIAN).putInt(offset, value)
        }, 178))
        assertNull(ObliviousTreeRanker.decode(bytes.copyOf(bytes.size - 1), 178))
        assertNull(ObliviousTreeRanker.decode(bytes + byteArrayOf(0), 178))
        assertNull(ObliviousTreeRanker.decode(ByteArray(65_537), 178))
    }

    @Test fun invalidWordsFeatureCountsAndNonfiniteVectorsNeverBecomeScores() {
        val bridge = bridge(); val base = DoubleArray(RightContextRevisionFeatures.BASE)
        for (count in listOf(0, 145, 178)) assertNull(bridge.build(DoubleArray(count), "", " будут ", "готов", "готовы"))
        for (value in listOf(Double.NaN, Double.POSITIVE_INFINITY)) {
            assertNull(bridge.build(base.clone().apply { this[0] = value }, "", " будут ", "готов", "готовы"))
            assertTrue(model().score(DoubleArray(178).apply { this[0] = value }).isNaN())
        }
        for (word in listOf("", "я", "готов_имя", "готов-имя", "ready", "а".repeat(33), "\uDC00")) {
            assertNull(bridge.build(base, "", " будут ", word, "готовы"))
            assertNull(bridge.build(base, "", " будут ", "готов", word))
        }
        assertTrue(model().score(DoubleArray(177)).isNaN())
    }

    @Test fun baseOwnershipAndFrozenV1ModelSemanticsRemainSeparateFromSourceV2() {
        val base = DoubleArray(RightContextRevisionFeatures.BASE) { it / 128.0 }; val before = base.clone()
        val vector = bridge().build(base, "", " и ", "ГОТОВА", "готова")!!
        assertArrayEquals(before, base, 0.0)
        assertEquals(1.0, vector[RightContextRevisionFeatures.APPLIED], 0.0)
        assertEquals(1.0, vector[RightContextRevisionFeatures.BASE + 9], 0.0)
        assertEquals(0.0, ReliableRightContextGrammarFeatures(dictionary).extract(" и ", "готова")[9], 0.0)
        vector[0] = 99.0
        assertArrayEquals(before, base, 0.0)
    }
}
