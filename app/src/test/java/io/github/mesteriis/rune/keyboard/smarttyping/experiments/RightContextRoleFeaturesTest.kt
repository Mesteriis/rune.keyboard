package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.io.File
import java.nio.ByteBuffer
import java.util.Base64
import java.util.Properties
import org.junit.Assert.*
import org.junit.Test

class RightContextRoleFeaturesTest {
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream("right-context-role-parity/$name")!!
    private val hashes by lazy { Properties().apply { resource("hashes.properties").use(::load) } }
    private fun dictionary(name: String, hashKey: String) = GrammarFeatureDictionary.open(
        ByteBuffer.wrap(resource(name).use { it.readBytes() }), hashes.getProperty(hashKey))!!

    private fun assertParity(model: RightContextRoleFeatures) {
        var cases = 0
        resource("vectors.tsv").bufferedReader().useLines { lines -> lines.forEach { line ->
            val fields = line.split('\t')
            fun decode(index: Int) = String(Base64.getDecoder().decode(fields[index]), Charsets.UTF_8)
            val expected = fields[3].split(',').map(String::toDouble).toDoubleArray()
            val actual = model.extract(decode(0), decode(1), decode(2))
            assertEquals(RightContextRoleFeatures.COUNT, actual.size)
            assertArrayEquals("Role parity $cases", expected, actual, 0.0)
            val words = if (fields[4] == "-") emptyList() else decode(4).split(' ')
            assertEquals("Clause boundary $cases", words, RightContextRoleFeatures.precedingClauseWords(decode(0)))
            cases++
        } }
        assertEquals(5472, cases)
    }

    @Test fun everyPythonRoleFeatureMatchesWithTheBoundMiniDictionaries() {
        assertParity(RightContextRoleFeatures(dictionary("grammar.bin", "grammar"), dictionary("past.bin", "past")))
    }

    @Test fun everyPythonRoleFeatureMatchesWithFullGrammarAndPastAssets() {
        val grammar = GrammarFeatureDictionary.open(ByteBuffer.wrap(File(
            "src/main/assets/smarttyping/experiments/ru-context.gram").readBytes()), FrozenContextualAssets.GRAMMAR_SHA256)!!
        assertParity(RightContextRoleFeatures(grammar, dictionary("full-past.gram", "fullPast")))
    }

    @Test fun imperativeWithoutPersonIsNotMistakenForPastAndPluralPastStopsOlderGender() {
        val grammar = dictionary("grammar.bin", "grammar")
        val past = dictionary("full-past.gram", "fullPast")
        assertTrue(grammar.analyses("иди").analyses.any { it.pos == "VERB" && it.person == null })
        assertTrue(past.analyses("иди").analyses.isEmpty())
        assertTrue(past.analyses("были").analyses.any { it.number == "plur" })
        val model = RightContextRoleFeatures(grammar, past)
        assertEquals(1.0, model.extract("она пришла, иди теперь ", " будешь ", "готова")[12], 0.0)
        assertEquals(0.0, model.extract("она пришла, были теперь ", " будешь ", "готова")[11], 0.0)
    }

    @Test fun wrongSupplementIdentityIsRejectedInsteadOfInventingTense() {
        assertNull(GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("full-past.gram").use { it.readBytes() }), "0".repeat(64)))
    }
}
