package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

class PackagedContextPayloadTest {
    private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
    private fun hash(bytes: ByteArray) = digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
    private fun buffer(bytes: ByteArray) = ByteBuffer.wrap(bytes).asReadOnlyBuffer()
    private fun fixture(magic: String, records: List<Pair<String, ByteArray>>): ByteArray {
        val body = ByteArrayOutputStream()
        for ((key, payload) in records) {
            val word = key.toByteArray(Charsets.UTF_8)
            body.write(0); body.write(word.size)
            body.write(payload.size and 255); body.write(payload.size ushr 8)
            body.write(word); body.write(payload)
        }
        val header = ByteBuffer.allocate(32).order(ByteOrder.LITTLE_ENDIAN)
        header.put(magic.toByteArray()).putInt(32).putInt(records.size).putInt(1).putInt(32)
            .putInt(0).putInt(body.size())
        val contents = header.array() + body.toByteArray()
        return contents + digest(contents)
    }
    private fun grammar(code: Int = 1) = byteArrayOf(1, 1, code.toByte(), (code ushr 8).toByte())
    private fun pairs(vararg counts: Int) = ByteBuffer.allocate(counts.size * 4).order(ByteOrder.LITTLE_ENDIAN)
        .apply { counts.forEach { putInt(it) } }.array()

    @Test fun everyPartOfSpeechAndNumberBitPatternIsCheckedBeforeArrayIndexing() {
        for (pos in 0..31) for (number in 0..3) {
            val code = pos or (number shl 8) or (7 shl 5) or (3 shl 10) or (3 shl 12) or (3 shl 14)
            val bytes = fixture("RUGRM001", listOf("а" to grammar(), "б" to grammar(code)))
            val index = GrammarFeatureDictionary.openPackaged(buffer(bytes), bytes.size.toLong())!!
            assertEquals("NOUN", index.analyses("а").analyses.single().pos)
            val result = index.analyses("б")
            val valid = pos < 18 && number < 3
            if (valid) {
                assertEquals(1, result.ambiguity)
                assertEquals(1, result.analyses.size)
                val analysis = result.analyses.single()
                assertEquals("voct", analysis.case)
                assertEquals("neut", analysis.gender)
                assertEquals("3per", analysis.person)
                assertTrue(analysis.modal); assertTrue(analysis.accusativeVerb)
                assertNotNull(GrammarFeatureDictionary.validate(buffer(bytes), hash(bytes)))
            } else {
                assertEquals(GrammarWord(0, emptyList()), result)
                assertNull(GrammarFeatureDictionary.validate(buffer(bytes), hash(bytes)))
            }
        }
    }

    @Test fun malformedGrammarLengthsCountsAndAmbiguityReturnNoAnalysis() {
        val invalid = listOf(byteArrayOf(1), byteArrayOf(1, 0), byteArrayOf(1, -1, 1, 0),
            byteArrayOf(0, 1, 1, 0), byteArrayOf(9, 1, 1, 0), byteArrayOf(1, 2, 1, 0),
            byteArrayOf(1, 1, 1, 0, 0))
        for (payload in invalid) {
            val bytes = fixture("RUGRM001", listOf("а" to grammar(), "б" to payload))
            val index = GrammarFeatureDictionary.openPackaged(buffer(bytes), bytes.size.toLong())!!
            assertEquals(1, index.analyses("а").analyses.size)
            assertEquals(GrammarWord(0, emptyList()), index.analyses("б"))
            assertNull(GrammarFeatureDictionary.validate(buffer(bytes), hash(bytes)))
        }
    }

    @Test fun malformedPairCountsCannotBecomeNumericFeatures() {
        val invalid = listOf(pairs(0, 1, 2, 2), pairs(-1, 1, 2, 2), pairs(2, 0, 2, 2),
            pairs(2, 3, 2, 2), pairs(2, 1, 1, 2), pairs(2, 1, 2, 1), pairs(2, 1, 2),
            pairs(2, 1, 2, 2, 0))
        for (payload in invalid) {
            val bytes = fixture("RUCNTX01", listOf("я\u0000а" to pairs(2, 1, 2, 2), "я\u0000б" to payload))
            val index = WordPairFeatures.openPackaged(buffer(bytes), bytes.size.toLong())!!
            assertEquals(1.0, index.extract("я ", "а", "а")[5], 0.0)
            assertArrayEquals(DoubleArray(6), index.extract("я ", "б", "б"), 0.0)
            assertNull(WordPairFeatures.validate(buffer(bytes), hash(bytes)))
        }
    }
}
