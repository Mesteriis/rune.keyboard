package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.*
import org.junit.Test

class ExperimentModelsTest {
    private val assets = File("src/main/assets/smarttyping/experiments")
    private fun loaded() = ExperimentModels().apply {
        loadRanker(File(assets, "ru-ranker.bin").readBytes())
        loadContext(File(assets, "ru-context.bin").readBytes())
    }
    private fun candidate(word: String) = GeneratedCandidate(word, word, word,
        KeyboardLanguage.RUSSIAN, false, 0, 300, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER)

    @Test fun unavailableAndUnsupportedAreNoOp() {
        val unavailable = ExperimentModels()
        assertFalse(unavailable.learnedReady)
        assertFalse(unavailable.contextReady)
        assertEquals(0.0, unavailable.rankScore("мы", "дм", candidate("дом")), 0.0)
        assertTrue(unavailable.nextLetters("мы", "", KeyboardLanguage.RUSSIAN).isEmpty())
        val ready = loaded()
        assertTrue(ready.learnedReady && ready.contextReady)
        assertEquals(0.0, ready.contextScore("we", "home", KeyboardLanguage.ENGLISH), 0.0)
        assertTrue(ready.nextLetters("we", "", KeyboardLanguage.ENGLISH).isEmpty())
    }

    @Test fun rejectsTruncatedExtraNonFiniteAndWrongDimensions() {
        for (name in listOf("ru-ranker.bin", "ru-context.bin")) {
            val bytes = File(assets, name).readBytes()
            val invalids = listOf(bytes.copyOf(bytes.size - 1), bytes + 0,
                bytes.clone().apply { this[0] = 0 }, bytes.clone().apply { this[4] = 0 },
                bytes.clone().apply { ByteBuffer.wrap(this).order(ByteOrder.LITTLE_ENDIAN).putFloat(size - 4, Float.NaN) })
            for (invalid in invalids) {
                val model = ExperimentModels()
                if (name.contains("ranker")) { model.loadRanker(invalid); assertFalse(model.learnedReady) }
                else { model.loadContext(invalid); assertFalse(model.contextReady) }
            }
        }
    }

    @Test fun finiteBoundedAndIndependentResources() {
        val model = loaded()
        val original = model.rankScore("мы", "дма", candidate("дом"))
        assertEquals(original, model.rankScore("мы", "дма", candidate("дом"), Double.NaN, Double.POSITIVE_INFINITY), 0.0)
        assertEquals(original + 0.4, model.rankScore("мы", "дма", candidate("дом"), 999.0, 999.0), 1e-9)
        val letters = model.nextLetters("мы идем", "д", KeyboardLanguage.RUSSIAN)
        assertEquals(33, letters.size)
        assertEquals(1.0, letters.values.sum(), 1e-9)
        assertTrue(letters.values.all { it.isFinite() && it in 0.0..1.0 })
        assertNotEquals(letters, model.nextLetters("мы хотим", "д", KeyboardLanguage.RUSSIAN))
        model.loadRanker(byteArrayOf())
        assertFalse(model.learnedReady)
        assertTrue(model.contextReady)
    }

    @Test fun treeThresholdAndBitOrderMatchNumericExport() {
        val buffer = ByteBuffer.allocate(56).order(ByteOrder.LITTLE_ENDIAN)
        buffer.put("RET1".toByteArray()).putInt(22).putInt(1).putFloat(1f).putFloat(0f)
        buffer.putInt(2).putInt(0).putFloat(0.5f).putInt(1).putFloat(0.25f)
        buffer.putFloat(0f).putFloat(1f).putFloat(2f).putFloat(3f)
        val tree = checkNotNull(ObliviousTreeRanker.decode(buffer.array()))
        val features = DoubleArray(22)
        features[0] = 0.5; features[1] = 0.25
        assertEquals(0.0, tree.score(features), 0.0)
        features[0] = 0.6
        assertEquals(1.0, tree.score(features), 0.0)
        features[1] = 0.3
        assertEquals(3.0, tree.score(features), 0.0)
        features[0] = 0.4
        assertEquals(2.0, tree.score(features), 0.0)
    }

    @Test fun pythonKotlinInferenceParity() {
        val model = loaded()
        val lines = File("../tools/typing_experiments/parity.tsv").readLines()
        assertEquals(4, lines.size)
        for (line in lines) {
            val fields = line.split('\t')
            val context = fields[0]
            val original = fields[1]
            val word = fields[2]
            assertEquals(fields[3].toDouble(), model.rankScore(context, original, candidate(word)), 1e-6)
            assertEquals(fields[4].toDouble(), model.contextScore(context, word, KeyboardLanguage.RUSSIAN), 1e-7)
            val actual = model.nextLetters(context, word, KeyboardLanguage.RUSSIAN)
            val expected = fields[5].split(',').map(String::toDouble)
            for (i in 1 until ExperimentModels.ALPHABET.length) {
                assertEquals(expected[i - 1], actual.getValue(ExperimentModels.ALPHABET[i]), 1e-7)
            }
        }
    }
}
