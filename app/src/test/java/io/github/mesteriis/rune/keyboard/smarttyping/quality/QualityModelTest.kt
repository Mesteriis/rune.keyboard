package io.github.mesteriis.rune.keyboard.smarttyping.quality

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class QualityModelTest {
    @Test fun `collection defaults off and privacy exclusion gates both tools`() {
        val model = QualityModel()
        assertFalse(model.record(QualityEvent.AUTOMATIC_APPLIED))
        assertFalse(model.compare(1, "source", "primary", "experimental"))
        model.configure(true, true, false)
        assertFalse(model.record(QualityEvent.CORRECTION_PICKED))
        assertFalse(model.candidateResponseNanos(100))
        assertFalse(model.compare(2, "source", "primary", "experimental"))
        assertEquals(QualitySnapshot(), model.snapshot())
    }

    @Test fun `quality and shadow toggles are independent`() {
        val model = QualityModel()
        model.configure(true, false, true)
        assertTrue(model.record(QualityEvent.AUTOMATIC_APPLIED))
        assertFalse(model.compare(1, "source", "primary", "experimental"))
        model.configure(false, true, true)
        assertFalse(model.record(QualityEvent.AUTOMATIC_APPLIED))
        assertFalse(model.candidateResponseNanos(100))
        assertTrue(model.compare(2, "source", "primary", "experimental"))
        assertEquals(1L, model.snapshot()[QualityEvent.AUTOMATIC_APPLIED])
        assertEquals(1L, model.snapshot()[ShadowResult.DISAGREEMENT])
    }

    @Test fun `all acknowledged event categories are separate and absence of undo labels nothing`() {
        val model = QualityModel().apply { configure(true, true, true) }
        QualityEvent.entries.forEach { assertTrue(model.record(it)) }
        model.compare(1, "source", "primary", "experimental")
        model.invalidatePending()
        assertEquals(List(QualityEvent.entries.size) { 1L }, model.snapshot().events)
        assertEquals(0L, model.snapshot().shadow.drop(2).sum())
    }

    @Test fun `latency uses nanosecond edges and discards negative values`() {
        val model = QualityModel().apply { configure(true, false, true) }
        assertFalse(model.candidateResponseNanos(-1))
        listOf(0L, 4_999_999, 5_000_000, 10_000_000, 25_000_000, 50_000_000, 100_000_000, Long.MAX_VALUE)
            .forEach { assertTrue(model.candidateResponseNanos(it)) }
        assertEquals(listOf(2L, 1L, 1L, 1L, 1L, 2L), model.snapshot().candidateResponseBuckets)
    }

    @Test fun `same revision refresh replaces aggregates and cannot double label`() {
        val model = QualityModel().apply { configure(false, true, true) }
        model.compare(1, "source", "primary", "experimental")
        assertTrue(model.compare(1, "source", "changed", "changed"))
        assertTrue(model.explicitChoice(1, "changed"))
        assertFalse(model.explicitChoice(1, "experimental"))
        assertFalse(model.compare(1, "source", "primary", "experimental"))
        assertEquals(0L, model.snapshot()[ShadowResult.DISAGREEMENT])
        assertEquals(1L, model.snapshot()[ShadowResult.EXPLICIT_BOTH])
        assertEquals(1L, model.snapshot()[ShadowResult.AGREEMENT])
    }

    @Test fun `same aggregate refresh updates pending choices without resurrecting invalidated decisions`() {
        val model = QualityModel().apply { configure(false, true, true) }
        assertTrue(model.compare(1, "source", "old", "experimental"))
        assertFalse(model.compare(1, "source", "new", "experimental"))
        assertTrue(model.explicitChoice(1, "new"))
        assertEquals(1L, model.snapshot()[ShadowResult.EXPLICIT_PRIMARY])
        assertEquals(1L, model.snapshot()[ShadowResult.DISAGREEMENT])
        model.compare(2, "source", "primary", "experimental")
        model.invalidatePending()
        assertFalse(model.compare(2, "source", "new", "new"))
        assertFalse(model.explicitChoice(2, "new"))
    }

    @Test fun `refresh does not subtract a saturated comparison that was never counted`() {
        val model = QualityModel().apply {
            configure(false, true, true)
            restore(QualitySnapshot(shadow = List(ShadowResult.entries.size) {
                if (it == ShadowResult.DISAGREEMENT.ordinal) QualityModel.MAX_COUNT else 0L
            }))
        }
        assertFalse(model.compare(1, "source", "primary", "experimental"))
        assertTrue(model.compare(1, "source", "same", "same"))
        assertEquals(QualityModel.MAX_COUNT, model.snapshot()[ShadowResult.DISAGREEMENT])
        assertEquals(1L, model.snapshot()[ShadowResult.AGREEMENT])
    }

    @Test fun `explicit matches count primary experimental both and neither independently`() {
        val model = QualityModel().apply { configure(false, true, true) }
        model.compare(1, "source", "primary", "experimental")
        model.explicitChoice(1, "primary")
        model.compare(2, "source", "primary", "experimental")
        model.explicitChoice(2, "experimental")
        model.compare(3, "source", "same", "same")
        model.explicitChoice(3, "same")
        model.compare(4, "source", "primary", "experimental")
        model.explicitChoice(4, "source")
        assertEquals(listOf(1L, 3L, 1L, 1L, 1L, 1L), model.snapshot().shadow)
    }

    @Test fun `stable configuration preserves pending while transitions clear it`() {
        val model = QualityModel().apply { configure(true, true, true) }
        model.compare(1, "source", "primary", "experimental")
        model.configure(true, true, true)
        assertTrue(model.explicitChoice(1, "primary"))
        model.compare(2, "source", "primary", "experimental")
        model.configure(true, true, false)
        model.configure(true, true, true)
        assertFalse(model.explicitChoice(2, "primary"))
        model.compare(3, "source", "primary", "experimental")
        model.configure(false, true, true)
        assertFalse(model.explicitChoice(3, "primary"))
    }

    @Test fun `stale or oversized feedback consumes pending without a label`() {
        val model = QualityModel().apply { configure(false, true, true) }
        model.compare(1, "source", "primary", "experimental")
        assertFalse(model.explicitChoice(2, "primary"))
        assertFalse(model.explicitChoice(1, "primary"))
        model.compare(3, "source", "primary", "experimental")
        assertFalse(model.explicitChoice(3, "x".repeat(QualityModel.MAX_TEXT_LENGTH + 1)))
        assertFalse(model.explicitChoice(3, "primary"))
    }

    @Test fun `new malformed comparisons and reset discard prior text`() {
        val model = QualityModel().apply { configure(false, true, true) }
        model.compare(1, "source", "primary", "experimental")
        assertFalse(model.compare(2, "x".repeat(QualityModel.MAX_TEXT_LENGTH + 1), "primary", "experimental"))
        assertFalse(model.explicitChoice(1, "primary"))
        model.compare(3, "source", "primary", "experimental")
        model.reset()
        assertFalse(model.explicitChoice(3, "primary"))
        assertEquals(QualitySnapshot(), model.snapshot())
    }

    @Test fun `codec persists only bounded numeric aggregates and restore has no pending text`() {
        val model = QualityModel().apply { configure(true, true, true) }
        model.compare(12, "secret-source", "secret-primary", "secret-experiment")
        model.record(QualityEvent.AUTOMATIC_APPLIED)
        val encoded = QualityCodec.encode(model.snapshot())
        assertTrue(encoded.size <= QualityCodec.MAX_BYTES)
        assertFalse(encoded.toString(Charsets.UTF_8).contains("secret"))
        val restored = QualityModel().apply { configure(true, true, true); restore(QualityCodec.decode(encoded)) }
        assertEquals(model.snapshot(), restored.snapshot())
        assertFalse(restored.explicitChoice(12, "secret-primary"))
    }

    @Test fun `malformed snapshots fail closed and counts saturate`() {
        val snapshot = QualitySnapshot(events = List(QualityEvent.entries.size) { QualityModel.MAX_COUNT })
        val model = QualityModel().apply { configure(true, false, true); restore(snapshot) }
        assertFalse(model.record(QualityEvent.AUTOMATIC_APPLIED))
        assertEquals(QualityModel.MAX_COUNT, model.snapshot()[QualityEvent.AUTOMATIC_APPLIED])
        val valid = QualityCodec.encode(QualitySnapshot()).toString(Charsets.US_ASCII)
        listOf(valid.replaceFirst("\n0\n", "\n-1\n"), valid + "0\n", valid.replaceFirst("\n0\n", "\n1000000000001\n"), "x".repeat(1025))
            .forEach { malformed -> assertThrows(IllegalArgumentException::class.java) { QualityCodec.decode(malformed.toByteArray()) } }
    }
}
