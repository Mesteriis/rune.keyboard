package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.io.File
import java.nio.ByteBuffer
import java.util.Base64
import java.util.Properties
import org.junit.Assert.*
import org.junit.Test

class ReliableRightContextGrammarFeaturesTest {
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream("reliable-subject-parity/$name")!!
    private val dictionary by lazy {
        val hashes = Properties().apply { resource("hashes.properties").use(::load) }
        GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("grammar.bin").use { it.readBytes() }), hashes.getProperty("grammar"))!!
    }

    private fun assertParity(model: ReliableRightContextGrammarFeatures) {
        var cases = 0
        resource("vectors.tsv").bufferedReader().useLines { lines -> lines.forEach { line ->
            val fields = line.split('\t')
            fun decode(position: Int) = String(Base64.getDecoder().decode(fields[position]), Charsets.UTF_8)
            val expected = fields[2].split(',').map(String::toDouble).toDoubleArray()
            assertArrayEquals("Reliable subject $cases", expected, model.extract(decode(0), decode(1)), 0.0)
            cases++
        } }
        assertEquals(5510, cases)
    }

    @Test fun everyPythonSourceFieldMatchesWithTheMiniDictionary() {
        assertParity(ReliableRightContextGrammarFeatures(dictionary))
    }

    @Test fun everyPythonSourceFieldMatchesWithTheFullProductionGrammar() {
        val full = GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
            "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()), FrozenContextualAssets.GRAMMAR_SHA256)!!
        assertParity(ReliableRightContextGrammarFeatures(full))
    }

    @Test fun functionWordNominalHomographsDoNotAlterRawDictionaryOrV1ModelFeatures() {
        val old = RightContextGrammarFeatures(dictionary)
        val reliable = ReliableRightContextGrammarFeatures(dictionary)
        for (word in listOf("и", "в", "по")) {
            val raw = dictionary.analyses(word)
            val frozen = old.extract(" $word ", "готовы")
            assertEquals(1.0, frozen[9], 0.0)
            assertEquals(0.0, reliable.extract(" $word ", "готовы")[9], 0.0)
            assertEquals(raw, dictionary.analyses(word))
            assertArrayEquals(frozen, old.extract(" $word ", "готовы"), 0.0)
        }
    }

    @Test fun realCopulaPronounsAndCaseAmbiguityRemainEvidence() {
        val old = RightContextGrammarFeatures(dictionary)
        val reliable = ReliableRightContextGrammarFeatures(dictionary)
        for (suffix in listOf(" модели ", " она ", " они ", " будут ", " будут она "))
            assertArrayEquals(old.extract(suffix, "готовы"), reliable.extract(suffix, "готовы"), 0.0)
        val afterFunction = reliable.extract(" будут и ", "готовы")
        assertEquals(1.0, afterFunction[4], 0.0)
        assertEquals(1.0, afterFunction[5], 0.0)
        assertEquals(0.0, afterFunction[9], 0.0)
        assertTrue(reliable.extract(" и", "готовы").sliceArray(4..13).all { it == 0.0 })
    }
}
