package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.session.*
import org.junit.Assert.*
import org.junit.Test

class TypingDiagnosticsHooksTest {
    @Test fun recordsActualCandidateRankingBoundaryAndUndoBranches() {
        val observer = Observer()
        val controller = prepared(observer)
        val request = controller.beginModelRanking(1)!!
        assertTrue(controller.acceptModelRanking(ScoringReply(request.token, ScoringCode.OK, 0,
            listOf(NumericScore(0, -100.0, 1), NumericScore(1, -1.0, 1)))))
        assertEquals(TypingTextResult.HANDLED, controller.typeText(" ", policy, keyboard,
            autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true })
        assertEquals("hello ", controller.state.contextText)
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious { true })
        assertEquals("helllo", controller.state.contextText)
        assertTrue(observer.has(DiagnosticKind.CANDIDATES, DiagnosticReason.ACCEPTED))
        assertTrue(observer.has(DiagnosticKind.RANKING, DiagnosticReason.ACCEPTED))
        assertTrue(observer.has(DiagnosticKind.BOUNDARY, DiagnosticReason.AUTO_REPLACE))
        assertTrue(observer.has(DiagnosticKind.UNDO, DiagnosticReason.ACCEPTED))
        assertTrue(observer.has(DiagnosticKind.EDITOR, DiagnosticReason.EDITOR_ACCEPTED))
        assertTrue(observer.texts.any { "hello" in it.candidates && it.original == "helllo" })
    }

    @Test fun rejectionAndProtectedBoundaryReasonsComeFromExistingBranches() {
        val observer = Observer()
        val controller = prepared(observer)
        val request = controller.beginModelRanking(1)!!
        assertFalse(controller.acceptModelRanking(ScoringReply(request.token, ScoringCode.CANCELLED, 0, emptyList())))
        assertTrue(observer.has(DiagnosticKind.RANKING, DiagnosticReason.MODEL_ERROR))
        controller.typeText(".", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertEquals("helllo.", controller.state.contextText)
        assertTrue(observer.has(DiagnosticKind.BOUNDARY, DiagnosticReason.PROTECTED_FORM))
    }

    @Test fun manualOriginalUsesActualChoiceWithoutASecondPolicyDecision() {
        val observer = Observer()
        val controller = prepared(observer)
        assertTrue(controller.selectOriginal(controller.originalCandidateId!!))
        assertTrue(observer.has(DiagnosticKind.MANUAL, DiagnosticReason.ORIGINAL))
        assertTrue(controller.state.originalSelected)
    }

    @Test fun invalidationClosesObserverBeforeEditorFinalization() {
        val observer = Observer()
        val controller = prepared(observer)
        assertTrue("Positive session must arm observer", observer.active)
        controller.invalidate {
            assertFalse("Admission must close before final editor command", observer.active)
            true
        }
        assertFalse(observer.active)
        controller.startSession(EditorContext.from(129, 0), 0, 0)
        assertFalse(observer.active)
    }

    @Test fun throwingObserverCannotChangeSuccessfulOrRejectedEditorBehavior() {
        val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(object : TypingDiagnostics {
            override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) { error("observer") }
            override fun invalidate() { error("observer") }
            override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) { error("observer") }
        })
        controller.startSession(EditorContext.from(1, 0), 0, 0)
        assertEquals(TypingTextResult.HANDLED, controller.typeText("public") { true })
        assertEquals("public", controller.state.contextText)
        assertEquals(TypingTextResult.REJECTED, controller.typeText("x") { false })
        assertFalse(controller.state.enabled)
    }

    private fun prepared(observer: Observer): TypingSessionController {
        val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(observer)
        controller.startSession(EditorContext.from(1, 0), 0, 0)
        controller.typeText("helllo") { true }
        val request = controller.beginCandidateRequest(1, KeyboardLanguage.ENGLISH)!!
        val word = GeneratedCandidate("hello", "hello", "hello", KeyboardLanguage.ENGLISH,
            false, 4, 1, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER)
        assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
            CandidateGeneration(request.token, listOf(word), CandidateCompletion.COMPLETE, false, null, 1, 1))))
        return controller
    }
    private class Observer : TypingDiagnostics {
        var active = false
        val events = mutableListOf<DiagnosticEvent>()
        val texts = mutableListOf<DiagnosticText>()
        override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) { active = eligible && fresh }
        override fun invalidate() { active = false }
        override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) {
            if (active) { events.add(event); text?.let { texts.add(it()) } }
        }
        fun has(kind: DiagnosticKind, reason: DiagnosticReason) = events.any { it.kind == kind && it.reason == reason }
    }
    private val keyboard = KeyboardState(KeyboardLanguage.ENGLISH)
    private val policy = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, true)
}
