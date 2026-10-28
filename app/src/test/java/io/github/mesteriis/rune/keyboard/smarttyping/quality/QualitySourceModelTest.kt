package io.github.mesteriis.rune.keyboard.smarttyping.quality

import org.junit.Assert.*
import org.junit.Test

class QualitySourceModelTest {
    @Test fun sourceAndOutcomePositionsAreTheFixedV3Schema() {
        assertEquals(listOf("COMMON_CONFUSION", "GENERAL_LOCAL", "COMPACT_PUBLIC", "NEIGHBOR_RECOVERY",
            "JOINT_SHORT", "JOINT_LONG", "JOINT_RESCUE", "WORD_CONTEXT", "CONTEXTUAL_RANKER",
            "INFINITIVE_REVISION", "NOUN_CASE_REVISION", "MODEL", "CONTEXTUAL", "CANONICAL_CASE"),
            AutomaticQualitySource.entries.map { it.name })
        assertEquals(listOf("APPLIED", "EXPLICIT_UNDO", "KEPT_ORIGINAL", "WINDOW_EXPIRED"),
            AutomaticQualityOutcome.entries.map { it.name })
        assertEquals(56, QualityModel.SOURCE_COUNTER_COUNT)
        assertFalse(AutomaticQualitySource.entries.any { it.name == "MODEL_REFINEMENT" })
        assertEquals(8, QualityEvent.entries.size)
    }

    @Test fun newRecorderMethodsAcceptOnlyFixedEnumsAndNumericDuration() {
        val methods = QualityRecorder::class.java.declaredMethods.associateBy { it.name }
        assertEquals(listOf(AutomaticQualitySource::class.java, AutomaticQualityOutcome::class.java),
            methods.getValue("recordAutomatic").parameterTypes.toList())
        assertEquals(listOf(java.lang.Long.TYPE), methods.getValue("modelResponseMillis").parameterTypes.toList())
        assertEquals(listOf(AutomaticQualitySource::class.java),
            methods.getValue("recordAutomaticApplication").parameterTypes.toList())
        assertEquals(listOf(AutomaticQualityApplication::class.java),
            methods.getValue("recordAutomaticUndo").parameterTypes.toList())
        assertTrue(AutomaticQualityApplication::class.java.declaredFields.none { it.type == String::class.java })
        assertEquals(0, QualityCollectionPeriod::class.java.declaredFields.size)
        for (name in listOf("recordAutomatic", "modelResponseMillis", "recordAutomaticApplication", "recordAutomaticUndo"))
            assertFalse(methods.getValue(name).parameterTypes.contains(String::class.java))
    }

    @Test fun everySourceOutcomeHasItsOwnCounterWithoutChangingLegacyEvents() {
        val model = QualityModel().apply { configure(true, false, true) }
        var value = 0
        for (source in AutomaticQualitySource.entries) for (outcome in AutomaticQualityOutcome.entries) {
            value++
            repeat(value) { assertTrue(model.recordAutomatic(source, outcome)) }
        }
        val snapshot = model.snapshot()
        assertEquals((1L..56L).toList(), snapshot.automaticSources)
        assertEquals(List(8) { 0L }, snapshot.events)
        assertEquals(List(6) { 0L }, snapshot.candidateResponseBuckets)
        assertEquals(List(6) { 0L }, snapshot.shadow)
        assertEquals(List(5) { 0L }, snapshot.modelResponseBuckets)
        value = 0
        for (source in AutomaticQualitySource.entries) for (outcome in AutomaticQualityOutcome.entries)
            assertEquals((++value).toLong(), snapshot[source, outcome])
    }

    @Test fun sourceAndModelCountersRequireMetricsAndEligibilityIndependentlyOfShadow() {
        for (metrics in listOf(false, true)) for (shadow in listOf(false, true)) for (eligible in listOf(false, true)) {
            val model = QualityModel().apply { configure(metrics, shadow, eligible) }
            assertEquals(metrics && eligible, model.recordAutomatic(AutomaticQualitySource.WORD_CONTEXT,
                AutomaticQualityOutcome.EXPLICIT_UNDO))
            assertEquals(metrics && eligible, model.modelResponseMillis(50))
            assertEquals(if (metrics && eligible) 1L else 0L,
                model.snapshot()[AutomaticQualitySource.WORD_CONTEXT, AutomaticQualityOutcome.EXPLICIT_UNDO])
        }
        val model = QualityModel()
        assertFalse(model.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED))
        assertFalse(model.modelResponseMillis(0))
        assertEquals(QualitySnapshot(), model.snapshot())
    }

    @Test fun modelResponseEdgesAreSeparateFromExistingCandidateLatency() {
        val model = QualityModel().apply { configure(true, false, true) }
        assertFalse(model.modelResponseMillis(-1))
        for (duration in listOf(0L, 49, 50, 99, 100, 249, 250, 499, 500, Long.MAX_VALUE))
            assertTrue(model.modelResponseMillis(duration))
        assertEquals(listOf(2L, 2L, 2L, 2L, 2L), model.snapshot().modelResponseBuckets)
        assertEquals(List(6) { 0L }, model.snapshot().candidateResponseBuckets)
        assertTrue(model.candidateResponseNanos(100_000_000))
        assertEquals(listOf(0L, 0L, 0L, 0L, 0L, 1L), model.snapshot().candidateResponseBuckets)
        assertEquals(listOf(2L, 2L, 2L, 2L, 2L), model.snapshot().modelResponseBuckets)
    }

    @Test fun undoFractionRequiresOneHundredApplicationsAndNeverLabelsAbsenceOfUndoAsCorrect() {
        val source = AutomaticQualitySource.CONTEXTUAL_RANKER
        val model = QualityModel().apply { configure(true, false, true) }
        repeat(99) { model.recordAutomatic(source, AutomaticQualityOutcome.APPLIED) }
        repeat(5) { model.recordAutomatic(source, AutomaticQualityOutcome.EXPLICIT_UNDO) }
        assertNull(model.snapshot().explicitUndoFraction(source))
        model.recordAutomatic(source, AutomaticQualityOutcome.APPLIED)
        assertEquals(0.05, model.snapshot().explicitUndoFraction(source)!!, 0.0)
        model.recordAutomatic(source, AutomaticQualityOutcome.APPLIED)
        assertEquals(5.0 / 101.0, model.snapshot().explicitUndoFraction(source)!!, 0.0)
        assertNull(model.snapshot().explicitUndoFraction(AutomaticQualitySource.MODEL))
        model.reset()
        assertNull(model.snapshot().explicitUndoFraction(source))
        repeat(100) { model.recordAutomatic(source, AutomaticQualityOutcome.APPLIED) }
        assertEquals(0.0, model.snapshot().explicitUndoFraction(source)!!, 0.0)
        repeat(101) { model.recordAutomatic(source, AutomaticQualityOutcome.EXPLICIT_UNDO) }
        assertNull(model.snapshot().explicitUndoFraction(source))
    }

    @Test fun v2MigrationPreservesEveryLegacyFieldAndDoesNotInventSourceOrModelHistory() {
        val values = (1L..20L).toList()
        val old = ("RUNE_QUALITY_2\n" + values.joinToString("\n") + "\n").toByteArray(Charsets.US_ASCII)
        val decoded = QualityCodec.decode(old)
        assertEquals((1L..8L).toList(), decoded.events)
        assertEquals((9L..14L).toList(), decoded.candidateResponseBuckets)
        assertEquals((15L..20L).toList(), decoded.shadow)
        assertEquals(List(56) { 0L }, decoded.automaticSources)
        assertEquals(List(5) { 0L }, decoded.modelResponseBuckets)
        assertEquals(decoded, QualityCodec.decode(QualityCodec.encode(decoded)))
        assertTrue(String(QualityCodec.encode(decoded), Charsets.US_ASCII).startsWith("RUNE_QUALITY_3\n"))
    }

    @Test fun maximumV3SnapshotRoundTripsAsOnlyHeaderAndBoundedDecimalCounters() {
        val value = QualityModel.MAX_COUNT
        val snapshot = QualitySnapshot(List(8) { value }, List(6) { value }, List(6) { value },
            List(56) { value }, List(5) { value })
        val encoded = QualityCodec.encode(snapshot)
        assertTrue(encoded.size <= QualityCodec.MAX_BYTES)
        val lines = encoded.toString(Charsets.US_ASCII).split('\n')
        assertEquals("RUNE_QUALITY_3", lines.first())
        assertEquals(83, lines.size)
        assertTrue(lines.drop(1).dropLast(1).all { it == "1000000000000" })
        assertEquals(snapshot, QualityCodec.decode(encoded))
    }

    @Test fun sourceAndModelCountsSaturateIndependentlyAndResetClearsBoth() {
        val model = QualityModel().apply {
            configure(true, false, true)
            restore(QualitySnapshot(automaticSources = List(56) { QualityModel.MAX_COUNT },
                modelResponseBuckets = List(5) { QualityModel.MAX_COUNT }))
        }
        for (source in AutomaticQualitySource.entries) for (outcome in AutomaticQualityOutcome.entries)
            assertFalse(model.recordAutomatic(source, outcome))
        assertFalse(model.modelResponseMillis(0))
        assertTrue(model.record(QualityEvent.AUTOMATIC_APPLIED))
        assertTrue(model.candidateResponseNanos(0))
        assertEquals(List(56) { QualityModel.MAX_COUNT }, model.snapshot().automaticSources)
        assertEquals(List(5) { QualityModel.MAX_COUNT }, model.snapshot().modelResponseBuckets)
        model.reset()
        assertEquals(QualitySnapshot(), model.snapshot())
    }

    @Test fun applicationTicketsAreSingleUseRecorderBoundAndRevokedByCollectionTransitions() {
        val source = AutomaticQualitySource.JOINT_LONG
        val a = QualityModel().apply { configure(true, false, true) }
        val b = QualityModel().apply { configure(true, false, true) }
        val first = a.recordAutomaticApplication(source)!!
        assertFalse(b.recordAutomaticUndo(first))
        a.configure(true, true, true) // Shadow alone does not change source collection.
        assertTrue(a.recordAutomaticUndo(first))
        assertFalse(a.recordAutomaticUndo(first))
        assertEquals(1L, a.snapshot()[source, AutomaticQualityOutcome.EXPLICIT_UNDO])
        for (cause in listOf("reset", "restore", "disabled", "private")) {
            val application = a.recordAutomaticApplication(source)!!
            when (cause) {
                "reset" -> a.reset()
                "restore" -> a.restore(a.snapshot())
                "disabled" -> { a.configure(false, false, true); a.configure(true, false, true) }
                else -> { a.configure(true, false, false); a.configure(true, false, true) }
            }
            assertFalse(a.recordAutomaticUndo(application))
        }
    }

    @Test fun noApplicationTicketIsIssuedForExcludedOrSaturatedCountsAndTicketsAreNotPersisted() {
        val source = AutomaticQualitySource.MODEL
        val model = QualityModel()
        assertNull(model.recordAutomaticApplication(source))
        model.configure(true, false, true)
        model.restore(QualitySnapshot(automaticSources = List(56) { QualityModel.MAX_COUNT }))
        assertNull(model.recordAutomaticApplication(source))
        model.reset()
        val application = model.recordAutomaticApplication(source)!!
        val restored = QualityModel().apply { configure(true, false, true); restore(QualityCodec.decode(QualityCodec.encode(model.snapshot()))) }
        assertFalse(restored.recordAutomaticUndo(application))
        assertEquals(1L, restored.snapshot()[source, AutomaticQualityOutcome.APPLIED])
        assertEquals(0L, restored.snapshot()[source, AutomaticQualityOutcome.EXPLICIT_UNDO])
    }

    @Test fun malformedV3DimensionsNumbersAndSizeFailClosed() {
        assertThrows(IllegalArgumentException::class.java) { QualitySnapshot(automaticSources = List(55) { 0L }) }
        assertThrows(IllegalArgumentException::class.java) { QualitySnapshot(modelResponseBuckets = List(4) { 0L }) }
        for (bad in listOf(-1L, QualityModel.MAX_COUNT + 1)) {
            assertThrows(IllegalArgumentException::class.java) { QualitySnapshot(automaticSources = List(56) { bad }) }
            assertThrows(IllegalArgumentException::class.java) { QualitySnapshot(modelResponseBuckets = List(5) { bad }) }
        }
        val valid = QualityCodec.encode(QualitySnapshot()).toString(Charsets.US_ASCII)
        for (bad in listOf(valid.dropLast(2), valid + "0\n", valid.replaceFirst("\n0\n", "\n+1\n"),
            valid.replaceFirst("\n0\n", "\n1000000000001\n"), "0".repeat(QualityCodec.MAX_BYTES + 1)))
            assertThrows(IllegalArgumentException::class.java) { QualityCodec.decode(bad.toByteArray()) }
    }
}
