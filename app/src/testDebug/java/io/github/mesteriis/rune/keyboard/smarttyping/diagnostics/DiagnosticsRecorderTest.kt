package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.io.OutputStream
import java.io.ByteArrayOutputStream
import org.junit.Assert.*
import org.junit.Test

class DiagnosticsRecorderTest {
    @Test fun malformedValuesFailClosedIndependently() {
        assertEquals(DiagnosticsPreferences(), DiagnosticsPreferences.decode(emptyMap<String, Any>()))
        assertEquals(DiagnosticsPreferences(true, false), DiagnosticsPreferences.decode(mapOf(
            DiagnosticsPreferences.METADATA to true, DiagnosticsPreferences.TEXT to true,
            DiagnosticsPreferences.CONSENT to "1")))
        assertEquals(DiagnosticsPreferences(false, true), DiagnosticsPreferences.decode(mapOf(
            DiagnosticsPreferences.METADATA to "true", DiagnosticsPreferences.TEXT to true,
            DiagnosticsPreferences.CONSENT to 1)))
        for (version in listOf(null, 0, 2, 1L, true)) {
            assertFalse(DiagnosticsPreferences.decode(mapOf(DiagnosticsPreferences.TEXT to true,
                DiagnosticsPreferences.CONSENT to version)).text)
        }
    }

    @Test fun consentRequiresBothStepsAndRejectsCancellationReplayAndStaleGeneration() {
        var generation = 1L
        val consent = DiagnosticsConsent { generation }
        val first = consent.begin()
        assertNull(consent.storage(first))
        assertTrue(consent.scope(first))
        consent.cancel()
        assertNull(consent.storage(first))
        val stale = consent.begin()
        assertTrue(consent.scope(stale))
        generation++
        assertNull(consent.storage(stale))
        val valid = consent.begin()
        assertTrue(consent.scope(valid))
        assertNotNull(consent.storage(valid))
        assertNull(consent.storage(valid))
    }

    @Test fun textNeedsConsentAndFreshEligibleSessionAndWorksWithoutMetadata() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier)
            recorder.startSession(1, true, true)
            var captured = 0
            fun record(id: Long) = recorder.record(event(id)) { captured++; DiagnosticText(input = "public") }
            record(1)
            assertEquals(0, captured)
            enable(recorder)
            record(1)
            recorder.startSession(2, true, false); record(2)
            recorder.startSession(3, false, true); record(3)
            assertEquals(0, captured)
            recorder.startSession(4, true, true); record(4)
            await(recorder::barrier)
            assertEquals(1, captured)
            assertTrue(backend.records.any { it.first == DiagnosticStream.TEXT && "public" in it.second.decodeToString() })
            assertFalse(backend.records.any { it.first == DiagnosticStream.METADATA })
            recorder.invalidate(); record(4)
            assertEquals(1, captured)
        }
    }

    @Test fun metadataNeverInvokesPayloadAndTextDisableClosesAdmissionImmediately() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier)
            await { recorder.setMetadata(true, it) }
            recorder.startSession(1, true, true)
            recorder.record(event(1)) { error("Payload must stay lazy") }
            await(recorder::barrier)
            assertTrue(backend.records.isNotEmpty())
            assertTrue(backend.records.all { it.first == DiagnosticStream.METADATA })
            enable(recorder)
            recorder.startSession(2, true, true)
            await(recorder::disableText)
            recorder.record(event(2)) { error("Disabled payload copied") }
        }
    }

    @Test fun fullEventQueueCannotStarveStopAndStopAcknowledgesAfterInflightIo() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier)
            enable(recorder)
            recorder.startSession(1, true, true)
            backend.block = true
            recorder.record(event(1)) { DiagnosticText(input = "first") }
            assertTrue(backend.entered.await(2, TimeUnit.SECONDS))
            repeat(600) { recorder.record(event(1)) { DiagnosticText(context = "q".repeat(2_048)) } }
            assertTrue("Byte capacity must bind before event count", recorder.queuedEvents in 1 until 256)
            assertTrue(recorder.queuedBytes <= 512 * 1024)
            val stopped = CountDownLatch(1)
            recorder.disableText { assertTrue(it); stopped.countDown() }
            assertFalse(stopped.await(50, TimeUnit.MILLISECONDS))
            assertEquals(0, recorder.queuedEvents)
            recorder.record(event(1)) { error("Stop must close admission before acknowledgement") }
            backend.release.countDown()
            assertTrue(stopped.await(2, TimeUnit.SECONDS))
            assertEquals(1, backend.records.size)
        }
    }

    @Test fun deleteInvalidatesQueuedRecordsAndAcknowledgesOnlyAfterIo() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier); enable(recorder)
            recorder.startSession(1, true, true)
            backend.block = true
            recorder.record(event(1)) { DiagnosticText(input = "inflight") }
            assertTrue(backend.entered.await(2, TimeUnit.SECONDS))
            recorder.record(event(1)) { DiagnosticText(input = "queued") }
            val deleted = CountDownLatch(1)
            recorder.delete { assertTrue(it); deleted.countDown() }
            assertFalse(deleted.await(50, TimeUnit.MILLISECONDS))
            backend.release.countDown()
            assertTrue(deleted.await(2, TimeUnit.SECONDS))
            assertEquals(DiagnosticsPreferences(), recorder.preferences)
            assertTrue(backend.records.isEmpty())
        }
    }

    @Test fun observerAndStorageFailuresAreContained() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier); enable(recorder)
            recorder.startSession(1, true, true)
            recorder.record(event(1)) { throw IllegalStateException("private exception") }
            backend.failAppend = true
            recorder.record(event(1)) { DiagnosticText(input = "public") }
            await(recorder::barrier)
            assertTrue(backend.records.isEmpty())
            backend.failAppend = false
            recorder.record(event(1)) { DiagnosticText(input = "recovered") }
            await(recorder::barrier)
            assertTrue(backend.records.any { "recovered" in it.second.decodeToString() })
        }
    }

    @Test fun ineligibleTransitionDropsQueuedPermittedPayloadBeforeWriterAdmission() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier); enable(recorder); recorder.startSession(1, true, true)
            backend.block = true
            recorder.record(event(1)) { DiagnosticText(input = "inflight") }
            assertTrue(backend.entered.await(2, TimeUnit.SECONDS))
            recorder.record(event(1)) { DiagnosticText(input = "queued-before-sensitive") }
            recorder.invalidate()
            recorder.startSession(2, false, true)
            recorder.record(event(2)) { error("Sensitive payload copied") }
            backend.release.countDown()
            await(recorder::barrier)
            assertEquals(1, backend.records.size)
            assertFalse(backend.records.any { "queued-before-sensitive" in it.second.decodeToString() })
        }
    }

    @Test fun blockedDocumentProviderCannotDelayManagedStopOrDelete() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier); enable(recorder); recorder.startSession(1, true, true)
            recorder.record(event(1)) { DiagnosticText(input = "public-export") }
            await(recorder::barrier)
            val entered = CountDownLatch(1)
            val release = CountDownLatch(1)
            val exported = CountDownLatch(1)
            val ticket = recorder.newExport()
            recorder.export(ticket, DiagnosticStream.TEXT, { object : OutputStream() {
                override fun write(value: Int) = Unit
                override fun write(bytes: ByteArray, offset: Int, count: Int) {
                    entered.countDown(); check(release.await(4, TimeUnit.SECONDS))
                }
            } }) { exported.countDown() }
            try {
                assertTrue(entered.await(2, TimeUnit.SECONDS))
                val stopped = CountDownLatch(1)
                recorder.disableText { if (it) stopped.countDown() }
                assertTrue("Provider blocked managed stop", stopped.await(300, TimeUnit.MILLISECONDS))
                val deleted = CountDownLatch(1)
                recorder.delete { if (it) deleted.countDown() }
                assertTrue("Provider blocked managed delete", deleted.await(300, TimeUnit.MILLISECONDS))
                assertTrue(backend.records.isEmpty())
            } finally { release.countDown(); assertTrue(exported.await(2, TimeUnit.SECONDS)) }
        }
    }

    @Test fun staleExportPickerTicketsNeverOpenDestination() {
        DiagnosticsRecorder(MemoryBackend()).use { recorder ->
            await(recorder::barrier)
            val stale = recorder.newExport()
            recorder.newExport()
            var opened = false
            val finished = CountDownLatch(1)
            var succeeded = true
            recorder.export(stale, DiagnosticStream.TEXT, { opened = true; ByteArrayOutputStream() }) {
                succeeded = it; finished.countDown()
            }
            assertTrue(finished.await(2, TimeUnit.SECONDS))
            assertFalse(opened); assertFalse(succeeded)
        }
    }

    @Test fun storedConsentLoadsAfterEarlySessionButCannotAdoptThatSessionsContext() {
        val backend = MemoryBackend(mapOf(DiagnosticsPreferences.TEXT to true,
            DiagnosticsPreferences.CONSENT to 1), blockLoad = true)
        DiagnosticsRecorder(backend).use { recorder ->
            assertTrue(backend.loadEntered.await(2, TimeUnit.SECONDS))
            recorder.startSession(1, true, true)
            backend.loadRelease.countDown()
            await(recorder::barrier)
            assertTrue("Early session must not discard stored consent", recorder.preferences.text)
            recorder.record(event(1)) { error("Pre-load session context must not be adopted") }
            recorder.startSession(2, true, true)
            recorder.record(event(2)) { DiagnosticText(input = "fresh") }
            await(recorder::barrier)
            assertTrue(backend.records.any { "fresh" in it.second.decodeToString() })
        }
    }

    @Test fun countCapacityAndRecordCapacityAreEnforcedIndependently() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier)
            await { recorder.setMetadata(true, it) }
            recorder.startSession(1, true, true)
            backend.block = true
            recorder.record(event(1))
            assertTrue(backend.entered.await(2, TimeUnit.SECONDS))
            repeat(600) { recorder.record(event(1)) }
            assertEquals(256, recorder.queuedEvents)
            backend.release.countDown(); await(recorder::barrier)
            assertEquals(257, backend.records.size)
            enable(recorder); recorder.startSession(2, true, true)
            recorder.record(event(2)) { DiagnosticText(context = "\u0000".repeat(2_048)) }
            await(recorder::barrier)
            assertTrue(backend.records.all { it.second.size <= 8 * 1024 })
            assertFalse(backend.records.any { it.first == DiagnosticStream.TEXT })
        }
    }

    @Test fun confirmedPreferenceSaveSurvivesQueuedAndInflightSessionChangesWithoutAdoptingContext() {
        for (inFlight in listOf(false, true)) {
            val backend = MemoryBackend(blockLoad = !inFlight)
            DiagnosticsRecorder(backend).use { recorder ->
                if (inFlight) { await(recorder::barrier); backend.blockSave = true }
                else assertTrue(backend.loadEntered.await(2, TimeUnit.SECONDS))
                val consent = DiagnosticsConsent { recorder.generation }
                val ticket = consent.begin(); assertTrue(consent.scope(ticket))
                val done = CountDownLatch(1); var success = false
                recorder.enableText(checkNotNull(consent.storage(ticket))) { success = it; done.countDown() }
                if (inFlight) assertTrue(backend.saveEntered.await(2, TimeUnit.SECONDS))
                recorder.invalidate(); recorder.startSession(41, true, true)
                backend.loadRelease.countDown(); backend.saveRelease.countDown()
                assertTrue(done.await(2, TimeUnit.SECONDS))
                assertTrue("Confirmed save was invalidated by a session transition", success)
                assertTrue(recorder.preferences.text)
                assertTrue(DiagnosticsPreferences.decode(backend.stored).text)
                recorder.record(event(41)) { error("Session started before save acknowledgement was adopted") }
                recorder.startSession(42, true, true)
                recorder.record(event(42)) { DiagnosticText(input = "fresh-after-save") }
                await(recorder::barrier)
                assertTrue(backend.records.any { "fresh-after-save" in it.second.decodeToString() })
            }
            DiagnosticsRecorder(MemoryBackend(backend.stored)).use { reloaded ->
                await(reloaded::barrier); assertTrue(reloaded.preferences.text)
            }
        }
    }

    @Test fun supersededQueuedAndInflightEnableCannotLeaveDurableEnableAtFailureAcknowledgement() {
        for (inFlight in listOf(false, true)) {
            val backend = MemoryBackend(blockLoad = !inFlight)
            DiagnosticsRecorder(backend).use { recorder ->
                if (inFlight) { await(recorder::barrier); backend.blockSave = true }
                else assertTrue(backend.loadEntered.await(2, TimeUnit.SECONDS))
                val consent = DiagnosticsConsent { recorder.generation }
                val ticket = consent.begin(); assertTrue(consent.scope(ticket))
                val enabled = CountDownLatch(1); var enableSucceeded = true; var durableAtFailure = true
                recorder.enableText(checkNotNull(consent.storage(ticket))) {
                    enableSucceeded = it; durableAtFailure = DiagnosticsPreferences.decode(backend.stored).text
                    enabled.countDown()
                }
                if (inFlight) assertTrue(backend.saveEntered.await(2, TimeUnit.SECONDS))
                val stopped = CountDownLatch(1); var stopSucceeded = false
                recorder.disableText { stopSucceeded = it; stopped.countDown() }
                backend.loadRelease.countDown(); backend.saveRelease.countDown()
                assertTrue(enabled.await(2, TimeUnit.SECONDS)); assertFalse(enableSucceeded)
                assertFalse("Failed enable left durable consent enabled", durableAtFailure)
                assertTrue(stopped.await(2, TimeUnit.SECONDS)); assertTrue(stopSucceeded)
                assertFalse(recorder.preferences.text)
                assertFalse(DiagnosticsPreferences.decode(backend.stored).text)
            }
            DiagnosticsRecorder(MemoryBackend(backend.stored)).use { reloaded ->
                await(reloaded::barrier); assertFalse(reloaded.preferences.text)
            }
        }
    }

    @Test fun failedDurableReconciliationNeverAcknowledgesStopAsSuccessfulAndCanBeRetried() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier); backend.blockSave = true
            val consent = DiagnosticsConsent { recorder.generation }
            val ticket = consent.begin(); assertTrue(consent.scope(ticket))
            val enabled = CountDownLatch(1); var enableSucceeded = true
            recorder.enableText(checkNotNull(consent.storage(ticket))) { enableSucceeded = it; enabled.countDown() }
            assertTrue(backend.saveEntered.await(2, TimeUnit.SECONDS))
            backend.failDisabledSave = true
            val stopped = CountDownLatch(1); var stopSucceeded = true
            recorder.disableText { stopSucceeded = it; stopped.countDown() }
            backend.saveRelease.countDown()
            assertTrue(enabled.await(2, TimeUnit.SECONDS)); assertFalse(enableSucceeded)
            assertTrue(stopped.await(2, TimeUnit.SECONDS)); assertFalse(stopSucceeded)
            assertFalse(recorder.preferences.text)
            assertTrue("Backend intentionally retained failed-to-revoke durable choice",
                DiagnosticsPreferences.decode(backend.stored).text)
            backend.failDisabledSave = false
            await(recorder::disableText)
            assertFalse(DiagnosticsPreferences.decode(backend.stored).text)
        }
    }

    @Test fun reconciledFailureIsNotRetriedAsADifferentSuccessfulPreferenceCommand() {
        val backend = MemoryBackend()
        DiagnosticsRecorder(backend).use { recorder ->
            await(recorder::barrier); backend.blockSave = true
            val consent = DiagnosticsConsent { recorder.generation }
            val ticket = consent.begin(); assertTrue(consent.scope(ticket))
            val enabled = CountDownLatch(1)
            recorder.enableText(checkNotNull(consent.storage(ticket))) { enabled.countDown() }
            assertTrue(backend.saveEntered.await(2, TimeUnit.SECONDS))
            backend.failMetadataSave = true
            val metadata = CountDownLatch(1); var succeeded = true
            recorder.setMetadata(true) { succeeded = it; metadata.countDown() }
            backend.saveRelease.countDown()
            assertTrue(enabled.await(2, TimeUnit.SECONDS)); assertTrue(metadata.await(2, TimeUnit.SECONDS))
            assertFalse("Failed requested enable must not acknowledge a fallback OFF write as success", succeeded)
            assertEquals(DiagnosticsPreferences(), recorder.preferences)
            assertEquals(2, backend.saveAttempts)
        }
    }

    private fun event(session: Long) = DiagnosticEvent(DiagnosticKind.INPUT, DiagnosticReason.NONE, session, 1)
    private fun enable(recorder: DiagnosticsRecorder) {
        val consent = DiagnosticsConsent { recorder.generation }
        val ticket = consent.begin()
        assertTrue(consent.scope(ticket))
        val grant = checkNotNull(consent.storage(ticket))
        await { recorder.enableText(grant, it) }
        assertTrue(recorder.preferences.text)
    }
    private fun await(action: ((Boolean) -> Unit) -> Unit) {
        val latch = CountDownLatch(1)
        var result = false
        action { result = it; latch.countDown() }
        assertTrue("Writer acknowledgement timed out", latch.await(3, TimeUnit.SECONDS))
        assertTrue("Writer command failed", result)
    }
    private class MemoryBackend(private val initial: Map<String, *> = emptyMap<String, Any>(),
        private val blockLoad: Boolean = false) : DiagnosticsBackend {
        val records = Collections.synchronizedList(mutableListOf<Pair<DiagnosticStream, ByteArray>>())
        @Volatile var block = false
        @Volatile var failAppend = false
        @Volatile var blockSave = false
        @Volatile var failDisabledSave = false
        @Volatile var failMetadataSave = false
        @Volatile var saveAttempts = 0
        @Volatile var stored: Map<String, *> = initial
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val loadEntered = CountDownLatch(1)
        val loadRelease = CountDownLatch(1)
        val saveEntered = CountDownLatch(1)
        val saveRelease = CountDownLatch(1)
        override fun loadPreferences(): Map<String, *> {
            loadEntered.countDown()
            if (blockLoad) check(loadRelease.await(3, TimeUnit.SECONDS))
            return stored
        }
        override fun savePreferences(value: DiagnosticsPreferences): Boolean {
            saveAttempts++
            if (blockSave) { saveEntered.countDown(); check(saveRelease.await(3, TimeUnit.SECONDS)) }
            if (failDisabledSave && !value.text) return false
            if (failMetadataSave && value.metadata) return false
            stored = mapOf(DiagnosticsPreferences.METADATA to value.metadata,
                DiagnosticsPreferences.TEXT to value.text, DiagnosticsPreferences.CONSENT to if (value.text) 1 else 0)
            return true
        }
        override fun append(stream: DiagnosticStream, bytes: ByteArray) {
            if (block) { entered.countDown(); check(release.await(3, TimeUnit.SECONDS)) }
            if (failAppend) throw IllegalStateException("private storage exception")
            records.add(stream to bytes.copyOf())
        }
        override fun snapshot(stream: DiagnosticStream): ByteArray = synchronized(records) {
            records.filter { it.first == stream }.flatMap { it.second.toList() }.toByteArray()
        }
        override fun delete() { records.clear() }
    }
}
