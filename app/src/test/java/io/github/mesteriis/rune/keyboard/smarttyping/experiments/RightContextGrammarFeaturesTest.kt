package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.io.File
import java.nio.ByteBuffer
import java.util.Base64
import java.util.Properties
import org.junit.Assert.*
import org.junit.Test

class RightContextGrammarFeaturesTest {
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream("right-context-feature-parity/$name")!!
    private val dictionary by lazy {
        val hashes = Properties().apply { resource("hashes.properties").use(::load) }
        GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("grammar.bin").use { it.readBytes() }), hashes.getProperty("grammar"))!!
    }

    @Test fun frozenPythonVectorsMatchEveryNumericFeature() {
        val model = RightContextGrammarFeatures(dictionary)
        var cases = 0
        resource("vectors.tsv").bufferedReader().useLines { lines -> lines.forEach { line ->
            val fields = line.split('\t')
            fun decode(index: Int) = String(Base64.getDecoder().decode(fields[index]), Charsets.UTF_8)
            val expected = fields[2].split(',').map(String::toDouble).toDoubleArray()
            val actual = model.extract(decode(0), decode(1))
            assertEquals(RightContextGrammarFeatures.COUNT, actual.size)
            assertArrayEquals("Parity case $cases", expected, actual, 0.0)
            assertTrue(actual.all { it in 0.0..1.0 })
            cases++
        } }
        assertEquals(1870, cases)
    }

    @Test fun frozenVectorsAlsoMatchTheCurrentProductionGrammarAsset() {
        val installed = GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
            "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()), FrozenContextualAssets.GRAMMAR_SHA256)!!
        val model = RightContextGrammarFeatures(installed)
        resource("vectors.tsv").bufferedReader().useLines { lines -> lines.forEachIndexed { index, line ->
            val fields = line.split('\t')
            fun decode(position: Int) = String(Base64.getDecoder().decode(fields[position]), Charsets.UTF_8)
            assertArrayEquals("Production dictionary parity $index", fields[2].split(',').map(String::toDouble).toDoubleArray(),
                model.extract(decode(0), decode(1)), 0.0)
        } }
    }

    @Test fun unfinishedTokensAndIdentifiersCannotSupplyRightContext() {
        for (suffix in listOf(" будут", " буд", " он", " она", "будут ", " будут_имя ",
            " будут-то ", " будут1 ", " будутabc ", " , будут ", " \nбудут "))
            assertTrue(RightContextGrammarFeatures.completedFollowingWords(suffix).isEmpty())
        assertEquals(listOf("будут"), RightContextGrammarFeatures.completedFollowingWords(" будут он"))
        val queries = mutableListOf<String>()
        val model = RightContextGrammarFeatures { word -> queries += word; dictionary.analyses(word).analyses }
        model.extract(" он", "виновны")
        assertEquals(listOf("виновны"), queries)
    }

    @Test fun punctuationCompletesAWordButPreventsCrossingIntoAnotherClause() {
        for (suffix in listOf(" будут, она ", " будут. она ", " будут\nона ", " будут! она "))
            assertEquals(listOf("будут"), RightContextGrammarFeatures.completedFollowingWords(suffix))
        assertEquals(listOf("будут", "они"), RightContextGrammarFeatures.completedFollowingWords(" БУДУТ\tОНИ "))
        assertEquals(listOf("ёлки"), RightContextGrammarFeatures.completedFollowingWords(" е\u0308лки "))
        assertEquals(8, RightContextGrammarFeatures.completedFollowingWords(" слово".repeat(100) + " ").size)
        assertTrue(RightContextGrammarFeatures.completedFollowingWords(" ".repeat(123) + "будут ").isEmpty())
    }

    @Test fun alternativeGrammaticalReadingsRemainEvidenceRatherThanFalseConflict() {
        fun tag(number: String) = GrammarAnalysis("ADJS", null, number, null, null, false, false)
        val model = RightContextGrammarFeatures { word ->
            if (word == "готов") listOf(tag("sing"), tag("plur")) else dictionary.analyses(word).analyses
        }
        val values = model.extract(" будут ", "готов")
        assertEquals(1.0, values[5], 0.0)
        assertEquals(0.0, values[6], 0.0)
        assertEquals(1.0, values[15], 0.0)
    }

    @Test fun candidateNormalizationNeverHidesATrailingIdentifierSuffix() {
        val queries = mutableListOf<String>()
        val model = RightContextGrammarFeatures { word ->
            queries += word
            listOf(GrammarAnalysis("ADJS", null, "sing", "masc", null, false, false))
        }
        val candidate = "ё".repeat(31) + "е\u0308"
        assertEquals(1.0, model.extract(" ", candidate)[0], 0.0)
        assertEquals(listOf("ё".repeat(32)), queries)
        queries.clear()
        assertEquals(0.0, model.extract(" ", candidate + "x")[0], 0.0)
        assertEquals(0.0, model.extract(" ", "а".repeat(1000))[0], 0.0)
        assertTrue(queries.isEmpty())
    }

    @Test fun installedDictionarySupportsTheDisclosedNumberContrastWithoutGenderGuessing() {
        val installed = GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
            "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()), FrozenContextualAssets.GRAMMAR_SHA256)!!
        val model = RightContextGrammarFeatures(installed)
        val singular = model.extract(" будут ", "виновен")
        val plural = model.extract(" будут ", "виновны")
        assertEquals(1.0, singular[6], 0.0)
        assertEquals(1.0, plural[5], 0.0)
        for (vector in listOf(singular, plural)) {
            assertEquals(0.0, vector[7], 0.0)
            assertEquals(0.0, vector[8], 0.0)
        }
    }
}
