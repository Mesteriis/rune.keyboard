package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream

class LearningCodecTest {
    private fun snapshot(): LearningSnapshot = LearningModel().apply {
        configure(true, true, true)
        record("caat", "cat", KeyboardLanguage.ENGLISH, FeedbackSource.ACCEPTED)
        record("word", "word", KeyboardLanguage.ENGLISH, FeedbackSource.CONFIRMED)
    }.snapshot()
    private fun fails(block: () -> Unit) { try { block(); fail("Expected invalid input") } catch (_: Exception) { } }
    @Test fun roundTripAndStrictMalformedBounds() {
        val snapshot = snapshot(); val bytes = LearningCodec.encode(snapshot)
        assertEquals(snapshot, LearningCodec.decode(bytes))
        fails { LearningCodec.decode(bytes + byteArrayOf(0)) }
        fails { LearningCodec.decode(bytes.copyOf(bytes.size - 1)) }
        fails { LearningCodec.decode(byteArrayOf(1, 2, 3)) }
        fails { LearningCodec.readBounded(ByteArrayInputStream(ByteArray(LearningCodec.MAX_BYTES + 1))) }
        fails { LearningCodec.encode(LearningSnapshot(List(513) { snapshot.evidence.first() })) }
        fails { LearningCodec.encode(LearningSnapshot(listOf(snapshot.evidence.first(), snapshot.evidence.first()))) }
    }
    @Test fun allMaximumShapeSupplementaryRowsFitTheFixedCodecBudget() {
        val model = LearningModel().apply { configure(true, true, true) }
        LearningStoreTest.maximumWords().forEach {
            assertEquals(48, it.codePointCount(0, it.length))
            assertTrue(model.record(it, it, KeyboardLanguage.ENGLISH, FeedbackSource.CONFIRMED))
        }
        val snapshot = model.snapshot()
        val bytes = LearningCodec.encode(snapshot)
        assertEquals(372744, bytes.size)
        assertTrue(bytes.size <= LearningCodec.MAX_BYTES)
        assertEquals(snapshot, LearningCodec.decode(bytes))
    }
    @Test fun refusesRawDigestMismatchAndHeldoutTraining() {
        val row = snapshot().evidence.first()
        fails { LearningCodec.encode(LearningSnapshot(listOf(row.copy(original = "secret")))) }
        fails { LearningCodec.encode(LearningSnapshot(listOf(row.copy(holdout = true, trains = true)))) }
        fails { LearningCodec.encode(LearningSnapshot(listOf(row.copy(source = FeedbackSource.REJECTED, trains = true)))) }
    }
}
