package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.intelligence.client.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.session.*
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import org.junit.Assert.*
import org.junit.Test

class TypingDiagnosticsHooksTest {
    @Test fun textChangingOriginalSelectionHasAnExactEditorOperationButVetoDoesNot() {
        for (accepted in listOf(true, false)) {
            val observer = Observer(); val controller = prepared(observer)
            val correction = controller.candidateViewState.candidates.filterIsInstance<CandidateUiItem.Correction>().first().id
            controller.selectCandidate(correction) { true }
            val priorAttempt = observer.events.last { it.kind == DiagnosticKind.MANUAL }
            assertEquals("hello", controller.state.contextText)
            observer.records.clear()
            controller.selectCandidate(controller.originalCandidateId!!) { accepted }
            val attempt = observer.records.single { it.first.kind == DiagnosticKind.MANUAL }
            val outcome = observer.events.single { it.kind == DiagnosticKind.EDITOR }
            assertEquals(DiagnosticReason.ORIGINAL, attempt.first.reason)
            assertTrue(attempt.first.operationId > 0)
            assertEquals(attempt.first.operationId, outcome.operationId)
            assertEquals(attempt.first.revision, outcome.revision)
            assertEquals(priorAttempt.requestId, attempt.first.requestId)
            assertTrue(attempt.first.requestId > 0)
            assertEquals("hello", attempt.second!!.original); assertEquals("helllo", attempt.second!!.result)
            assertEquals(if (accepted) DiagnosticReason.EDITOR_ACCEPTED else DiagnosticReason.EDITOR_REJECTED, outcome.reason)
            if (accepted) assertEquals("helllo", controller.state.contextText)
        }
        val observer = Observer(); val controller = prepared(observer)
        observer.records.clear()
        controller.selectCandidate(controller.originalCandidateId!!) { error("Veto cannot mutate editor") }
        assertEquals(0L, observer.events.single().operationId)
    }

    @Test fun ordinaryLettersDoNotProduceBoundaryDecisions() {
        val observer = Observer(); val controller = prepared(observer)
        observer.records.clear()
        controller.recordInput("x")
        controller.typeText("x", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertFalse(observer.events.any { it.kind == DiagnosticKind.BOUNDARY })
        controller.typeText(" ", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertTrue(observer.events.any { it.kind == DiagnosticKind.BOUNDARY })
    }

    @Test fun backspaceRecordsTheOwnedWordWithoutStealingTheEditorOperation() {
        val observer = Observer(); val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
        controller.typeText("word") { true }
        observer.records.clear()
        controller.recordBackspace()
        assertEquals(TypingTextResult.HANDLED, controller.deletePrevious { true })
        val attempt = observer.records.single { it.first.kind == DiagnosticKind.BACKSPACE }
        val outcome = observer.events.single { it.kind == DiagnosticKind.EDITOR }
        assertEquals("word", attempt.second!!.original)
        assertEquals(0L, attempt.first.operationId)
        assertTrue(outcome.operationId > 0)
        assertEquals(DiagnosticReason.EDITOR_ACCEPTED, outcome.reason)
    }

    @Test fun staleScoringUsesOriginalIdentityAndExactCodeWithoutText() {
        val observer = Observer(); val controller = prepared(observer)
        val request = checkNotNull(controller.beginModelRanking(1))
        controller.typeText("x") { true }
        assertFalse(controller.acceptModelRanking(ScoringReply(request.token, ScoringCode.CANCELLED, 17, emptyList())))
        val (event, text) = observer.records.last()
        assertEquals(request.token.revision, event.revision)
        assertEquals(request.token.sessionId, event.session)
        assertNull(text)
        val encoded = DiagnosticsEncoding.metadata(event).decodeToString()
        assertTrue(encoded.contains("\"scoringCode\":9"))
        assertTrue(encoded.contains("\"elapsedMs\":17"))
    }

    @Test fun schemaTwoAttributesCandidateCompletionAndDecisionSource() {
        val observer = Observer(); prepared(observer)
        val event = observer.events.last { it.kind == DiagnosticKind.CANDIDATES }
        val encoded = DiagnosticsEncoding.metadata(event).decodeToString()
        assertTrue(encoded.contains("\"schema\":2"))
        assertTrue(encoded.contains("\"completion\":\"COMPLETE\""))
        assertTrue(encoded.contains("\"source\":\"LOCAL_POLICY\""))
    }

    @Test fun correctionAttemptAndTerminalOutcomeMatchExactOperationAfterEditorResponse() {
        for (accepted in listOf(true, false)) {
            val observer = Observer(); val controller = prepared(observer)
            val id = controller.candidateViewState.candidates.filterIsInstance<CandidateUiItem.Correction>().first().id
            observer.records.clear()
            var firstCall = true
            controller.selectCandidate(id) {
                if (firstCall) assertFalse(observer.events.any { it.kind == DiagnosticKind.EDITOR })
                firstCall = false
                accepted
            }
            val attempt = observer.events.first { it.kind == DiagnosticKind.MANUAL }
            val outcome = observer.events.single { it.kind == DiagnosticKind.EDITOR }
            assertEquals(DiagnosticSource.LOCAL_POLICY, attempt.source)
            assertEquals(attempt.source, outcome.source)
            val operationPattern = Regex("\\\"operationId\\\":([0-9]+)")
            val operation = operationPattern.find(DiagnosticsEncoding.metadata(attempt).decodeToString())?.groupValues?.get(1)
            assertNotNull(operation); assertNotEquals("0", operation)
            assertEquals(operation, operationPattern.find(DiagnosticsEncoding.metadata(outcome).decodeToString())?.groupValues?.get(1))
            assertEquals(attempt.revision, outcome.revision)
            assertEquals(if (accepted) DiagnosticReason.EDITOR_ACCEPTED else DiagnosticReason.EDITOR_REJECTED, outcome.reason)
        }
    }

    @Test fun candidateCompletionsRetainExactSearchStatusIncludingFailureAndExhaustion() {
        for (completion in CandidateCompletion.entries) {
            val observer = Observer(); val controller = TypingSessionController(jvmGraphemes)
            controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
            controller.typeText("word") { true }
            val request = checkNotNull(controller.beginCandidateRequest(1, KeyboardLanguage.ENGLISH))
            controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration("word", emptyList(), completion, completion == CandidateCompletion.VALID_WORD,
                    if (completion == CandidateCompletion.PROTECTED) ProtectedTokenReason.ALL_CAPS else null, 1, 1)))
            val event = observer.events.last { it.kind == DiagnosticKind.CANDIDATES }
            assertEquals(completion.name, event.completion.name)
            assertEquals(1L, event.requestId)
            assertTrue(event.elapsedMs in 0..60_000)
        }
    }

    @Test fun mechanicalAttemptsHaveTheirActualSource() {
        val observer = Observer(); val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
        controller.typeText("hello") { true }
        controller.typeText(" ", policy, keyboard) { true }
        controller.typeText(" ", policy, keyboard, doubleSpaceGesture = true) { true }
        val attempt = observer.events.last { it.reason == DiagnosticReason.AUTO_REPLACE }
        assertEquals(DiagnosticSource.MECHANICAL, attempt.source)
        assertTrue(attempt.operationId > 0)
        assertEquals(attempt.operationId, observer.events.last { it.kind == DiagnosticKind.EDITOR }.operationId)
    }

    @Test fun boundaryNotReadyIsDistinctFromPolicyRejectionAndModelAbstention() {
        val observer = Observer(); val controller = prepared(observer)
        controller.beginModelRanking(1)
        controller.typeText(" ", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertTrue(observer.has(DiagnosticKind.BOUNDARY, DiagnosticReason.RESULT_NOT_READY))
        val other = Observer(); val ready = prepared(other)
        ready.typeText(" ", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertTrue(other.has(DiagnosticKind.BOUNDARY, DiagnosticReason.POLICY_REJECTED))
    }

    @Test fun validWordBoundaryIsNotMisreportedAsMissingContextualRanking() {
        val observer = Observer(); val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
        controller.typeText("word") { true }
        val local = checkNotNull(controller.beginCandidateRequest(1, KeyboardLanguage.ENGLISH))
        assertTrue(controller.acceptCandidates(LocalCandidateReply(local.sessionId, local.revision, local.requestId,
            CandidateGeneration(local.token, emptyList(), CandidateCompletion.VALID_WORD, true, null, 1, 1))))
        controller.recordRequest(DiagnosticReason.SCHEDULED, DiagnosticSource.CONTEXTUAL)
        controller.typeText(" ", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertEquals(DiagnosticReason.VALID_WORD,
            observer.events.single { it.kind == DiagnosticKind.BOUNDARY }.reason)
    }

    @Test fun modelSchedulingCancellationAndUnavailableServiceRemainAttributed() {
        val observer = Observer(); val controller = prepared(observer)
        var scheduledTask: Runnable? = null
        val inputs = mutableListOf<ScoringInput>()
        val client = object : ModelScoringClient {
            override var available = true
            override fun attachSession(sessionId: Long?, effectiveAvailability: Boolean) = Unit
            override fun score(input: ScoringInput) { inputs += input }
            override fun cancel() = Unit
            override fun close() = Unit
        }
        val scheduler = object : ModelPauseScheduler {
            override fun postDelayed(task: Runnable, millis: Long) { scheduledTask = task }
            override fun remove(task: Runnable) { if (scheduledTask === task) scheduledTask = null }
        }
        val readiness = object : ModelReadinessSource {
            override val hint = ModelReadinessHint.READY
            override fun setActive(active: Boolean) = Unit
            override fun close() = Unit
        }
        ModelCandidateCoordinator(controller, { client }, scheduler,
            { CandidateOwnerState(true, true, KeyboardLayer.LETTERS, KeyboardLanguage.ENGLISH, false) },
            readiness, {}).use { coordinator ->
            observer.records.clear()
            coordinator.candidatesChanged()
            assertTrue(observer.has(DiagnosticKind.REQUEST, DiagnosticReason.SCHEDULED))
            coordinator.cancel()
            assertTrue(observer.has(DiagnosticKind.REQUEST, DiagnosticReason.CANCELLED))
            coordinator.candidatesChanged(); scheduledTask!!.run()
            val request = inputs.single()
            coordinator.onReply(ScoringReply(request.token, ScoringCode.NO_MODEL, 53, emptyList()))
            val refusal = observer.events.last { it.reason == DiagnosticReason.SERVICE_REFUSED }
            assertEquals(request.token.revision, refusal.revision)
            assertEquals(request.token.requestId, refusal.requestId)
            assertEquals(ScoringCode.NO_MODEL, refusal.scoringCode)
            assertEquals(53L, refusal.elapsedMs)
            controller.typeText("x") { true }
            coordinator.onDiscardedReply(ScoringReply(request.token, ScoringCode.CANCELLED, 60, emptyList()))
            val stale = observer.records.last()
            assertEquals(DiagnosticReason.STALE, stale.first.reason)
            assertEquals(request.token.revision, stale.first.revision)
            assertNull(stale.second)
        }
    }

    @Test fun localSubmissionAndCancellationKeepRequestOrigin() {
        val observer = Observer(); val controller = prepared(observer)
        observer.records.clear()
        val request = checkNotNull(controller.beginCandidateRequest(2, KeyboardLanguage.ENGLISH))
        controller.typeText("x") { true }
        val requests = observer.events.filter { it.kind == DiagnosticKind.REQUEST }
        assertEquals(listOf(DiagnosticReason.SUBMITTED, DiagnosticReason.CANCELLED), requests.map { it.reason })
        assertTrue(requests.all { it.requestId == request.requestId && it.revision == request.revision &&
            it.source == DiagnosticSource.LOCAL_POLICY })
    }

    @Test fun eligibleLanguageAndLettersReturnReopensOnlyAnEmptyFreshSegment() {
        val observer = Observer(); val controller = prepared(observer)
        controller.invalidate { true }
        assertFalse(observer.active)
        controller.reopenDiagnosticsForLetters(false)
        assertFalse(observer.active)
        controller.reopenDiagnosticsForLetters(true)
        assertTrue(observer.active)
        controller.recordInput("fresh")
        assertEquals("", observer.texts.last().context)
        assertEquals(DiagnosticReason.START, observer.events.last { it.kind == DiagnosticKind.SESSION }.reason)
        controller.typeText("fresh") { true }
        val starts = observer.events.count { it.kind == DiagnosticKind.SESSION }
        controller.reopenDiagnosticsForLetters(true)
        assertEquals(starts, observer.events.count { it.kind == DiagnosticKind.SESSION })
        controller.startSession(EditorContext.from(129, 0), 0, 0)
        controller.reopenDiagnosticsForLetters(true)
        assertFalse(observer.active)
    }

    @Test fun contextualDecisionsAndManualCorrectionsRetainTheirSource() {
        val observer = Observer(); val controller = contextual(observer)
        val request = checkNotNull(controller.beginContextualRanking(1))
        controller.acceptContextualRanking(ScoringReply(request.token, ScoringCode.OK, 23,
            request.token.candidateIds.map { NumericScore(it, if (it == 4) -1.0 else -100.0, 1) }))
        val candidate = controller.candidateViewState.candidates.filterIsInstance<CandidateUiItem.Punctuation>().single()
        controller.selectCandidate(candidate.id) { true }
        assertTrue(observer.events.filter { it.reason == DiagnosticReason.CONTEXTUAL }.all {
            it.source == DiagnosticSource.CONTEXTUAL
        })
        assertEquals(DiagnosticSource.CONTEXTUAL, observer.events.last { it.kind == DiagnosticKind.EDITOR }.source)
    }

    @Test fun everyScoringDecisionKeepsExactCodeTimingAndAbstention() {
        for (code in listOf(ScoringCode.OK, ScoringCode.CANCELLED, ScoringCode.UNAVAILABLE,
                ScoringCode.INTERNAL, ScoringCode.SCORING_FAILED)) {
            val observer = Observer(); val controller = prepared(observer)
            val request = checkNotNull(controller.beginModelRanking(1))
            controller.acceptModelRanking(ScoringReply(request.token, code, 37,
                if (code == ScoringCode.OK) request.token.candidateIds.map {
                    NumericScore(it, if (it == 0) -1.0 else -100.0, 1)
                } else emptyList()))
            val event = observer.events.last { it.kind == DiagnosticKind.RANKING }
            assertEquals(code, event.scoringCode)
            assertEquals(37L, event.elapsedMs)
            assertEquals(request.token.requestId, event.requestId)
            assertEquals(when (code) {
                ScoringCode.OK -> DiagnosticReason.ABSTAINED
                ScoringCode.CANCELLED -> DiagnosticReason.CANCELLED
                ScoringCode.UNAVAILABLE -> DiagnosticReason.SERVICE_REFUSED
                ScoringCode.SCORING_FAILED -> DiagnosticReason.SCORING_FAILED
                else -> DiagnosticReason.MODEL_ERROR
            }, event.reason)
        }
    }

    @Test fun scorerFailureRemainsTheFinalWordBoundaryReason() {
        val observer = Observer(); val controller = prepared(observer)
        val request = checkNotNull(controller.beginModelRanking(1))
        assertFalse(controller.acceptModelRanking(ScoringReply(request.token,
            ScoringCode.SCORING_FAILED, 0, emptyList())))
        controller.typeText(" ", policy, keyboard,
            autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertEquals(DiagnosticReason.SCORING_FAILED,
            observer.events.single { it.kind == DiagnosticKind.BOUNDARY }.reason)
    }

    @Test fun mechanicalLetterTransformationIsNotABoundaryEvent() {
        val observer = Observer(); val controller = TypingSessionController(jvmGraphemes)
        controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
        for (text in listOf("hello", ".", " ")) controller.typeText(text, policy, keyboard) { true }
        observer.records.clear()
        controller.typeText("w", policy, keyboard) { true }
        assertFalse(observer.events.any { it.kind == DiagnosticKind.BOUNDARY })
        assertEquals("hello. W", controller.state.contextText)
    }

    @Test fun cancelledAtBoundaryIsNotMisreportedAsPolicyRejection() {
        val observer = Observer(); val controller = prepared(observer)
        controller.beginModelRanking(1)
        controller.cancelModelRanking()
        controller.typeText(" ", policy, keyboard, autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
        assertTrue(observer.has(DiagnosticKind.BOUNDARY, DiagnosticReason.RESULT_NOT_READY))
    }

    @Test fun canonicalCaseManualAndAutomaticAttemptsHaveCanonicalSource() {
        for (automatic in listOf(false, true)) {
            val observer = Observer(); val controller = TypingSessionController(jvmGraphemes)
            controller.setDiagnostics(observer); controller.startSession(EditorContext.from(1, 0), 0, 0)
            controller.typeText("london") { true }
            val request = checkNotNull(controller.beginCandidateRequest(1, KeyboardLanguage.ENGLISH))
            val word = GeneratedCandidate("London", "london", "london", KeyboardLanguage.ENGLISH,
                false, 4, 1, 0, EditFeatures(0.0, 0, 0.0), 0, CasePattern.TITLE,
                GeneratedCandidateKind.CANONICAL_CASE, true, true)
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration("london", listOf(word), CandidateCompletion.VALID_WORD, true, null, 1, 1))))
            if (automatic) controller.typeText(" ", policy, keyboard,
                autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { true }
            else controller.selectCandidate(controller.candidateViewState.candidates.filterIsInstance<CandidateUiItem.Correction>().single().id) { true }
            val attempt = observer.events.last { it.reason in setOf(DiagnosticReason.AUTO_REPLACE, DiagnosticReason.CORRECTION) }
            assertEquals(DiagnosticSource.CANONICAL_CASE, attempt.source)
        }
    }

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
        assertTrue(observer.has(DiagnosticKind.RANKING, DiagnosticReason.CANCELLED))
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
                if (code == ScoringCode.OK) DiagnosticReason.ABSTAINED else DiagnosticReason.CANCELLED,
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
                if (code == ScoringCode.OK) DiagnosticReason.ABSTAINED else DiagnosticReason.CANCELLED,
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
