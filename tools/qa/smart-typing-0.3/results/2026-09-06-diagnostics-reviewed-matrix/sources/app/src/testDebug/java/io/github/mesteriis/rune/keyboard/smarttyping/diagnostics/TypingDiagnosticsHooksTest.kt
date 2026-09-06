package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.session.*
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
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

    @Test fun contextualWinnerAndTapPairActualSevenVariantsWithTheirOriginAndResult() {
        val observer = Observer(); val controller = contextual(observer)
        val request = checkNotNull(controller.beginContextualRanking(1))
        assertEquals(7, request.continuations.size)
        assertTrue(controller.acceptContextualRanking(ScoringReply(request.token, ScoringCode.OK, 0,
            request.token.candidateIds.map { NumericScore(it, if (it == 4) -1.0 else -100.0, 1) })))
        assertDecision(observer, DiagnosticKind.RANKING, DiagnosticReason.CONTEXTUAL, request,
            "world", request.continuations, 4, ". World")
        val candidate = controller.candidateViewState.candidates.single { it is CandidateUiItem.Punctuation }
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(candidate.id) { true })
        assertDecision(observer, DiagnosticKind.MANUAL, DiagnosticReason.CONTEXTUAL, request,
            "world", request.continuations, 4, ". World")
        assertEquals("hello. World", controller.state.contextText)
    }

    @Test fun contextualAbstentionAndErrorPairActualPendingVariantsWithoutFabricatingDecision() {
        for (code in listOf(ScoringCode.CANCELLED, ScoringCode.OK)) {
            val observer = Observer(); val controller = contextual(observer)
            val request = checkNotNull(controller.beginContextualRanking(1))
            assertFalse(controller.acceptContextualRanking(ScoringReply(request.token, code, 0,
                if (code == ScoringCode.OK) request.token.candidateIds.map { NumericScore(it, -10.0, 1) } else emptyList())))
            assertDecision(observer, DiagnosticKind.RANKING,
                if (code == ScoringCode.OK) DiagnosticReason.ABSTAINED else DiagnosticReason.MODEL_ERROR,
                request, "world", request.continuations, -1, "")
            assertEquals("hello world", controller.state.contextText)
        }
    }

    @Test fun deferredSpaceAbstentionAndErrorUseSavedWordCandidatesAndRequestRevision() {
        for (code in listOf(ScoringCode.CANCELLED, ScoringCode.OK)) {
            val observer = Observer(); val controller = prepared(observer)
            val request = checkNotNull(controller.beginModelRanking(1))
            assertEquals(TypingTextResult.HANDLED, controller.retainRankingAcrossSpace {
                controller.typeText(" ", policy, keyboard,
                    autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
            })
            assertTrue(controller.isCurrentSpaceCorrection(request.token))
            assertEquals("helllo ", controller.state.contextText)
            assertFalse(controller.acceptSpaceCorrection(ScoringReply(request.token, code, 0,
                if (code == ScoringCode.OK) request.token.candidateIds.map {
                    NumericScore(it, if (it == 0) -1.0 else -100.0, 1)
                } else emptyList())) { true })
            assertDecision(observer, DiagnosticKind.RANKING,
                if (code == ScoringCode.OK) DiagnosticReason.ABSTAINED else DiagnosticReason.MODEL_ERROR,
                request, "helllo", listOf("hello"), -1, "")
            assertEquals("helllo ", controller.state.contextText)
        }
    }

    private fun assertDecision(observer: Observer, kind: DiagnosticKind, reason: DiagnosticReason,
        request: ScoringInput, original: String, candidates: List<String>, selected: Int, result: String) {
        val (event, payload) = observer.records.last { it.first.kind == kind && it.first.reason == reason }
        assertEquals(request.token.sessionId, event.session); assertEquals(request.token.revision, event.revision)
        assertEquals(candidates.size, event.candidateCount); assertEquals(selected, event.selectedIndex)
        val text = checkNotNull(payload)
        assertEquals(original, text.original); assertEquals(candidates, text.candidates); assertEquals(result, text.result)
    }

    private fun contextual(observer: Observer): TypingSessionController {
        val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
        for (value in listOf("hello", " ", "world")) controller.typeText(value) { true }
        val request = checkNotNull(controller.beginCandidateRequest(1, KeyboardLanguage.ENGLISH))
        assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
            CandidateGeneration(request.token, emptyList(), CandidateCompletion.COMPLETE, true, null, 1, 1))))
        return controller
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
        val records = mutableListOf<Pair<DiagnosticEvent, DiagnosticText?>>()
        val events get() = records.map { it.first }
        val texts get() = records.mapNotNull { it.second }
        override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) { active = eligible && fresh }
        override fun invalidate() { active = false }
        override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) {
            if (active) records.add(event to text?.invoke())
        }
        fun has(kind: DiagnosticKind, reason: DiagnosticReason) = events.any { it.kind == kind && it.reason == reason }
    }
    private val keyboard = KeyboardState(KeyboardLanguage.ENGLISH)
    private val policy = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, true)
}
