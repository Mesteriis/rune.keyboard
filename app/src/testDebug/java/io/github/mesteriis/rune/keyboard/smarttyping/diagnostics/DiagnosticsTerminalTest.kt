package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingTextResult
import io.github.mesteriis.rune.keyboard.smarttyping.session.jvmGraphemes
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert.*
import org.junit.Test

class DiagnosticsTerminalTest {
    @Test fun lateScoringNeedsAnAdmittedExactRequestAndRetainsOnlyOriginMetadata() {
        val backend = Backend()
        DiagnosticsRecorder(backend).use { recorder ->
            configure(recorder, setOf(DiagnosticStream.TEXT)); recorder.startSession(7, true, true)
            recorder.record(DiagnosticEvent(DiagnosticKind.REQUEST, DiagnosticReason.SUBMITTED, 7, 10,
                source = DiagnosticSource.CONTEXTUAL, requestId = 3), null)
            await(recorder::barrier); backend.records.clear()
            recorder.startSession(8, false, true)
            val stale = DiagnosticEvent(DiagnosticKind.RANKING, DiagnosticReason.STALE, 7, 10,
                source = DiagnosticSource.MODEL, requestId = 3, scoringCode = 9, elapsedMs = 21)
            recorder.record(stale.copy(revision = 11), null)
            recorder.record(stale, null); recorder.record(stale, null)
            await(recorder::barrier)
            val line = backend.records.single().second
            assertTrue(line.contains("\"session\":7,")); assertTrue(line.contains("\"revision\":10,"))
            assertTrue(line.contains("\"source\":\"CONTEXTUAL\"")); assertTrue(line.contains("\"scoringCode\":9"))
            assertFalse(line.contains("\"input\""))
        }
    }

    @Test fun lateScoringAdmissionIsBoundedAndRevokedByConsentChanges() {
        val backend = Backend()
        DiagnosticsRecorder(backend).use { recorder ->
            configure(recorder, setOf(DiagnosticStream.TEXT)); recorder.startSession(7, true, true)
            for (id in 1L..100) recorder.record(DiagnosticEvent(DiagnosticKind.REQUEST, DiagnosticReason.SUBMITTED,
                7, 10, source = DiagnosticSource.MODEL, requestId = id), null)
            await(recorder::barrier); backend.records.clear(); recorder.invalidate()
            for (id in 1L..100) recorder.record(DiagnosticEvent(DiagnosticKind.RANKING, DiagnosticReason.STALE,
                7, 10, requestId = id, scoringCode = 9), null)
            await(recorder::barrier)
            assertTrue(backend.records.size in 1..32)
            recorder.startSession(8, true, true)
            recorder.record(DiagnosticEvent(DiagnosticKind.REQUEST, DiagnosticReason.SUBMITTED,
                8, 20, source = DiagnosticSource.MODEL, requestId = 101), null)
            await(recorder::disableText); backend.records.clear()
            recorder.record(DiagnosticEvent(DiagnosticKind.RANKING, DiagnosticReason.STALE,
                8, 20, requestId = 101, scoringCode = 9), null)
            await(recorder::barrier); assertTrue(backend.records.isEmpty())
        }
    }

    @Test fun acceptedOutcomeRetainsExactAdmittedOperationWithoutTextAcrossPrivacyTransition() {
        val backend = Backend()
        DiagnosticsRecorder(backend).use { recorder ->
            configure(recorder, DiagnosticStream.entries.toSet()); recorder.startSession(7, true, true)
            val terminal = checkNotNull(recorder.editorOutcome(DiagnosticEvent(DiagnosticKind.MANUAL,
                DiagnosticReason.CORRECTION, 7, 10, source = DiagnosticSource.CANONICAL_CASE, operationId = 31)))
            recorder.invalidate(); recorder.startSession(8, false, true)
            terminal(true); terminal(false)
            await(recorder::barrier)
            assertEquals(2, backend.records.size)
            backend.records.forEach { (_, line) ->
                assertTrue(line.contains("\"session\":7,")); assertTrue(line.contains("\"revision\":10,"))
                assertTrue(line.contains("\"operationId\":31")); assertTrue(line.contains("EDITOR_ACCEPTED"))
                assertTrue(line.contains("CANONICAL_CASE")); assertFalse(line.contains("\"input\""))
            }
        }
    }

    @Test fun refusedEditorRetainsOnlyOriginalContentFreeOutcomeAcrossSensitiveTransition() = refusal(false)
    @Test fun reentrantEditorSessionUsesOriginIdsAndDoesNotCaptureReplacementSession() = refusal(true)

    private fun refusal(reentrant: Boolean) {
        for (streams in listOf(setOf(DiagnosticStream.METADATA), setOf(DiagnosticStream.TEXT), DiagnosticStream.entries.toSet())) {
            val backend = Backend()
            DiagnosticsRecorder(backend).use { recorder ->
                configure(recorder, streams)
                val controller = TypingSessionController(jvmGraphemes)
                controller.setDiagnostics(recorder)
                controller.startSession(EditorContext.from(1, 0), 0, 0)
                controller.typeText("public") { true }
                await(recorder::barrier); backend.records.clear()
                val session = controller.state.sessionId
                val revision = controller.state.revision + 1
                backend.block = true
                controller.recordInput("public-blocker")
                assertTrue(backend.entered.await(2, TimeUnit.SECONDS))
                try {
                    assertEquals(TypingTextResult.REJECTED, controller.typeText("x") {
                        if (reentrant) controller.startSession(EditorContext.from(129, 0), 0, 0)
                        reentrant
                    })
                    if (!reentrant) controller.startSession(EditorContext.from(129, 0), 0, 0)
                    recorder.record(DiagnosticEvent(DiagnosticKind.INPUT, DiagnosticReason.NONE,
                        controller.state.sessionId, controller.state.revision)) { error("Sensitive payload copied") }
                } finally { backend.release.countDown() }
                await(recorder::barrier)
                val outcomes = backend.records.filter { "EDITOR_REJECTED" in it.second }
                assertEquals("Missing independent stream outcomes", streams, outcomes.map { it.first }.toSet())
                assertEquals(streams.size, outcomes.size)
                outcomes.forEach { (_, line) ->
                    assertTrue(line.contains("\"session\":$session,"))
                    assertTrue(line.contains("\"revision\":$revision,"))
                    assertFalse("Terminal record contains text fields", line.contains("\"input\""))
                    assertFalse(line.contains("\"context\"")); assertFalse(line.contains("\"candidates\""))
                }
                assertTrue(backend.records.all { "public-blocker" in it.second || "EDITOR_REJECTED" in it.second ||
                    (it.first == DiagnosticStream.METADATA && "\"kind\":\"INPUT\"" in it.second) })
            }
        }
    }

    @Test fun queuedTerminalOutcomeIsRevokedByOffAndDeleteBeforeAcknowledgement() {
        for (delete in listOf(false, true)) {
            val backend = Backend()
            DiagnosticsRecorder(backend).use { recorder ->
                configure(recorder, setOf(DiagnosticStream.TEXT)); recorder.startSession(9, true, true)
                backend.block = true
                recorder.record(DiagnosticEvent(DiagnosticKind.INPUT, DiagnosticReason.NONE, 9, 1)) { DiagnosticText(input = "inflight") }
                assertTrue(backend.entered.await(2, TimeUnit.SECONDS))
                try {
                    val refused = checkNotNull(recorder.editorOperation(9, 2))
                    recorder.invalidate(); refused()
                    val done = CountDownLatch(1); var success = false
                    if (delete) recorder.delete { success = it; done.countDown() }
                    else recorder.disableText { success = it; done.countDown() }
                    assertFalse(done.await(40, TimeUnit.MILLISECONDS))
                    refused() // Already consumed, and consent has also been revoked.
                    backend.release.countDown()
                    assertTrue(done.await(2, TimeUnit.SECONDS)); assertTrue(success)
                    await(recorder::barrier)
                    assertFalse(backend.records.any { "EDITOR_REJECTED" in it.second })
                    if (delete) assertTrue(backend.records.isEmpty())
                } finally { backend.release.countDown() }
            }
        }
    }

    @Test fun terminalAdmissionIsOneShotAndCannotOriginateFromIneligibleOrUnarmedSession() {
        val backend = Backend()
        DiagnosticsRecorder(backend).use { recorder ->
            configure(recorder, setOf(DiagnosticStream.TEXT))
            recorder.startSession(1, false, true); assertNull(recorder.editorOperation(1, 1))
            recorder.startSession(2, true, false); assertNull(recorder.editorOperation(2, 1))
            recorder.startSession(3, true, true)
            assertNull(recorder.editorOperation(2, 1))
            val callback = checkNotNull(recorder.editorOperation(3, 1))
            recorder.invalidate(); callback(); callback()
            await(recorder::barrier)
            assertEquals(1, backend.records.size)
            assertTrue(backend.records.single().second.contains("EDITOR_REJECTED"))
            assertFalse(backend.records.single().second.contains("\"input\""))
        }
    }

    private fun configure(recorder: DiagnosticsRecorder, streams: Set<DiagnosticStream>) {
        await(recorder::barrier)
        if (DiagnosticStream.METADATA in streams) await { recorder.setMetadata(true, it) }
        if (DiagnosticStream.TEXT in streams) {
            val consent = DiagnosticsConsent { recorder.generation }
            val ticket = consent.begin(); assertTrue(consent.scope(ticket))
            await { recorder.enableText(checkNotNull(consent.storage(ticket)), it) }
        }
    }
    private fun await(action: ((Boolean) -> Unit) -> Unit) {
        val done = CountDownLatch(1); var success = false
        action { success = it; done.countDown() }
        assertTrue(done.await(3, TimeUnit.SECONDS)); assertTrue(success)
    }
    private class Backend : DiagnosticsBackend {
        val records = Collections.synchronizedList(mutableListOf<Pair<DiagnosticStream, String>>())
        @Volatile var block = false
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        override fun loadPreferences() = emptyMap<String, Any>()
        override fun savePreferences(value: DiagnosticsPreferences) = true
        override fun append(stream: DiagnosticStream, bytes: ByteArray) {
            if (block) { entered.countDown(); check(release.await(3, TimeUnit.SECONDS)) }
            records.add(stream to bytes.decodeToString())
        }
        override fun snapshot(stream: DiagnosticStream) = byteArrayOf()
        override fun delete() { records.clear() }
    }
}
