package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.quality.*
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticText
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnostics
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingModel
import java.lang.reflect.Proxy
import org.junit.Assert.*
import org.junit.Test

/** Real owner/executor with an independent editor document. Synthetic quality admission only. */
class CorrectionBoundaryTest {
    @Test fun `accepted palette boundary allows whole next word without retaining previous context`() {
        val f = Fixture()
        f.raw("teh")
        assertEquals(TypingTextResult.HANDLED, f.controller.typeIsolatedText("😀", f.execute))
        assertEquals("teh😀", f.document)
        assertEquals("", f.controller.state.contextText)
        f.raw("teh"); f.publishCommon("the")
        assertNotNull(f.controller.spaceReplacementCandidateId(KeyboardLanguage.ENGLISH))
        f.type(" ")
        assertEquals("teh😀the ", f.document)
        assertTrue(f.calls.none { it.startsWith("get") })
    }

    @Test fun `palette boundary proof is revoked by invalidation external cursor or deletion outside context`() {
        for (cause in listOf("invalidate", "cursor", "delete")) {
            val f = Fixture()
            f.synchronous = true
            f.raw("old")
            assertEquals(TypingTextResult.HANDLED, f.controller.typeIsolatedText("😀", f.execute))
            when (cause) {
                "invalidate" -> f.controller.invalidate(f.execute)
                "cursor" -> { f.controller.updateSelection(1, 1, -1, -1, f.execute); f.caret = 1 }
                "delete" -> {
                    assertEquals(TypingTextResult.BYPASS, f.controller.deletePrevious(f.execute))
                    // The service delegates this deletion to the editor, then receives its actual caret.
                    f.document = "old"; f.caret = 3
                    f.controller.updateSelection(3, 3, -1, -1, f.execute)
                }
            }
            f.raw("teh")
            assertTrue("Fresh candidate ownership after $cause", f.controller.canRequestCandidates)
            f.publishCommon("the")
            assertNull(f.controller.spaceReplacementCandidateId(KeyboardLanguage.ENGLISH))
        }
    }

    @Test fun `model ready and late corrections retain next word Undo but never refinement authority`() {
        for (late in listOf(false, true)) {
            val f = Fixture(modelOnly = true, refinement = true, refinementQualified = true)
            f.controller.configureFeatures(DiagnosticFeature.VISIBLE_UNDO.bit, DiagnosticFeature.VISIBLE_UNDO.bit)
            val input = if (late) f.pendingSpace() else {
                f.raw("helllo"); f.publish("hello"); f.controller.beginModelRanking(1)!!
            }
            val reply = ScoringReply(input.token, ScoringCode.OK, 0,
                listOf(NumericScore(0, -20.0, 1), NumericScore(1, -1.0, 1)))
            if (late) assertTrue(f.controller.acceptSpaceCorrection(reply, f.execute))
            else { assertTrue(f.controller.acceptModelRanking(reply)); f.type(" ") }
            assertEquals("hello ", f.document)
            f.raw("w")
            assertFalse(f.controller.canRefinePreviousWord)
            assertNull(f.controller.beginPreviousWordRefinement(2))
            val undo = f.controller.candidateViewState.candidates.filterIsInstance<
                io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single()
            assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
            assertEquals("helllo w", f.document)
        }
    }

    @Test fun `late canonical replies do not open a new automatic correction source`() {
        val f = Fixture(qualified = true, refinement = true)
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.controller.configureFeatures(DiagnosticFeature.VISIBLE_UNDO.bit, DiagnosticFeature.VISIBLE_UNDO.bit)
        f.raw("москва")
        val reply = f.pendingCanonicalSpace("Москва")
        assertFalse(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
        assertEquals("москва ", f.document)
        f.raw("д")
        assertFalse(f.controller.canRefinePreviousWord)
        assertNull(f.controller.beginPreviousWordRefinement(2))
        assertTrue(f.controller.candidateViewState.candidates.none { it is
            io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo })
        assertEquals("москва д", f.document)
    }

    @Test fun `canonical correction retains next word Undo without refinement authority`() {
        val f = Fixture(qualified = true, refinement = true)
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.controller.configureFeatures(DiagnosticFeature.VISIBLE_UNDO.bit, DiagnosticFeature.VISIBLE_UNDO.bit)
        f.raw("москва"); f.publishCanonical("Москва", unambiguous = true)
        f.type(" "); assertEquals("Москва ", f.document)
        f.raw("д")
        assertFalse(f.controller.canRefinePreviousWord)
        assertNull(f.controller.beginPreviousWordRefinement(1))
        val undo = f.controller.candidateViewState.candidates.filterIsInstance<
            io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single()
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
        assertEquals("москва д", f.document)
    }

    @Test fun `long editor session learns phrases and inserts continuation only after current tap`() {
        val f = Fixture()
        val language = KeyboardLanguage.ENGLISH
        val model = PersonalTypingModel { word, lang -> lang == language && word in setOf("world", "see", "you", "soon") }
        f.controller.setPersonalization(object : TypingPersonalization {
            override fun committed(prefix: String, word: String, retypedFrom: String?, language: KeyboardLanguage) =
                model.recordPhrase(prefix, word, language)
            override fun continuations(context: String, language: KeyboardLanguage) = model.suggestions(context, language).map { it.text }
        }, language)
        val session = f.controller.state.sessionId
        repeat(100) { f.type("world"); f.type(" ") }
        repeat(3) { for (word in listOf("see", "you", "soon")) { f.type(word); f.type(" ") } }
        f.type("see"); f.type(" "); f.type("you"); f.type(" ")
        val before = "world ".repeat(100) + "see you soon ".repeat(3) + "see you "
        assertEquals(before, f.document)
        assertEquals(session, f.controller.state.sessionId)
        assertTrue(f.controller.state.enabled)
        assertTrue(f.controller.state.contextText.length > PersonalTypingModel.MAX_CONTEXT_CHARS)
        val continuation = f.controller.candidateViewState.candidates.single()
        assertEquals("soon", continuation.text)
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(continuation.id, f.execute))
        assertEquals(before + "soon ", f.document)
        assertEquals(4, model.snapshot().phrases.single { it.prefix == "see you" && it.continuation == "soon" }.support)
        assertFalse(f.calls.any { it.startsWith("get") })
    }

    @Test fun `noun case revision needs its own qualification and admission and keeps exact undo`() {
        for (qualified in listOf(false, true)) for (admitted in listOf(false, true)) {
            val f = Fixture(nounCaseQualified = qualified)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val target = GeneratedCandidate("фотографию", "фотографию", "фотографию", KeyboardLanguage.RUSSIAN,
                false, 4, 100, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage, baselineWord: String?) =
                    io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice(target, nounCaseRevision = true)
                override fun nounCaseAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(admitted)
                // Other sources deliberately admit: this source must not borrow their authority.
                override fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(true)
                override fun contextualAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(true)
            }, KeyboardLanguage.RUSSIAN)
            f.raw("показал"); f.type(" "); f.raw("фотографие")
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
            val pool = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(target), 1, 1)
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(target), CandidateCompletion.COMPLETE,
                    false, null, 1, 1, jointSearch = pool, jointEvaluated = true))))
            f.type(" ")
            assertEquals(if (qualified && admitted) "показал фотографию " else "показал фотографие ", f.document)
            if (qualified && admitted) { f.undo(); assertEquals("показал фотографие", f.document) }
        }
    }

    @Test fun `infinitive revision needs its own qualification and admission and keeps exact undo`() {
        for (qualified in listOf(false, true)) for (admitted in listOf(false, true)) {
            val f = Fixture(grammarRevisionQualified = qualified)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val target = GeneratedCandidate("научиться", "научиться", "научиться", KeyboardLanguage.RUSSIAN,
                false, 4, 100, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage, baselineWord: String?) =
                    io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice(target, grammarRevision = true)
                override fun grammarRevisionAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(admitted)
                // Other sources deliberately admit: this source must not borrow their authority.
                override fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(true)
                override fun contextualAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(true)
            }, KeyboardLanguage.RUSSIAN)
            f.raw("надо"); f.type(" "); f.raw("научищься")
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
            val pool = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(target), 1, 1)
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(target), CandidateCompletion.COMPLETE,
                    false, null, 1, 1, jointSearch = pool, jointEvaluated = true))))
            f.type(" ")
            assertEquals(if (qualified && admitted) "надо научиться " else "надо научищься ", f.document)
            if (qualified && admitted) { f.undo(); assertEquals("надо научищься", f.document) }
        }
    }

    @Test fun `known original may offer explicit neighbours without ever replacing on Space`() {
        for (staged in listOf(false, true)) {
        val f = Fixture()
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.raw("нуден")
        val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
        val candidate = GeneratedCandidate("нужен", "нужен", "нужен", KeyboardLanguage.RUSSIAN,
            false, 4, 1000000, 1, EditFeatures(.75, 0, 0.0), 0, CasePattern.LOWER,
            GeneratedCandidateKind.PUBLIC_AUGMENTED)
        val original = CandidateGeneration("нуден", emptyList(), CandidateCompletion.VALID_WORD, true, null, 1, 0)
        val manual = original.copy(alternatives = listOf(candidate), completion = CandidateCompletion.COMPLETE, isValidWord = false)
        assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
            request.requestId, original, manualGeneration = if (staged) null else manual, isFinal = !staged)))
        if (staged) assertTrue(f.controller.acceptRecoveryCandidates(LocalCandidateReply(request.sessionId,
            request.revision, request.requestId, original.copy(jointEvaluated = true,
                jointSearch = LocalSearchEvidence(CandidateCompletion.VALID_WORD, emptyList(), 0, 0)),
            manualGeneration = manual, stage = CandidateStage.RECOVERY)))
        assertTrue(f.controller.candidateViewState.candidates.any { it.text == "нужен" })
        assertNull(f.controller.spaceReplacementCandidateId(KeyboardLanguage.RUSSIAN))
        assertNull(f.controller.beginModelRanking(2))
        val id = f.controller.candidateViewState.candidates.single { it.text == "нужен" }.id
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(id, f.execute))
        assertEquals("нужен", f.document)
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(f.controller.originalCandidateId!!, f.execute))
        assertEquals("нуден", f.document)
        f.type(" ")
        assertEquals("нуден ", f.document)
        assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `reviewed context owns admission qualification visible winner and exact undo`() {
        for (qualified in listOf(false, true)) for (admitted in listOf(false, true)) {
            val f = Fixture(wordContextQualified = qualified)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val target = GeneratedCandidate("новый", "новый", "новый", KeyboardLanguage.RUSSIAN,
                false, 4, 1, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage, baselineWord: String?) =
                    io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice(target, wordContext = true)
                override fun wordContextAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(admitted)
            }, KeyboardLanguage.RUSSIAN)
            f.raw("нужен"); f.type(" "); f.raw("новй")
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
            val pool = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(target), 1, 1)
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(target), CandidateCompletion.COMPLETE,
                    false, null, 1, 1, jointSearch = pool, jointEvaluated = true))))
            if (qualified && admitted) assertEquals("новый", f.controller.candidateViewState.candidates[1].text)
            f.type(" ")
            assertEquals(if (qualified && admitted) "нужен новый " else "нужен новй ", f.document)
            if (qualified && admitted) { f.undo(); assertEquals("нужен новй", f.document) }
        }
    }

    @Test fun `rescue never borrows primary joint qualification and preserves exact undo`() {
        for (qualified in listOf(false, true)) {
            val f = Fixture(rescueQualified = qualified)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val target = GeneratedCandidate("словарь", "словарь", "словарь", KeyboardLanguage.RUSSIAN,
                false, 4, 1, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage, baselineWord: String?) =
                    io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice(target, rescue = true)
                override fun rescueAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(true)
            }, KeyboardLanguage.RUSSIAN)
            f.raw("сдоварь")
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
            val pool = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(target), 1, 1)
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(target), CandidateCompletion.COMPLETE,
                    false, null, 1, 1, jointSearch = pool, jointEvaluated = true))))
            f.type(" ")
            assertEquals(if (qualified) "словарь " else "сдоварь ", f.document)
            if (qualified) { f.undo(); assertEquals("сдоварь", f.document) }
        }
    }
    @Test fun `qualified compact public winner is separate from baseline and uses its own admission`() {
        fun publishCompact(fixture: Fixture, admitted: Boolean) {
            fixture.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            fixture.controller.setPersonalization(object : TypingPersonalization {
                override fun compactAutomaticCandidate(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage) = generation.compactAlternatives.singleOrNull()
                override fun compactAutomaticDecision(generation: CandidateGeneration,
                    candidate: GeneratedCandidate, language: KeyboardLanguage) =
                    AutomaticTypingDecision(admitted,
                        if (admitted) null else AutomaticAdmissionRefusal.NOT_QUALIFIED)
            }, KeyboardLanguage.RUSSIAN)
            fixture.raw("кармн")
            val request = checkNotNull(fixture.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN))
            val candidate = GeneratedCandidate("кармен", "кармен", "кармен", KeyboardLanguage.RUSSIAN,
                false, 2, 50_001, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER,
                GeneratedCandidateKind.PUBLIC_AUGMENTED)
            val generation = CandidateGeneration(request.token, emptyList(), CandidateCompletion.COMPLETE,
                false, null, 1, 0, LocalSearchEvidence(CandidateCompletion.COMPLETE, emptyList(), 1, 0),
                compactAlternatives = listOf(candidate))
            assertTrue(fixture.controller.acceptCandidates(LocalCandidateReply(request.sessionId,
                request.revision, request.requestId, generation)))
            assertEquals(listOf("кармн", "кармен"),
                fixture.controller.candidateViewState.candidates.map { it.text })
        }

        val accepted = Fixture()
        publishCompact(accepted, admitted = true)
        accepted.type(" ")
        assertEquals("кармен ", accepted.document)
        accepted.undo()
        assertEquals("кармн", accepted.document)

        val refused = Fixture()
        publishCompact(refused, admitted = false)
        refused.type(" ")
        assertEquals("кармн ", refused.document)
        assertNull(refused.controller.state.lastAutoEdit)
    }

    @Test fun `qualified joint winner outranks legacy choice and original veto cannot launch old model`() {
        for (originalWins in listOf(false, true)) {
            val f = Fixture()
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("пережодим")
            fun candidate(word: String) = GeneratedCandidate(word, word, word, KeyboardLanguage.RUSSIAN,
                false, 2, 1, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
            val legacy = candidate("переводим")
            val target = candidate("переходим")
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage, baselineWord: String?) = io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice(
                        if (originalWins) null else target)
                override fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(true)
            }, KeyboardLanguage.RUSSIAN)
            // setPersonalization invalidates earlier requests; admit only the new owned request.
            val current = f.controller.beginCandidateRequest(2, KeyboardLanguage.RUSSIAN)!!
            val local = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(legacy), 1, 1)
            val joint = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(legacy, target), 1, 2)
            val generation = CandidateGeneration(current.token, listOf(legacy), CandidateCompletion.COMPLETE,
                false, null, 1, 1, local, jointSearch = joint, jointEvaluated = true)
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(current.sessionId, current.revision, current.requestId, generation)))
            assertFalse(f.controller.canRequestModelRanking)
            assertNull(f.controller.beginModelRanking(3))
            f.type(" ")
            assertEquals(if (originalWins) "пережодим " else "переходим ", f.document)
            if (!originalWins) { f.undo(); assertEquals("пережодим", f.document) }
        }
    }

    @Test fun `joint decision has independent qualification and never borrows baseline admission`() {
        val f = Fixture(qualified = false)
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.controller.setPersonalization(object : TypingPersonalization {
            override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
                language: KeyboardLanguage, baselineWord: String?) = io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice(
                    generation.jointSearch.alternatives.singleOrNull())
            override fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                language: KeyboardLanguage) = AutomaticTypingDecision(true)
        }, KeyboardLanguage.RUSSIAN)
        f.raw("нудо")
        val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
        val target = GeneratedCandidate("надо", "надо", "надо", KeyboardLanguage.RUSSIAN,
            false, 2, 1, 1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
        val generation = CandidateGeneration("нудо", listOf(target), CandidateCompletion.COMPLETE,
            false, null, 1, 1, jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(target), 1, 1), jointEvaluated = true)
        assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId, generation)))
        f.type(" ")
        assertEquals("нудо ", f.document)
    }

    @Test fun `short public manual pool is selectable but never an automatic replacement`() {
        for (pick in listOf(false, true)) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("кнь")
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
            val baseline = CandidateGeneration("кнь", emptyList(), CandidateCompletion.COMPLETE, false, null, 1, 0)
            val word = GeneratedCandidate("конь", "конь", "конь", KeyboardLanguage.RUSSIAN,
                false, 2, 50_001, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER,
                GeneratedCandidateKind.PUBLIC_AUGMENTED)
            val manual = baseline.copy(alternatives = listOf(word), verifiedTerminals = 1)
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
                request.requestId, baseline, manual)))
            assertEquals(listOf("кнь", "конь"), f.controller.candidateViewState.candidates.map { it.text })
            assertNull(f.controller.spaceReplacementCandidateId(KeyboardLanguage.RUSSIAN))
            if (pick) {
                val candidate = f.controller.candidateViewState.candidates.last()
                assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(candidate.id, f.execute))
                assertEquals("конь", f.document)
            } else {
                f.type(" ")
                assertEquals("кнь ", f.document)
                assertNull(f.controller.state.lastAutoEdit)
            }
        }
    }

    @Test fun `late visible Undo expires after eight seconds and stale action cannot edit`() {
        val f = Fixture(qualified = null)
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        val flag = DiagnosticFeature.VISIBLE_UNDO.bit
        f.controller.configureFeatures(flag, flag)
        val reply = f.pendingLocalSpace("зочу", "хочу")
        f.controller.retainLocalSpaceAcrossNextWord { f.raw("до") }
        assertTrue(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
        val id = f.controller.candidateViewState.candidates.filterIsInstance<
            io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single().id
        f.now = 8_000_000_000
        assertTrue(f.controller.candidateViewState.candidates.any { it.id == id })
        f.now++
        assertTrue(f.controller.candidateViewState.candidates.none { it is
            io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo })
        f.calls.clear()
        assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
        assertTrue(f.calls.isEmpty())
        assertEquals("хочу до", f.document)
    }

    @Test fun `automatic preview rejects an unknown editor prefix and a stale word`() {
        for (initial in listOf("", "outside@")) {
            val f = Fixture(qualified = null, initial = initial)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("зочу"); f.publishCommon("хочу")
            val id = f.controller.spaceReplacementCandidateId(KeyboardLanguage.RUSSIAN)
            assertEquals(initial.isEmpty(), id != null)
            f.raw("а")
            assertNull(f.controller.spaceReplacementCandidateId(KeyboardLanguage.RUSSIAN))
        }
    }

    @Test fun `late local ranking uses the preceding context rather than the next word`() {
        for (next in listOf("", "до")) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val observed = mutableListOf<String>()
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun compactAutomaticCandidate(context: String, generation: CandidateGeneration,
                    language: KeyboardLanguage): GeneratedCandidate? {
                    observed += context
                    return null
                }
            }, KeyboardLanguage.RUSSIAN)
            f.raw("я ")
            val reply = f.pendingLocalSpace("зочу", "хочу")
            if (next.isNotEmpty()) f.controller.retainLocalSpaceAcrossNextWord { f.raw(next) }
            assertTrue(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
            assertEquals(listOf("я "), observed)
            assertEquals("я хочу $next", f.document)
        }
    }

    @Test fun `late correction learns only an explicit Undo and not ordinary next word deletion`() {
        for (explicitUndo in listOf(false, true)) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val rejected = mutableListOf<Pair<String, String>>()
            val positive = mutableListOf<String>()
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun rejected(original: String, replacement: String, language: KeyboardLanguage) {
                    rejected += original to replacement
                }
                override fun accepted(original: String, replacement: String, language: KeyboardLanguage) { positive += replacement }
                override fun confirmed(word: String, language: KeyboardLanguage) { positive += word }
            }, KeyboardLanguage.RUSSIAN)
            val flag = DiagnosticFeature.VISIBLE_UNDO.bit
            f.controller.configureFeatures(flag, flag)
            val reply = f.pendingLocalSpace("зочу", "хочу")
            f.controller.retainLocalSpaceAcrossNextWord { f.raw("до") }
            assertTrue(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
            assertTrue(rejected.isEmpty()); assertTrue(positive.isEmpty())
            if (explicitUndo) {
                val undo = f.controller.candidateViewState.candidates.filterIsInstance<
                    io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single()
                assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
                assertEquals(listOf("зочу" to "хочу"), rejected)
                assertEquals("зочу до", f.document)
            } else {
                f.undo()
                assertEquals("хочу д", f.document)
                assertTrue(rejected.isEmpty())
            }
            assertTrue(positive.isEmpty())
        }
    }

    @Test fun `late local replacement preserves real editor next word caret and visible Undo`() {
        for (synchronous in listOf(false, true)) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.synchronous = synchronous
            val flag = DiagnosticFeature.VISIBLE_UNDO.bit
            f.controller.configureFeatures(flag, flag)
            f.raw("я ")
            val reply = f.pendingLocalSpace("автокрекция", "автокоррекция")
            f.now = 60_000_000
            f.controller.retainLocalSpaceAcrossNextWord { f.raw("до") }
            assertTrue(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
            assertEquals("я автокоррекция до", f.document)
            assertEquals(f.document.length, f.caret)
            assertEquals(f.document.length - 3, f.composingStart)
            assertNull(f.controller.state.lastAutoEdit)
            val undo = f.controller.candidateViewState.candidates.filterIsInstance<
                io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single()
            assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
            assertEquals("я автокрекция до", f.document)
            assertEquals(f.document.length, f.caret)
            assertEquals(f.document.length - 3, f.composingStart)
        }
    }

    @Test fun `late local response refuses non-letter edits policy changes and exact deadline`() {
        for (action in listOf<(Fixture) -> Unit>(
            { it.controller.retainLocalSpaceAcrossNextWord { it.raw(".") } },
            { it.controller.retainLocalSpaceAcrossNextWord { it.raw(" ") } },
            { it.controller.retainLocalSpaceAcrossNextWord { it.raw("1") } },
            { it.controller.retainLocalSpaceAcrossNextWord { it.undo() } },
            { it.controller.retainLocalSpaceAcrossNextWord {
                it.controller.configureFeatures(DiagnosticFeature.QUALITY_METRICS.bit, DiagnosticFeature.QUALITY_METRICS.bit)
                it.raw("д")
            } },
            { it.now = 250_000_000; it.controller.retainLocalSpaceAcrossNextWord { it.raw("д") } },
            { it.controller.updateSelection(0, 0, -1, -1, it.execute) })) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val reply = f.pendingLocalSpace("зочу", "хочу")
            action(f)
            f.calls.clear()
            assertFalse(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
            assertTrue(f.calls.isEmpty())
        }
    }

    @Test fun `late local replacement aborts on editor failure without reading or deleting text`() {
        for (failure in listOf("setComposingRegion", "commitText")) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            val reply = f.pendingLocalSpace("зочу", "хочу")
            f.controller.retainLocalSpaceAcrossNextWord { f.raw("до") }
            f.fail = failure
            assertFalse(f.controller.acceptLocalSpaceCorrection(reply, f.execute))
            assertEquals("зочу до", f.document)
            assertFalse(f.controller.state.enabled)
        }
    }

    @Test fun `reviewed Russian typo corrects without model and Undo restores exact input`() {
        for ((original, target) in listOf("зочу" to "хочу", "Зочу" to "Хочу",
            "расмотри" to "рассмотри", "Расмотри" to "Рассмотри")) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw(original); f.publishCommon(target.lowercase(java.util.Locale.ROOT))
            assertEquals(listOf(original, target), f.controller.candidateViewState.candidates.map { it.text })
            assertFalse(f.controller.canRequestModelRanking)
            f.type(" ")
            assertEquals("$target ", f.document)
            f.undo()
            assertEquals(original, f.document)
            f.type(" ")
            assertEquals("$original ", f.document)
        }
    }

    @Test fun `short Russian confusion preserves suggestion modes protected prefixes and editor policy`() {
        for (mode in listOf(AutocorrectionMode.OFF, AutocorrectionMode.SUGGESTIONS)) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN); f.mode = mode
            f.raw("зочу"); f.publishCommon("хочу"); f.type(" ")
            assertEquals("зочу ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
        }
        for (prefix in listOf("@", "/", ".", "x=")) {
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw(prefix); f.raw("зочу"); f.publishCommon("хочу"); f.type(" ")
            assertEquals(prefix + "зочу ", f.document)
        }
        val f = Fixture(qualified = null)
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.raw("зочу"); f.publishCommon("хочу")
        f.policy = f.policy.copy(inputPolicy = InputPolicy.SENSITIVE)
        f.type(" ")
        assertEquals("зочу ", f.document)
        assertNull(f.controller.state.lastAutoEdit)
    }

    @Test fun `Russian correction requires known whole token even when candidates are ready`() {
        for (initial in listOf("", "outside@")) {
            val f = Fixture(initial = initial)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("пережодим"); f.publish("переходим"); f.type(" ")
            assertEquals(if (initial.isEmpty()) "переходим " else initial + "пережодим ", f.document)
            // An explicit Rune space establishes a boundary even after an unknown editor prefix.
            f.raw("пережодим"); f.publish("переходим"); f.type(" ")
            assertEquals((if (initial.isEmpty()) "переходим " else initial + "пережодим ") + "переходим ", f.document)
        }
    }

    @Test fun `experimental context is owned and contains only preceding acknowledged text`() {
        val f = Fixture()
        assertNull(f.controller.experimentalInput())
        f.raw("hello "); f.raw("worl")
        val input = checkNotNull(f.controller.experimentalInput())
        assertEquals("hello ", input.context)
        assertEquals("worl", input.word)
        assertEquals("ExperimentalTypingInput(redacted)", input.toString())
        f.controller.awaitEditorSelection(f.execute)
        assertNull(f.controller.experimentalInput())
    }

    @Test fun `experimental scoring sees context but cannot change the original or editor`() {
        val f = Fixture()
        val observed = mutableListOf<String>()
        f.controller.setPersonalization(object : TypingPersonalization {
            override fun contextualPreference(context: String, original: String, candidate: GeneratedCandidate,
                language: KeyboardLanguage): Double {
                observed.add(context)
                return if (candidate.text == "help") 10.0 else 0.0
            }
        }, KeyboardLanguage.ENGLISH)
        f.raw("say "); f.raw("hellp"); f.publishMany("hello", "help")
        val choices = f.controller.candidateViewState.candidates
        assertEquals("hellp", choices.first().text)
        assertEquals("help", choices[1].text)
        assertTrue(observed.isNotEmpty()); assertTrue(observed.all { it == "say " })
        assertEquals("say hellp", f.document)
    }

    @Test fun `protection resolves only live word ids and profile transitions invalidate them`() {
        val flag = DiagnosticFeature.PROTECTED_WORDS.bit
        val f = Fixture()
        f.controller.configureFeatures(flag, flag)
        f.raw("teh"); f.publish("the")
        val items = f.controller.candidateViewState.candidates
        assertEquals("teh", f.controller.wordForProtection(items[0].id))
        assertEquals("the", f.controller.wordForProtection(items[1].id))
        assertEquals("teh", f.document)
        assertNull(f.controller.wordForProtection("invented"))
        f.controller.configureFeatures(flag, flag, 1)
        assertNull(f.controller.wordForProtection(items[1].id))
        f.controller.configureFeatures(0, 0)
        assertNull(f.controller.wordForProtection(f.controller.candidateViewState.candidates.first().id))
    }

    @Test fun `profile code is logged on configuration and ordinary editor outcomes`() {
        val events = mutableListOf<io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent>()
        val f = Fixture()
        f.controller.setDiagnostics(object : io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnostics {
            override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) {}
            override fun invalidate() {}
            override fun record(event: io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent,
                text: (() -> io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticText)?) { events.add(event) }
        })
        val flag = DiagnosticFeature.APP_PROFILES.bit
        f.controller.configureFeatures(flag, flag, 2)
        f.raw("hello")
        assertTrue(events.isNotEmpty())
        assertTrue(events.all { it.typingProfile == 2 })
        assertTrue(events.any { it.kind == io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind.EDITOR })
    }

    @Test fun `word split join and abbreviation suggestions change only the current owned suffix on tap`() {
        for ((source, replacement, kind) in listOf(
            Triple("незнаю", "не знаю", TypingToolKind.WORD_BOUNDARY),
            Triple("при вет", "привет", TypingToolKind.WORD_BOUNDARY),
            Triple("щб", "щас буду", TypingToolKind.ABBREVIATION))) {
            val f = Fixture(); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.controller.setTypingTools(TypingTools { context, _, _ ->
                if (context.endsWith(source)) listOf(TypingToolSuggestion(source, replacement, kind)) else emptyList()
            })
            f.raw("Привет "); f.raw(source)
            val id = f.controller.candidateViewState.candidates.filterIsInstance<io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Tool>().single().id
            assertEquals("Привет $source", f.document)
            assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(id, f.execute))
            assertEquals("Привет $replacement", f.document)
            assertNull(f.controller.state.composing)
            assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
        }
    }

    @Test fun `finished phrase review uses real policy and exact owned region`() {
        val f = Fixture(); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.controller.setPersonalizationLanguage(KeyboardLanguage.RUSSIAN)
        f.controller.setTypingTools(TypingTools { context, _, language ->
            io.github.mesteriis.rune.keyboard.smarttyping.texttools.PhraseReviewPolicy.suggest(context, language)?.let {
                listOf(TypingToolSuggestion(it.sourceSuffix, it.replacementSuffix, TypingToolKind.PHRASE_REVIEW))
            }.orEmpty()
        })
        f.raw("Я идут домой.")
        val candidate = f.controller.candidateViewState.candidates.single()
        assertEquals("Я иду домой.", candidate.text)
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(candidate.id, f.execute))
        assertEquals("Я иду домой.", f.document)
    }

    @Test fun `tool suggestions reject unknown boundary stale disabled and failed editor transactions`() {
        for (prefix in listOf("@", "/", "x=")) {
            val f = Fixture(); f.controller.setTypingTools(TypingTools { _, _, _ ->
                listOf(TypingToolSuggestion("щб", "щас буду", TypingToolKind.ABBREVIATION)) })
            f.raw(prefix); f.raw("щб")
            assertTrue(f.controller.candidateViewState.candidates.none { it is io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Tool })
        }
        for (invalidate in listOf<(Fixture) -> Unit>(
            { it.controller.clearCandidates() }, { it.controller.setTypingTools(NoTypingTools) },
            { it.controller.endSession() }, { it.controller.updateSelection(0, 0, -1, -1, it.execute) })) {
            val f = Fixture(); f.controller.setTypingTools(TypingTools { _, _, _ ->
                listOf(TypingToolSuggestion("щб", "щас буду", TypingToolKind.ABBREVIATION)) })
            f.raw("щб"); val id = f.controller.candidateViewState.candidates.last().id
            invalidate(f)
            assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
        }
        val f = Fixture(); f.controller.setTypingTools(TypingTools { _, _, _ ->
            listOf(TypingToolSuggestion("щб", "щас буду", TypingToolKind.ABBREVIATION)) })
        f.raw("щб"); val id = f.controller.candidateViewState.candidates.last().id
        f.fail = "commitText"
        assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
        assertEquals("щб", f.document)
        assertFalse(f.controller.state.enabled)
    }

    @Test fun `visible undo is explicit expires with edit and toggle without disabling backspace undo`() {
        val flag = io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature.VISIBLE_UNDO.bit
        val f = Fixture(); f.controller.configureFeatures(flag, flag)
        f.raw("helllo"); f.publish("hello"); f.type(" ")
        val undo = f.controller.candidateViewState.candidates.single()
        assertTrue(undo is io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo)
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
        assertEquals("helllo", f.document)
        assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(undo.id, f.execute))
        val hidden = Fixture(); hidden.controller.configureFeatures(flag, flag)
        hidden.raw("helllo"); hidden.publish("hello"); hidden.type(" ")
        val stale = hidden.controller.candidateViewState.candidates.single().id
        hidden.controller.configureFeatures(0, 0)
        assertEquals(TypingTextResult.REJECTED, hidden.controller.selectCandidate(stale, hidden.execute))
        hidden.undo(); assertEquals("helllo", hidden.document)
    }

    @Test fun `diagnostics session changes carry configured and eligible feature states`() {
        val f = Fixture()
        val events = mutableListOf<io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent>()
        f.controller.setDiagnostics(object : io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnostics {
            override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) {}
            override fun invalidate() {}
            override fun record(event: io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent,
                text: (() -> io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticText)?) { events += event }
        })
        val flag = io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature.ABBREVIATIONS.bit
        f.controller.configureFeatures(flag, flag)
        f.controller.startSession(EditorContext.from(1, 0), 0, 0)
        f.type("a")
        val start = events.last { it.kind == io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind.SESSION }
        assertEquals(flag, start.configuredFeatures)
        assertEquals(flag, start.effectiveFeatures)
        val editorEvents = events.filter { it.kind == io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind.EDITOR }
        assertTrue(editorEvents.isNotEmpty())
        assertTrue(editorEvents.all { it.configuredFeatures == flag && it.effectiveFeatures == flag })
        f.controller.configureFeatures(flag, 0)
        assertEquals(flag, events.last().configuredFeatures)
        assertEquals(0, events.last().effectiveFeatures)
        f.raw("b")
        assertEquals(flag, events.last().configuredFeatures)
        assertEquals(0, events.last().effectiveFeatures)
        f.controller.configureFeatures(flag, flag)
        f.controller.closeDiagnosticsAdmission()
        f.raw("c")
        val closedOutcome = events.last { it.kind == io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind.EDITOR }
        assertEquals(flag, closedOutcome.configuredFeatures)
        assertEquals(0, closedOutcome.effectiveFeatures)
        f.controller.startSession(EditorContext.from(129, 0), 0, 0)
        assertEquals(0, events.last().effectiveFeatures)
    }


    private fun quality(f: Fixture): QualityModel {
        val model = QualityModel().apply { configure(true, true, true) }
        f.controller.setQualityRecorder(object : QualityRecorder {
            override fun record(event: QualityEvent) { model.record(event) }
            override fun compare(revision: Long, source: String, primaryChoice: String, experimentalChoice: String) {
                model.compare(revision, source, primaryChoice, experimentalChoice)
            }
            override fun explicitChoice(revision: Long, chosen: String) { model.explicitChoice(revision, chosen) }
            override fun invalidatePending() { model.invalidatePending() }
        })
        val flags = DiagnosticFeature.SHADOW_COMPARISON.bit or DiagnosticFeature.AUTO_CORRECTION.bit
        f.controller.configureFeatures(flags, flags)
        return model
    }

    @Test fun `quality comparison cannot label a later word or cursor-owned fragment`() {
        for (boundary in listOf("space", "cursor", "settings", "new-letter")) {
            val f = Fixture(); val model = quality(f)
            f.raw("helllo"); f.publish("hello")
            when (boundary) {
                "space" -> { f.mode = AutocorrectionMode.SUGGESTIONS; f.type(" "); f.raw("hello") }
                "cursor" -> { f.controller.updateSelection(2, 2, 0, 6, f.execute); f.raw("hello") }
                "settings" -> f.controller.clearCandidates()
                else -> f.raw("o")
            }
            assertTrue(f.controller.selectOriginal(f.controller.originalCandidateId!!))
            assertEquals(boundary, 0L, model.snapshot().shadow.drop(2).sum())
        }
    }

    @Test fun `only immediate undo or backed retype labels the compared word`() {
        val undo = Fixture(); val undoModel = quality(undo)
        undo.raw("helllo"); undo.publish("hello"); undo.type(" "); undo.undo()
        assertEquals(1L, undoModel.snapshot()[ShadowResult.EXPLICIT_NEITHER])
        val retype = Fixture(); val retypeModel = quality(retype)
        retype.raw("hellp"); retype.publish("hello"); retype.undo(); retype.type("o"); retype.type(" ")
        assertEquals(1L, retypeModel.snapshot().shadow.drop(2).sum())
        val unrelated = Fixture(); val unrelatedModel = quality(unrelated)
        unrelated.raw("helllo"); unrelated.publish("hello"); unrelated.type(" ")
        unrelated.raw("hellp"); unrelated.undo(); unrelated.type("o"); unrelated.type(" ")
        assertEquals(0L, unrelatedModel.snapshot().shadow.drop(2).sum())
        val finished = Fixture(); val finishedModel = quality(finished)
        finished.raw("hellp"); finished.publish("hello"); finished.undo(); finished.type("o")
        finished.controller.finishComposition(finished.execute)
        assertEquals(0L, finishedModel.snapshot().shadow.drop(2).sum())
    }

    @Test fun `only an acknowledged changed manual retype increments its numeric quality counter`() {
        val changed = Fixture(); val changedModel = quality(changed)
        changed.raw("hellp"); changed.undo(); changed.type("o"); changed.type(" ")
        assertEquals("hello ", changed.document)
        assertEquals(1L, changedModel.snapshot()[QualityEvent.MANUAL_RETYPE])

        val unchanged = Fixture(); val unchangedModel = quality(unchanged)
        unchanged.raw("hello"); unchanged.undo(); unchanged.type("o"); unchanged.type(" ")
        assertEquals("hello ", unchanged.document)
        assertEquals(0L, unchangedModel.snapshot()[QualityEvent.MANUAL_RETYPE])
    }

    @Test fun `qualified model choice is the primary with one comparison before manual pick or late undo`() {
        val f = Fixture(modelOnly = true); val model = quality(f)
        f.raw("helllo"); f.publish("hello")
        val request = f.controller.beginModelRanking(1)!!
        assertTrue(f.controller.acceptModelRanking(winningReply(request)))
        repeat(3) { f.controller.candidateViewState }
        val candidate = f.controller.candidateViewState.candidates[1]
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(candidate.id, f.execute))
        assertEquals(1L, model.snapshot()[ShadowResult.EXPLICIT_BOTH])
        assertEquals(1L, model.snapshot().shadow.take(2).sum())
        val late = Fixture(modelOnly = true); val lateModel = quality(late)
        val lateRequest = late.pendingSpace()
        assertTrue(late.controller.acceptSpaceCorrection(winningReply(lateRequest), late.execute))
        assertEquals("hello ", late.document)
        late.undo()
        assertEquals(1L, lateModel.snapshot().shadow.take(2).sum())
        assertEquals(1L, lateModel.snapshot()[ShadowResult.EXPLICIT_NEITHER])
    }

    @Test fun `disabled shadow does not evaluate its ranking or personalization`() {
        val f = Fixture()
        f.controller.setPersonalization(object : TypingPersonalization {
            override fun preference(original: String, candidate: String, language: KeyboardLanguage): Double =
                error("Shadow ranking must stay off")
            override fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
                language: KeyboardLanguage): Boolean = error("Shadow guard must stay off")
        }, KeyboardLanguage.ENGLISH)
        f.raw("helllo"); f.publish("hello")
    }

    private class PersonalEvents : TypingPersonalization {
        var allow = true
        val events = mutableListOf<String>()
        val committedPrefixes = mutableListOf<String>()
        var phrases = emptyList<String>()
        override fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage) = allow
        override fun accepted(original: String, replacement: String, language: KeyboardLanguage) {
            events.add("accept:$original:$replacement")
        }
        override fun rejected(original: String, replacement: String, language: KeyboardLanguage) {
            events.add("reject:$original:$replacement")
        }
        override fun confirmed(word: String, language: KeyboardLanguage) { events.add("confirm:$word") }
        override fun committed(prefix: String, word: String, retypedFrom: String?, language: KeyboardLanguage) {
            events.add("commit:$word:$retypedFrom")
            committedPrefixes.add(prefix)
        }
        override fun continuations(context: String, language: KeyboardLanguage) = phrases
    }

    @Test fun `personal veto preserves suggestions and prevents immediate and delayed replacements`() {
        val direct = Fixture(); val hook = PersonalEvents().apply { allow = false }
        direct.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
        direct.raw("helllo"); direct.publish("hello")
        assertEquals(listOf("helllo", "hello"), direct.controller.candidateViewState.candidates.map { it.text })
        assertEquals(direct.controller.originalCandidateId, direct.controller.candidateViewState.selectedCandidateId)
        direct.type(" "); assertEquals("helllo ", direct.document)
        val delayed = Fixture(modelOnly = true)
        delayed.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
        val request = delayed.pendingSpace()
        assertFalse(delayed.controller.acceptSpaceCorrection(winningReply(request), delayed.execute))
        assertEquals("helllo ", delayed.document)
    }

    @Test fun `specific admission vetoes reach immediate and delayed boundary diagnostics without replacement`() {
        val reasons = listOf(
            AutomaticAdmissionRefusal.TARGET_UNKNOWN to io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason.TARGET_UNKNOWN,
            AutomaticAdmissionRefusal.RIVAL_UNKNOWN to io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason.RIVAL_UNKNOWN,
            AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE to io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason.RESOURCE_UNAVAILABLE,
            AutomaticAdmissionRefusal.PERSONAL_VETO to io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason.PERSONAL_VETO,
            AutomaticAdmissionRefusal.PROTECTED_WORD to io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason.PROTECTED_WORD,
        )
        for ((refusal, expected) in reasons) for (late in listOf(false, true)) {
            val f = Fixture(modelOnly = late)
            val events = mutableListOf<io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent>()
            f.controller.setDiagnostics(object : io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnostics {
                override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
                override fun invalidate() = Unit
                override fun record(event: io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent,
                    text: (() -> io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticText)?) { events += event }
            })
            f.controller.setPersonalization(object : TypingPersonalization {
                override fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = false
                override fun automaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                    language: KeyboardLanguage) = AutomaticTypingDecision(false, refusal)
            }, KeyboardLanguage.ENGLISH)
            if (late) {
                val request = f.pendingSpace()
                events.clear()
                assertFalse(f.controller.acceptSpaceCorrection(winningReply(request), f.execute))
            } else {
                f.raw("helllo"); f.publish("hello")
                assertTrue(f.controller.candidateViewState.candidates.any { it.text == "hello" })
                events.clear()
                f.type(" ")
            }
            val boundary = events.single {
                it.kind == io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind.BOUNDARY
            }
            assertEquals("refusal=$refusal late=$late", expected, boundary.reason)
            assertEquals("helllo ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
            assertTrue(f.calls.none { it.startsWith("get") })
        }
    }

    @Test fun `generic deterministic ranking refusal keeps its observed local reason but model refusal stays authoritative`() {
        for (completeLocal in listOf(false, true)) for (useModel in listOf(false, true)) {
            val f = Fixture()
            val events = mutableListOf<DiagnosticEvent>()
            f.controller.setDiagnostics(object : TypingDiagnostics {
                override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
                override fun invalidate() = Unit
                override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) { events += event }
            })
            f.raw("helllo")
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.ENGLISH)!!
            val items = listOf("hello", "help", "held", "hero").map { word ->
                GeneratedCandidate(word, word, word, KeyboardLanguage.ENGLISH, false, 4, 1, 1,
                    EditFeatures(1.0, 0, 0.0), kotlin.math.abs(word.length - request.token.length), CasePattern.LOWER)
            }
            val local = if (completeLocal) LocalSearchEvidence(CandidateCompletion.COMPLETE, emptyList(), 1, 0)
                else LocalSearchEvidence.NONE
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
                request.requestId, CandidateGeneration(request.token, items, CandidateCompletion.COMPLETE,
                    false, null, 1, 4, local))))
            if (useModel) {
                val input = f.controller.beginModelRanking(1)!!
                assertTrue(f.controller.acceptModelRanking(ScoringReply(input.token, ScoringCode.OK, 0,
                    input.token.candidateIds.map { NumericScore(it, if (it == 1) -1.0 else -20.0, 1) })))
            }
            events.clear()
            f.type(" ")
            assertEquals("helllo ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
            val expected = when {
                useModel -> DiagnosticReason.NOT_QUALIFIED
                completeLocal -> DiagnosticReason.LOCAL_SEARCH_EMPTY
                else -> DiagnosticReason.SEARCH_INCOMPLETE
            }
            assertEquals("completeLocal=$completeLocal useModel=$useModel", expected,
                events.single { it.kind == DiagnosticKind.BOUNDARY }.reason)
            assertTrue(f.calls.none { it.startsWith("get") })
        }
    }

    @Test fun `specific joint refusal is not replaced by the earlier empty local search`() {
        val f = Fixture()
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.controller.setPersonalization(object : TypingPersonalization {
            override fun jointAutomaticEvaluation(context: String, generation: CandidateGeneration,
                language: KeyboardLanguage, baselineWord: String?) =
                io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionEvaluation(
                    refusal = io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionRefusal.RESOURCE_UNAVAILABLE)
        }, KeyboardLanguage.RUSSIAN)
        val events = mutableListOf<DiagnosticEvent>()
        f.controller.setDiagnostics(object : TypingDiagnostics {
            override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
            override fun invalidate() = Unit
            override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) { events += event }
        })
        f.raw("словоо")
        f.publishMany("слово", "слова", "словом", "словах")
        events.clear()
        f.type(" ")
        assertEquals("словоо ", f.document)
        assertEquals(DiagnosticReason.RESOURCE_UNAVAILABLE, events.single { it.kind == DiagnosticKind.BOUNDARY }.reason)
        assertNull(f.controller.state.lastAutoEdit)
    }

    @Test fun `only acknowledged manual choices train and stale choices never train`() {
        for (fails in listOf(false, true)) {
            val f = Fixture(); val hook = PersonalEvents()
            f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            f.raw("helllo"); f.publish("hello")
            val id = f.controller.candidateViewState.candidates[1].id
            if (fails) f.fail = "setComposingText"
            val result = f.controller.selectCandidate(id, f.execute)
            assertEquals(if (fails) TypingTextResult.REJECTED else TypingTextResult.HANDLED, result)
            assertEquals(if (fails) emptyList<String>() else listOf("accept:helllo:hello"), hook.events)
            val count = hook.events.size
            assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
            assertEquals(count, hook.events.size)
        }
    }

    @Test fun `undo teaches exact rejected pair but ordinary backspace teaches no rejection`() {
        val f = Fixture(); val hook = PersonalEvents()
        f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
        f.raw("helllo"); f.publish("hello"); f.type(" ")
        assertTrue(hook.events.isEmpty())
        f.undo()
        assertEquals(listOf("reject:helllo:hello"), hook.events)
        hook.events.clear(); f.undo(); assertTrue(hook.events.isEmpty())
    }

    @Test fun `manual retype emitted only after owned word completed and forgotten on context loss`() {
        val f = Fixture(); val hook = PersonalEvents()
        f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
        f.raw("hellp"); f.undo(); f.type("o")
        assertTrue(hook.events.isEmpty())
        f.type(" "); assertEquals(listOf("commit:hello:hellp"), hook.events)
        hook.events.clear(); f.raw("worle"); f.undo()
        f.controller.invalidate(f.execute)
        f.raw("world"); f.type(" ")
        assertEquals(listOf("commit:world:null"), hook.events)
    }

    @Test fun `automatic word boundaries discard retype evidence before the next word`() {
        for (boundary in listOf(" ", "\n", "send")) {
            val f = Fixture(); val hook = PersonalEvents()
            f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            f.raw("helllp"); f.undo(); f.type("o"); f.publish("hello")
            val result = if (boundary == "send") f.controller.prepareEditorAction(
                f.policy, f.keyboard, f.mode, f.execute) else f.type(boundary)
            assertEquals(TypingTextResult.HANDLED, result)
            assertTrue(hook.events.isEmpty())
            f.type("world"); f.type(" ")
            assertEquals(listOf("commit:world:null"), hook.events)
        }
    }

    @Test fun `late automatic acknowledgement and composition finish discard retype evidence`() {
        for (lateCorrection in listOf(false, true)) {
            val f = Fixture(modelOnly = true); val hook = PersonalEvents()
            f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            f.raw("helllp"); f.undo(); f.type("o")
            if (lateCorrection) {
                f.publish("hello")
                val request = f.controller.beginModelRanking(1)!!
                assertEquals(TypingTextResult.HANDLED,
                    f.controller.retainRankingAcrossSpace { f.raw(" ") })
                assertTrue(f.controller.acceptSpaceCorrection(winningReply(request), f.execute))
            } else {
                assertEquals(TypingTextResult.HANDLED,
                    f.controller.prepareEditorAction(f.policy, f.keyboard, f.mode, f.execute))
            }
            assertTrue(hook.events.isEmpty())
            f.type("world"); f.type(" ")
            assertEquals(listOf("commit:world:null"), hook.events)
        }
    }

    @Test fun `learning policy changes finish owned text and discard prior prefix and retype`() {
        for (wasEnabled in listOf(false, true)) {
            val f = Fixture(); val hook = PersonalEvents()
            f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            f.raw("earlier"); f.type(" "); f.raw("hellp"); f.undo()
            hook.events.clear(); hook.committedPrefixes.clear()
            val before = f.document
            assertTrue(f.controller.updatePersonalLearningPolicy(wasEnabled, !wasEnabled, f.execute))
            assertEquals(before, f.document)
            assertNull(f.controller.state.composing)
            assertEquals("", f.controller.state.contextText)
            assertTrue(hook.events.isEmpty())
            if (wasEnabled) {
                f.raw("disabled"); f.type(" ")
                assertTrue(f.controller.updatePersonalLearningPolicy(false, true, f.execute))
                hook.events.clear(); hook.committedPrefixes.clear()
            }
            f.type("world"); f.type(" ")
            assertEquals(listOf("commit:world:null"), hook.events)
            assertEquals(listOf(""), hook.committedPrefixes)
        }
    }

    @Test fun `unchanged learning policy preserves ownership and failed boundary cannot reuse it`() {
        val f = Fixture(); f.raw("hello")
        assertTrue(f.controller.updatePersonalLearningPolicy(true, true, f.execute))
        assertEquals("hello", f.controller.state.composing?.typedWord)
        f.fail = "finishComposingText"
        assertFalse(f.controller.updatePersonalLearningPolicy(false, true, f.execute))
        assertFalse(f.controller.state.enabled)
        assertEquals("", f.controller.state.contextText)
    }

    @Test fun `candidate invalidation and personalization replacement expire continuation IDs`() {
        for (replacePersonalization in listOf(false, true)) {
            val f = Fixture(); val hook = PersonalEvents().apply { phrases = listOf("friend") }
            f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            f.raw("hello"); f.type(" "); hook.events.clear()
            val oldId = f.controller.candidateViewState.candidates.single().id
            if (replacePersonalization) f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            else f.controller.clearCandidates()
            val newId = f.controller.candidateViewState.candidates.single().id
            assertNotEquals(oldId, newId)
            assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(oldId, f.execute))
            assertEquals("hello ", f.document)
            assertTrue(hook.events.isEmpty())
            assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(newId, f.execute))
            assertEquals("hello friend ", f.document)
        }
    }

    @Test fun `continuations insert only on explicit current tap and preserve owned suffix`() {
        val f = Fixture(); val hook = PersonalEvents().apply { phrases = listOf("my friend") }
        f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
        f.raw("hello"); f.type(" "); hook.events.clear()
        val id = f.controller.candidateViewState.candidates.single().id
        assertEquals("hello ", f.document)
        assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(id, f.execute))
        assertEquals("hello my friend ", f.document)
        assertEquals(ComposingSegment(leadingBoundary = " "), f.controller.state.composing)
        assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
        assertEquals(listOf("confirm:my", "commit:my:null", "confirm:friend", "commit:friend:null"), hook.events)
    }

    @Test fun `continuation allowlist changes and failed or reentrant commits cannot train`() {
        for (action in listOf<(Fixture, PersonalEvents) -> Unit>(
            { _, h -> h.phrases = listOf("different") },
            { f, _ -> f.fail = "commitText" },
            { f, _ -> f.afterCall = { if (it == "commitText") f.controller.endSession() } },
            { f, _ -> f.controller.endSession() })) {
            val f = Fixture(); val hook = PersonalEvents().apply { phrases = listOf("friend") }
            f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
            f.raw("hello"); f.type(" "); hook.events.clear()
            val id = f.controller.candidateViewState.candidates.single().id
            action(f, hook)
            assertEquals(TypingTextResult.REJECTED, f.controller.selectCandidate(id, f.execute))
            assertTrue(hook.events.isEmpty())
        }
    }

    @Test fun `sensitive session cannot expose phrases or emit feedback`() {
        val f = Fixture(); val hook = PersonalEvents().apply { phrases = listOf("friend") }
        f.controller.setPersonalization(hook, KeyboardLanguage.ENGLISH)
        f.controller.startSession(EditorContext.from(android.text.InputType.TYPE_CLASS_TEXT or
            android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD, 0), 0, 0)
        f.type("hello"); f.type(" ")
        assertFalse(f.controller.candidateViewState.enabled)
        assertTrue(hook.events.isEmpty())
    }


    @Test fun `post-space score corrects the exact committed suffix and first Backspace restores complete original`() {
        for (synchronous in listOf(false, true)) {
            val f = Fixture(modelOnly = true); f.synchronous = synchronous
            f.raw("I"); f.raw(" "); f.raw("helllo"); f.publish("hello")
            val input = f.controller.beginModelRanking(1)!!
            assertEquals(TypingTextResult.HANDLED, f.controller.retainRankingAcrossSpace { f.type(" ") })
            assertEquals("I helllo ", f.document)
            assertTrue(f.controller.isCurrentSpaceCorrection(input.token))
            f.calls.clear()
            assertTrue(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
            assertEquals("I hello ", f.document)
            assertEquals(ComposingSegment(" "), f.controller.state.composing)
            assertEquals(listOf("beginBatchEdit", "setComposingRegion", "commitText", "setComposingRegion", "endBatchEdit"), f.calls)
            f.calls.clear(); f.undo()
            assertEquals("I helllo", f.document)
            assertEquals(ComposingSegment(" ", "helllo"), f.controller.state.composing)
            assertEquals("I helllo", f.controller.state.contextText)
            assertTrue(f.controller.state.originalSelected)
            assertFalse(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
        }
    }

    @Test fun `post-space request cannot survive any later edit or ownership invalidation`() {
        for (action in listOf<(Fixture) -> Unit>(
            { it.type("w") }, { it.undo() }, { it.type(" ") }, { it.type(",") }, { it.type("\n") },
            { it.controller.clearCandidates() }, { it.controller.endSession() },
            { it.controller.updateSelection(0, 0, -1, -1, it.execute) })) {
            val f = Fixture(modelOnly = true); val input = f.pendingSpace()
            action(f)
            val before = f.document; f.calls.clear()
            assertFalse(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
            assertEquals(before, f.document); assertTrue(f.calls.isEmpty())
        }
    }

    @Test fun `post-space token must match every original request identity and is single use`() {
        val f = Fixture(modelOnly = true); val input = f.pendingSpace()
        val original = input.token
        for (token in listOf(ScoringToken(original.sessionId + 1, original.revision, original.requestId, original.candidateIds),
            ScoringToken(original.sessionId, original.revision + 1, original.requestId, original.candidateIds),
            ScoringToken(original.sessionId, original.revision, original.requestId + 1, original.candidateIds),
            ScoringToken(original.sessionId, original.revision, original.requestId, listOf(0, 2)))) {
            val reply = ScoringReply(token, ScoringCode.OK, 0, token.candidateIds.map { NumericScore(it, -1.0, 1) })
            assertFalse(f.controller.acceptSpaceCorrection(reply, f.execute))
        }
        assertTrue(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
        f.calls.clear()
        assertFalse(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
        assertTrue(f.calls.isEmpty())
    }

    @Test fun `post-space failure or Original winner never edits and clears ownership`() {
        for (failure in listOf(true, false)) {
            val f = Fixture(modelOnly = true); val input = f.pendingSpace(); f.calls.clear()
            val reply = if (failure) ScoringReply(input.token, ScoringCode.CANCELLED, 0, emptyList()) else
                ScoringReply(input.token, ScoringCode.OK, 0,
                    listOf(NumericScore(0, -1.0, 1), NumericScore(1, -20.0, 1)))
            assertFalse(f.controller.acceptSpaceCorrection(reply, f.execute))
            assertFalse(f.controller.hasSpaceCorrection)
            assertEquals("helllo ", f.document); assertTrue(f.calls.isEmpty())
        }
    }

    @Test fun `late replacement stops between editor calls on refusal or reentrant ownership loss`() {
        for (fail in listOf("setComposingRegion", "commitText")) {
            val f = Fixture(modelOnly = true); val input = f.pendingSpace(); f.calls.clear(); f.fail = fail
            assertFalse(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
            assertEquals("helllo ", f.document); assertFalse(f.controller.state.enabled)
            assertEquals(0, f.batchDepth)
            if (fail == "setComposingRegion") assertFalse("commitText" in f.calls)
        }
        val f = Fixture(modelOnly = true); val input = f.pendingSpace(); f.calls.clear()
        f.afterCall = { if (it == "setComposingRegion") f.controller.endSession() }
        assertFalse(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
        assertEquals("helllo ", f.document); assertFalse("commitText" in f.calls)
        assertEquals(0, f.batchDepth)
    }

    @Test fun `post-space ownership requires a complete ordinary token and bounded region`() {
        for (prefix in listOf("@", ".", "/", ":", "x=", " ".repeat(250))) {
            val f = Fixture(modelOnly = true); prefix.forEach { f.raw(it.toString()) }
            f.raw("helllo"); f.publish("hello")
            f.controller.beginModelRanking(1)
            f.controller.retainRankingAcrossSpace { f.type(" ") }
            assertFalse(f.controller.hasSpaceCorrection)
        }
        val unknown = Fixture(modelOnly = true, initial = "outside")
        unknown.pendingSpace()
        assertFalse(unknown.controller.hasSpaceCorrection)
    }

    private fun winningReply(input: ScoringInput) = ScoringReply(input.token, ScoringCode.OK, 0,
        listOf(NumericScore(0, -20.0, 1), NumericScore(1, -1.0, 1)))

    @Test fun `post-space correction and Undo preserve exact Unicode source in every language`() {
        for ((language, original, replacement) in listOf(
            Triple(KeyboardLanguage.ENGLISH, "cafe\u0301ss", "cafés"),
            Triple(KeyboardLanguage.RUSSIAN, "превет", "привет"),
            Triple(KeyboardLanguage.SPANISH, "holaa", "hola"))) {
            val f = Fixture(modelOnly = true); f.keyboard = KeyboardState(language)
            f.raw(original); f.publish(replacement)
            val input = f.controller.beginModelRanking(1)!!
            f.controller.retainRankingAcrossSpace { f.type(" ") }
            assertTrue(f.controller.acceptSpaceCorrection(winningReply(input), f.execute))
            assertEquals("$replacement ", f.document)
            f.undo(); assertEquals(original, f.document)
            assertEquals(original, f.controller.state.contextText)
            assertEquals(original, f.controller.state.composing?.typedWord)
        }
    }

    @Test fun `multiline Enter consumes ready correction commits newline and Undo restores original`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.calls.clear()
        assertEquals(TypingTextResult.HANDLED, f.type("\n"))
        assertEquals("hello\n", f.document); assertNull(f.controller.state.composing)
        assertEquals(-1, f.composingStart)
        assertEquals(listOf("beginBatchEdit", "commitText", "endBatchEdit"), f.calls)
        f.calls.clear(); assertEquals(TypingTextResult.HANDLED, f.undo())
        assertEquals("helllo", f.document)
        assertEquals(ComposingSegment(typedWord = "helllo"), f.controller.state.composing)
        assertTrue(f.controller.state.originalSelected)
        assertEquals(listOf("beginBatchEdit", "setComposingRegion", "setComposingText", "endBatchEdit"), f.calls)
    }

    @Test fun `multiline Enter without an admitted correction finishes span and commits exact newline`() {
        for (mode in AutocorrectionMode.entries) {
            val f = Fixture(qualified = false); f.mode = mode; f.raw("helllo"); f.publish("hello"); f.calls.clear()
            assertEquals(TypingTextResult.HANDLED, f.type("\n"))
            assertEquals("helllo\n", f.document); assertNull(f.controller.state.composing)
            assertEquals(listOf("finishComposingText", "commitText"), f.calls)
            assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `editor action adds no punctuation and rejected action newline remains in correction Undo`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.calls.clear()
        assertEquals(TypingTextResult.HANDLED, f.controller.prepareEditorAction(f.policy, f.keyboard, f.mode, f.execute))
        assertEquals("hello", f.document); assertNull(f.controller.state.composing)
        assertFalse(f.document.endsWith('.'))
        assertEquals(TypingTextResult.HANDLED, f.controller.appendEditorActionFallbackNewline(f.execute))
        assertEquals("hello\n", f.document)
        f.calls.clear(); assertEquals(TypingTextResult.HANDLED, f.undo())
        assertEquals("helllo", f.document); assertTrue(f.controller.state.originalSelected)
    }

    @Test fun `editor action without ready correction closes original and fallback newline has no synthetic Undo`() {
        val f = Fixture(); f.raw("hello"); f.calls.clear()
        assertEquals(TypingTextResult.HANDLED, f.controller.prepareEditorAction(f.policy, f.keyboard, f.mode, f.execute))
        assertEquals("hello", f.document); assertNull(f.controller.state.composing)
        assertEquals(listOf("finishComposingText"), f.calls)
        assertEquals(TypingTextResult.HANDLED, f.controller.appendEditorActionFallbackNewline(f.execute))
        assertEquals("hello\n", f.document); assertNull(f.controller.state.lastAutoEdit)
    }

    @Test fun `failed editor action preparation never executes fallback over uncertain text`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.calls.clear(); f.fail = "commitText"
        assertEquals(TypingTextResult.REJECTED,
            f.controller.prepareEditorAction(f.policy, f.keyboard, f.mode, f.execute))
        assertFalse(f.controller.state.enabled)
        assertEquals(TypingTextResult.REJECTED, f.controller.appendEditorActionFallbackNewline(f.execute))
        assertEquals("helllo", f.document)
    }

    @Test fun `space and punctuation commit corrected word but compose only the boundary`() {
        for (boundary in listOf(" ", ",", "!", "?", ";")) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.calls.clear()
            assertEquals(TypingTextResult.HANDLED, f.type(boundary))
            assertEquals("hello$boundary", f.document)
            assertEquals(ComposingSegment(boundary), f.controller.state.composing)
            assertEquals(5, f.composingStart)
            assertEquals(listOf("beginBatchEdit", "commitText", "setComposingRegion", "endBatchEdit"), f.calls)
            assertNotNull(f.controller.state.lastAutoEdit)
            assertTrue(f.controller.candidateViewState.candidates.isEmpty())
            assertEquals(0, f.batchDepth)
        }
    }

    @Test fun `undo followed by the same boundary respects original across languages and acknowledgements`() {
        for (synchronous in listOf(false, true)) {
            for ((language, original, target) in listOf(
                Triple(KeyboardLanguage.ENGLISH, "helllo", "hello"),
                Triple(KeyboardLanguage.RUSSIAN, "всее", "все"),
                Triple(KeyboardLanguage.RUSSIAN, "зочу", "хочу"))) {
                for (boundary in listOf(" ", ",", "!", "?", ";", "\n")) {
                    val f = Fixture(); f.synchronous = synchronous
                    f.keyboard = KeyboardState(language)
                    f.raw("🙂 "); f.raw(original)
                    if (language == KeyboardLanguage.RUSSIAN) f.publishCommon(target) else f.publish(target)
                    assertEquals(TypingTextResult.HANDLED, f.type(boundary))
                    assertEquals("🙂 $target$boundary", f.document)
                    assertEquals(TypingTextResult.HANDLED, f.undo())
                    assertEquals("🙂 $original", f.document)
                    assertTrue(f.controller.state.originalSelected)
                    assertFalse(f.controller.canRequestCandidates)
                    assertNull(f.controller.beginCandidateRequest(100, language))
                    f.calls.clear()
                    assertEquals(TypingTextResult.HANDLED, f.type(boundary))
                    assertEquals("🙂 $original$boundary", f.document)
                    assertNull(f.controller.state.lastAutoEdit)
                    assertEquals(0, f.batchDepth)
                    assertFalse("beginBatchEdit" in f.calls)
                    assertTrue(f.controller.state.enabled)
                }
            }
        }
    }

    @Test fun `erasing restored word rearms correction for a freshly typed word without losing its first letter`() {
        for (synchronous in listOf(false, true)) {
            val f = Fixture(); f.synchronous = synchronous
            f.raw("helllo"); f.publish("hello"); f.type(" "); f.undo()
            repeat("helllo".length) { assertEquals(TypingTextResult.HANDLED, f.undo()) }
            assertEquals("", f.document)
            assertFalse(f.controller.state.originalSelected)
            for (letter in "helllo") {
                assertEquals(TypingTextResult.HANDLED, f.type(letter.toString()))
                assertEquals(f.document, f.controller.state.contextText)
            }
            assertEquals("helllo", f.document)
            assertTrue(f.controller.canRequestCandidates)
            f.publish("hello"); f.type(" ")
            assertEquals("hello ", f.document)
            f.undo(); assertEquals("helllo", f.document)
            assertEquals(0, f.batchDepth)
        }
    }

    @Test fun `editing restored word keeps explicit rejection until that word is finished`() {
        for (synchronous in listOf(false, true)) {
            val f = Fixture(); f.synchronous = synchronous
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("зочу"); f.publishCommon("хочу"); f.type(" ")
            assertEquals("хочу ", f.document)
            f.undo(); assertEquals("зочу", f.document)
            assertEquals(TypingTextResult.HANDLED, f.undo())
            assertEquals("зоч", f.document)
            assertEquals(TypingTextResult.HANDLED, f.type("у"))
            assertEquals("зочу", f.document)
            assertTrue(f.controller.state.originalSelected)
            assertFalse(f.controller.canRequestCandidates)
            f.type(" "); assertEquals("зочу ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
            f.type("з")
            assertEquals("зочу з", f.document)
            assertFalse(f.controller.state.originalSelected)
            assertTrue(f.controller.canRequestCandidates)
            assertEquals(0, f.batchDepth)
        }
    }

    @Test fun `first Backspace restores original composition and candidates without a Delete`() {
        val f = Fixture(); f.raw("I"); f.raw(" "); f.raw("helllo"); f.publish("hello")
        f.type(" "); f.calls.clear()
        assertEquals(TypingTextResult.HANDLED, f.undo())
        assertEquals("I helllo", f.document)
        assertEquals(ComposingSegment(" ", "helllo"), f.controller.state.composing)
        assertEquals("I helllo", f.controller.state.contextText)
        assertEquals(listOf("beginBatchEdit", "setComposingRegion", "setComposingText", "endBatchEdit"), f.calls)
        assertEquals(listOf("helllo", "hello"), f.controller.candidateViewState.candidates.map { it.text })
        assertTrue(f.controller.state.originalSelected)
        assertEquals(f.controller.originalCandidateId, f.controller.candidateViewState.selectedCandidateId)
        assertNull(f.controller.state.lastAutoEdit)
        f.calls.clear(); f.undo()
        assertEquals("I helll", f.document)
        assertEquals(listOf("setComposingText"), f.calls)
    }

    @Test fun `next text closes correction Undo and a later automatic gesture owns the only transaction`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.type(" "); f.type("w")
        assertNull(f.controller.state.lastAutoEdit)
        f.undo(); assertEquals("hello ", f.document)
        val gesture = Fixture(); gesture.raw("helllo"); gesture.publish("hello"); gesture.type(" ")
        gesture.policy = gesture.policy.copy(doubleSpaceEnabled = true)
        gesture.type(" ", doubleSpace = true)
        assertEquals("hello. ", gesture.document)
        gesture.undo(); assertEquals("hello ", gesture.document)
        assertNull(gesture.controller.state.lastAutoEdit)
    }

    @Test fun `all languages restore exact source including decomposed marks and length change`() {
        for ((language, original, replacement) in listOf(
            Triple(KeyboardLanguage.ENGLISH, "cafe\u0301ss", "cafés"),
            Triple(KeyboardLanguage.RUSSIAN, "преветствие", "приветствие"),
            Triple(KeyboardLanguage.SPANISH, "mensage", "mensaje"))) {
            val f = Fixture(); f.keyboard = KeyboardState(language)
            f.raw(original); f.publish(replacement); f.type(" ")
            assertEquals("$replacement ", f.document)
            f.undo(); assertEquals(original, f.document)
            assertEquals(original, f.controller.state.composing?.typedWord)
        }
    }

    @Test fun `calibration without qualification and OFF or suggestions never auto replace`() {
        val current = Fixture(qualified = null)
        current.raw("helllo"); current.publish("hello"); current.type(" ")
        assertEquals("helllo ", current.document); assertNull(current.controller.state.lastAutoEdit)
        for (mode in AutocorrectionMode.entries) {
            val f = Fixture(qualified = false); f.mode = mode; f.raw("helllo"); f.publish("hello"); f.type(" ")
            assertEquals("helllo ", f.document); assertNull(f.controller.state.lastAutoEdit)
        }
        for (mode in listOf(AutocorrectionMode.OFF, AutocorrectionMode.SUGGESTIONS)) {
            val f = Fixture(); f.mode = mode; f.raw("helllo"); f.publish("hello"); f.type(" ")
            assertEquals("helllo ", f.document); assertFalse("beginBatchEdit" in f.calls)
        }
    }

    @Test fun `current qualification keeps English general local disabled and admits ready model decisions`() {
        for (language in KeyboardLanguage.entries) {
            assertEquals(language != KeyboardLanguage.ENGLISH,
                SpellingQualification.CURRENT.allowsGeneralLocal(language))
            assertTrue(SpellingQualification.CURRENT.allowsModel(language))
            val f = Fixture(qualified = null)
            f.keyboard = KeyboardState(language)
            f.raw("helllo"); f.publish("hello")
            val input = f.controller.beginModelRanking(1)!!
            assertTrue(f.controller.acceptModelRanking(ScoringReply(input.token, ScoringCode.OK, 0,
                listOf(NumericScore(0, -20.0, 1), NumericScore(1, -1.0, 1)))))
            f.type(" ")
            assertEquals("hello ", f.document)
            assertNotNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `original choice and manual alternative suppress boundary autocorrection`() {
        for (chooseOriginal in listOf(true, false)) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello")
            val view = f.controller.candidateViewState
            f.controller.selectCandidate(view.candidates[if (chooseOriginal) 0 else 1].id, f.execute)
            f.calls.clear(); f.type(" ")
            assertEquals(if (chooseOriginal) "helllo " else "hello ", f.document)
            assertNull(f.controller.state.lastAutoEdit); assertFalse("beginBatchEdit" in f.calls)
        }
    }

    @Test fun `partial retrieval settings layer language and sensitive policy veto automatic write`() {
        for (change in 0..5) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello", if (change == 0) CandidateCompletion.STATES_EXHAUSTED else CandidateCompletion.COMPLETE)
            when (change) {
                1 -> f.mode = AutocorrectionMode.OFF
                2 -> f.keyboard = f.keyboard.copy(layer = KeyboardLayer.SYMBOLS)
                3 -> f.keyboard = KeyboardState(KeyboardLanguage.SPANISH)
                4 -> f.policy = f.policy.copy(inputPolicy = InputPolicy.SENSITIVE)
                5 -> f.policy = f.policy.copy(requiresRawKeyEvents = true)
            }
            f.calls.clear(); f.type(" ")
            assertEquals("helllo ", f.document)
            assertFalse("beginBatchEdit" in f.calls)
        }
    }

    @Test fun `qualified deterministic decision commits without requesting the model`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello")
        assertNull(f.controller.beginModelRanking(1))
        f.type(" ")
        assertEquals("hello ", f.document)
        val absent = Fixture(); absent.raw("helllo"); absent.type(" ")
        assertEquals("helllo ", absent.document)
    }

    @Test fun `ready model result and qualification are consulted for the actual scoring branch`() {
        val f = Fixture(modelOnly = true); f.raw("helllo"); f.publish("hello"); f.type(" ")
        assertEquals("helllo ", f.document)
        val ready = Fixture(modelOnly = true); ready.raw("helllo"); ready.publish("hello")
        val input = ready.controller.beginModelRanking(1)!!
        assertTrue(ready.controller.acceptModelRanking(ScoringReply(input.token, ScoringCode.OK, 0,
            listOf(NumericScore(0, -20.0, 1), NumericScore(1, -1.0, 1)))))
        ready.type(" "); assertEquals("hello ", ready.document)
        val veto = Fixture(modelOnly = true); veto.raw("helllo"); veto.publish("hello")
        val losing = veto.controller.beginModelRanking(1)!!
        veto.controller.acceptModelRanking(ScoringReply(losing.token, ScoringCode.OK, 0,
            listOf(NumericScore(0, -1.0, 1), NumericScore(1, -100.0, 1))))
        veto.type(" "); assertEquals("helllo ", veto.document)
    }

    @Test fun `synchronous intermediate acknowledgements keep ownership through commit and Undo`() {
        val f = Fixture(); f.synchronous = true; f.raw("helllo"); f.publish("hello")
        f.type(" "); assertTrue(f.controller.state.enabled)
        f.undo(); assertEquals("helllo", f.document); assertTrue(f.controller.state.enabled)
        assertEquals(0, f.batchDepth)
    }

    @Test fun `rejected commit region or Undo disables session without replay or further batch mutation`() {
        for (failure in listOf("beginBatchEdit", "commitText", "setComposingRegion")) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.fail = failure; f.calls.clear()
            assertEquals(TypingTextResult.REJECTED, f.type(" "))
            assertFalse(f.controller.state.enabled); assertNull(f.controller.state.lastAutoEdit)
            assertEquals(if (failure == "setComposingRegion") "hello " else "helllo", f.document)
            assertEquals(0, f.batchDepth)
            f.calls.clear(); assertEquals(TypingTextResult.BYPASS, f.type("x")); assertTrue(f.calls.isEmpty())
        }
        val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.type(" "); f.fail = "setComposingText"
        assertEquals(TypingTextResult.REJECTED, f.undo()); assertEquals("hello ", f.document)
        assertFalse(f.controller.state.enabled); assertEquals(0, f.batchDepth)
    }

    @Test fun `reentrant lifecycle after commit stops region creation and keeps new session empty`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello")
        f.afterCall = { if (it == "commitText") f.controller.startSession(EditorContext.from(1, 0), 0, 0) }
        f.calls.clear(); assertEquals(TypingTextResult.REJECTED, f.type(" "))
        assertEquals(listOf("beginBatchEdit", "commitText", "endBatchEdit"), f.calls)
        assertEquals("", f.controller.state.contextText); assertNull(f.controller.state.lastAutoEdit)
        assertEquals(0, f.batchDepth)
    }

    @Test fun `ownership loss between Undo region and replacement prevents restoring old buffer`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.type(" ")
        f.afterCall = { if (it == "setComposingRegion") f.controller.updateSelection(0, 0, -1, -1) { true } }
        f.calls.clear(); assertEquals(TypingTextResult.REJECTED, f.undo())
        assertFalse("setComposingText" in f.calls)
        assertEquals("hello ", f.document); assertFalse(f.controller.state.enabled)
        assertEquals(0, f.batchDepth)
    }

    @Test fun `context eviction Undo restores the original bounded RAM snapshot`() {
        val f = Fixture(); f.raw("x ".repeat(509)); f.raw("helllo"); f.publish("hello")
        val before = f.controller.state.contextText
        f.type(" "); f.undo()
        assertEquals(before, f.controller.state.contextText)
        assertTrue(f.document.endsWith(" helllo"))
        assertFalse(f.controller.state.lastAutoEdit.toString().contains("helllo"))
    }

    @Test fun `owned email URL code and ambiguous hostname fragments retain original`() {
        for (prefix in listOf("name@", "https://", "foo.", "/", "foo_", "x=", "foo-")) {
            val f = Fixture(); f.raw(prefix); f.raw("helllo"); f.publish("hello"); f.type(" ")
            assertEquals(prefix + "helllo ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `ordinary spelling qualification cannot auto capitalize a known lowercase word`() {
        for ((prefix, original, canonical) in listOf(
            Triple("we", "will", "Will"), Triple("we", "may", "May"), Triple("a", "brown", "Brown"))) {
            val f = Fixture(qualified = true)
            f.raw(prefix); f.raw(" "); f.raw(original)
            f.publishCanonical(canonical, unambiguous = false)
            assertEquals(TypingTextResult.HANDLED, f.type(" "))
            assertEquals("$prefix $original ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `canonical case auto replaces on boundary and Undo restores lowercase original`() {
        val f = Fixture(qualified = false)
        f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.raw("москва")
        f.publishCanonical("Москва", unambiguous = true)

        assertEquals(TypingTextResult.HANDLED, f.type(" "))
        assertEquals("Москва ", f.document)
        assertNotNull(f.controller.state.lastAutoEdit)
        assertEquals(TypingTextResult.HANDLED, f.undo())
        assertEquals("москва", f.document)
        assertEquals("москва", f.controller.state.composing?.typedWord)
        assertTrue(f.controller.state.originalSelected)
    }

    @Test fun `routed lowercase conflict blocks canonical auto even with ordinary qualification`() {
        val f = Fixture(qualified = true)
        f.raw("si")
        f.publishCanonical("Si", unambiguous = true, eligible = false)
        assertEquals(TypingTextResult.HANDLED, f.type(" "))
        assertEquals("si ", f.document)
        assertNull(f.controller.state.lastAutoEdit)
    }

    @Test fun `disabled autocorrection keeps canonical case as a suggestion`() {
        for (mode in listOf(AutocorrectionMode.SUGGESTIONS, AutocorrectionMode.OFF)) {
            val f = Fixture(qualified = false)
            f.keyboard = KeyboardState(KeyboardLanguage.SPANISH)
            f.mode = mode
            f.raw("juan")
            f.publishCanonical("Juan", unambiguous = false)
            f.type(" ")
            assertEquals("juan ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `first dot or colon cannot change a future hostname or scheme`() {
        for (boundary in listOf(".", ":")) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello"); f.type(boundary)
            assertEquals("helllo$boundary", f.document)
            assertNull(f.controller.state.lastAutoEdit)
            f.raw(if (boundary == ".") "com" else "//host")
            f.type(" ")
            assertEquals(if (boundary == ".") "helllo.com " else "helllo://host ", f.document)
        }
    }

    @Test fun `dot and colon correct a ready Cyrillic word while ASCII protected forms stay unchanged`() {
        for (boundary in listOf(".", ":")) {
            val cyrillic = Fixture().apply { keyboard = KeyboardState(KeyboardLanguage.RUSSIAN) }
            cyrillic.raw("смотруть"); cyrillic.publish("смотреть")
            assertEquals(TypingTextResult.HANDLED, cyrillic.type(boundary))
            assertEquals("смотреть$boundary", cyrillic.document)
            assertNotNull(cyrillic.controller.state.lastAutoEdit)
            assertEquals(TypingTextResult.HANDLED, cyrillic.undo())
            assertEquals("смотруть", cyrillic.document)

            val ascii = Fixture().apply { keyboard = KeyboardState(KeyboardLanguage.RUSSIAN) }
            ascii.raw("helllo"); ascii.publish("hello")
            assertEquals(TypingTextResult.HANDLED, ascii.type(boundary))
            assertEquals("helllo$boundary", ascii.document)
            assertNull(ascii.controller.state.lastAutoEdit)
        }
    }

    @Test fun `reentrant candidate policy invalidation stops batch and never publishes its Undo`() {
        for (stage in listOf("beginBatchEdit", "commitText", "endBatchEdit")) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello")
            f.afterCall = { if (it == stage) f.controller.clearCandidates() }
            f.calls.clear(); assertEquals(TypingTextResult.REJECTED, f.type(" "))
            assertFalse(f.controller.state.enabled); assertNull(f.controller.state.lastAutoEdit)
            if (stage != "endBatchEdit") assertFalse("setComposingRegion" in f.calls)
            assertEquals(0, f.batchDepth)
        }
    }

    @Test fun `dead connection and throwing cleanup disable session without replay or uncaught exception`() {
        for (afterCommit in listOf(false, true)) {
            val f = Fixture(); f.raw("helllo"); f.publish("hello")
            if (afterCommit) f.afterCall = { if (it == "commitText") f.throwAll = true } else f.throwAll = true
            assertEquals(TypingTextResult.REJECTED, f.type(" "))
            assertFalse(f.controller.state.enabled); assertNull(f.controller.state.lastAutoEdit)
            assertEquals(if (afterCommit) "hello " else "helllo", f.document)
            assertEquals("finishComposingText", f.calls.last())
        }
    }

    @Test fun `unknown editor prefix abstains until Rune supplies an explicit word boundary`() {
        val f = Fixture(initial = "outside@")
        f.raw("helllo"); f.publish("hello"); f.type(" ")
        assertEquals("outside@helllo ", f.document); assertNull(f.controller.state.lastAutoEdit)
        f.raw("helllo"); f.publish("hello"); f.type(" ")
        assertEquals("outside@helllo hello ", f.document)
        f.undo(); assertEquals("outside@helllo helllo", f.document)
    }

    @Test fun `all explicit confusions correct on fast Space with exact Undo and retained Original`() {
        for ((language, original, target) in commonConfusions) {
            val f = Fixture(qualified = null); f.keyboard = KeyboardState(language)
            f.raw(original); f.publishCommon(target)
            assertEquals(listOf(original, target), f.controller.candidateViewState.candidates.map { it.text })
            assertFalse(f.controller.canRequestModelRanking)
            assertNull(f.controller.beginModelRanking(1))
            f.type(" "); assertEquals("$target ", f.document)
            f.undo(); assertEquals(original, f.document)
            assertTrue(f.controller.state.originalSelected)
            f.type(" "); assertEquals("$original ", f.document)
        }
    }

    @Test fun `explicit confusions stay suggestions outside automatic mode`() {
        for (mode in listOf(AutocorrectionMode.OFF, AutocorrectionMode.SUGGESTIONS)) {
            val f = Fixture(qualified = null); f.mode = mode
            f.raw("teh"); f.publishCommon("the"); f.type(" ")
            assertEquals("teh ", f.document); assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `explicit confusions honor ownership language editor and incomplete search vetoes`() {
        for (completion in listOf(CandidateCompletion.STATES_EXHAUSTED, CandidateCompletion.VERIFIED_EXHAUSTED)) {
            val f = Fixture(qualified = null); f.raw("teh"); f.publishCommon("the", completion)
            assertEquals(listOf("teh", "the"), f.controller.candidateViewState.candidates.map { it.text })
            f.type(" "); assertEquals("teh ", f.document)
        }
        for (prefix in listOf("@", "/", ".", "x=")) {
            val f = Fixture(qualified = null); f.raw(prefix); f.raw("teh"); f.publishCommon("the")
            f.type(" "); assertEquals(prefix + "teh ", f.document)
        }
        for (change in listOf<(Fixture) -> Unit>(
            { it.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN) },
            { it.policy = it.policy.copy(inputPolicy = InputPolicy.SENSITIVE) },
            { it.controller.clearCandidates() })) {
            val f = Fixture(qualified = null); f.raw("teh"); f.publishCommon("the"); change(f)
            f.type(" "); assertFalse(f.document.contains("the")); assertNull(f.controller.state.lastAutoEdit)
        }
        val f = Fixture(qualified = null); f.raw("teh"); f.publishCommon("the")
        f.controller.endSession(); f.type(" "); assertEquals("teh", f.document)
    }

    @Test fun `one and two codepoint words never request spelling model`() {
        for ((original, target) in listOf("a" to "at", "ba" to "bat")) {
            val f = Fixture(qualified = null); f.raw(original); f.publish(target)
            assertFalse(f.controller.canRequestModelRanking)
            assertNull(f.controller.beginModelRanking(1))
        }
    }

    @Test fun `stale model reply cannot overwrite a newly resolved local decision`() {
        val f = Fixture(qualified = null); f.raw("helllo"); f.publish("hello")
        val input = f.controller.beginModelRanking(1)!!
        f.type(" "); f.raw("teh"); f.publishCommon("the")
        assertFalse(f.controller.acceptModelRanking(winningReply(input)))
        f.type(" "); assertEquals("helllo the ", f.document)
    }

    private val commonConfusions = listOf(
        Triple(KeyboardLanguage.RUSSIAN, "автокрекция", "автокоррекция"),
        Triple(KeyboardLanguage.RUSSIAN, "арфография", "орфография"),
        Triple(KeyboardLanguage.RUSSIAN, "сообшение", "сообщение"),
        Triple(KeyboardLanguage.RUSSIAN, "реалбно", "реально"),
        Triple(KeyboardLanguage.RUSSIAN, "мододец", "молодец"),
        Triple(KeyboardLanguage.RUSSIAN, "шоржусь", "горжусь"),
        Triple(KeyboardLanguage.RUSSIAN, "заьыл", "забыл"),
        Triple(KeyboardLanguage.RUSSIAN, "расмотри", "рассмотри"),
        Triple(KeyboardLanguage.RUSSIAN, "прийду", "приду"),
        Triple(KeyboardLanguage.RUSSIAN, "спосибо", "спасибо"),
        Triple(KeyboardLanguage.RUSSIAN, "скороо", "скоро"),
        Triple(KeyboardLanguage.RUSSIAN, "всее", "все"),
        Triple(KeyboardLanguage.ENGLISH, "teh", "the"),
        Triple(KeyboardLanguage.ENGLISH, "recieve", "receive"),
        Triple(KeyboardLanguage.ENGLISH, "adress", "address"),
        Triple(KeyboardLanguage.SPANISH, "mensage", "mensaje"),
        Triple(KeyboardLanguage.SPANISH, "correcion", "corrección"),
    )

    @Test fun `recovery winner retains recovery evidence when already present in baseline suggestions`() {
        val f = Fixture(); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.controller.setPersonalization(object : TypingPersonalization {
            override fun recoveryAutomaticCandidate(context: String, generation: CandidateGeneration,
                language: KeyboardLanguage) = generation.neighborRecovery.alternatives.singleOrNull()
            override fun recoveryAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
                language: KeyboardLanguage) = AutomaticTypingDecision(candidate in generation.neighborRecovery.alternatives)
        }, KeyboardLanguage.RUSSIAN)
        f.raw("рооверка")
        val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
        val baseline = GeneratedCandidate("проверка", "проверка", "проверка", KeyboardLanguage.RUSSIAN,
            false, 2, 30, 2, EditFeatures(1.5, 2, 0.0), 0, CasePattern.LOWER)
        val recovery = baseline.copy(languagePrior = 0)
        val generation = CandidateGeneration(request.token, listOf(baseline), CandidateCompletion.COMPLETE,
            false, null, 1, 1, LocalSearchEvidence(CandidateCompletion.COMPLETE, emptyList(), 1, 0),
            neighborRecovery = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(recovery), 2, 1))
        assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId, generation)))
        f.type(" ")
        assertEquals("проверка ", f.document)
        f.undo()
        assertEquals("рооверка", f.document)
    }

    @Test fun `model refines previous word while preserving live next word and root undo`() {
        for (target in listOf("проверки", "проверочка", "слово", "рроверка")) for (synchronous in listOf(false, true)) {
            val f = Fixture(refinement = true)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.controller.configureFeatures(DiagnosticFeature.VISIBLE_UNDO.bit, DiagnosticFeature.VISIBLE_UNDO.bit)
            f.synchronous = synchronous
            f.raw("рроверка")
            // Baseline has a single distance-one winner. Additional words belong only to the recovery pool.
            val request = f.controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
            fun candidate(word: String) = GeneratedCandidate(word, word, word, KeyboardLanguage.RUSSIAN,
                false, 2, 1, 1, EditFeatures(0.75, 1, 0.0), 0, CasePattern.LOWER)
            val local = candidate("проверка")
            val generation = CandidateGeneration(request.token, listOf(local), CandidateCompletion.COMPLETE,
                false, null, 1, 1, LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(local), 1, 1),
                neighborRecovery = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(candidate(target)), 1, 1))
            assertTrue(f.controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId, generation)))
            f.type(" ")
            assertEquals("проверка ", f.document)
            val input = f.controller.beginPreviousWordRefinement(1)!!
            f.type("сл")
            f.type("ед")
            val wordIndex = input.continuations.indexOf(target)
            f.now = 999_000_000
            val reply = ScoringReply(input.token, ScoringCode.OK, 1, input.token.candidateIds.map {
                NumericScore(it, if (it == wordIndex) -1.0 else -8.0, 1) })
            assertTrue(f.controller.acceptPreviousWordRefinement(reply, f.execute))
            assertEquals("$target след", f.document)
            assertEquals(" след", f.controller.state.composing!!.text)
            assertEquals(f.document.length, f.caret)
            assertEquals(target.length, f.composingStart)
            assertFalse(f.controller.acceptPreviousWordRefinement(reply, f.execute))
            val undo = f.controller.candidateViewState.candidates.filterIsInstance<io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single()
            assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
            assertEquals("рроверка след", f.document)
            assertEquals(f.document.length, f.caret)
            assertTrue(f.calls.none { it in setOf("getTextBeforeCursor", "getTextAfterCursor", "getSelectedText", "getSurroundingText", "getExtractedText", "getCursorCapsMode") })
        }
    }

    @Test fun `refinement expires exactly at one second and backspace keeps normal next word behavior`() {
        for (time in listOf(999_000_000L, 1_000_000_000L, 1_001_000_000L)) {
            val f = Fixture(refinement = true)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("рроверка"); f.publish("проверка"); f.type(" ")
            val input = f.controller.beginPreviousWordRefinement(1)!!
            f.type("след")
            f.now = time
            val reply = ScoringReply(input.token, 0, 1, input.token.candidateIds.map { NumericScore(it, if (it == 0) -1.0 else -8.0, 1) })
            assertEquals(time < 1_000_000_000L, f.controller.acceptPreviousWordRefinement(reply, f.execute))
            f.undo()
            assertEquals((if (time < 1_000_000_000L) "рроверка" else "проверка") + " сле", f.document)
            assertFalse(f.controller.canRefinePreviousWord)
        }
    }

    @Test fun `deleting next word letters cancels model but preserves root Undo until boundary`() {
        for (deleteCount in listOf(1, 4)) {
            val f = Fixture(refinement = true); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.controller.configureFeatures(DiagnosticFeature.VISIBLE_UNDO.bit, DiagnosticFeature.VISIBLE_UNDO.bit)
            f.raw("рроверка"); f.publish("проверка"); f.type(" ")
            val input = f.controller.beginPreviousWordRefinement(1)!!
            f.type("след")
            repeat(deleteCount) { f.undo() }
            f.now = 5_000_000_000L
            assertFalse(f.controller.isCurrentPreviousWordRefinement(input.token))
            val undo = f.controller.candidateViewState.candidates.filterIsInstance<io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo>().single()
            assertEquals(TypingTextResult.HANDLED, f.controller.selectCandidate(undo.id, f.execute))
            assertEquals("рроверка " + "след".dropLast(deleteCount), f.document)
            assertTrue(f.controller.candidateViewState.candidates.none { it is io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Undo })
        }
    }

    @Test fun `next boundary and editor failure invalidate previous word refinement`() {
        for (boundary in listOf(" ", ".", "\n")) {
            val f = Fixture(refinement = true); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("рроверка"); f.publish("проверка"); f.type(" ")
            val input = f.controller.beginPreviousWordRefinement(1)!!
            f.type("след"); f.type(boundary)
            assertFalse(f.controller.isCurrentPreviousWordRefinement(input.token))
        }
        for (failure in listOf("beginBatchEdit", "setComposingRegion", "commitText")) {
            val f = Fixture(refinement = true); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("рроверка"); f.publish("проверка"); f.type(" ")
            val input = f.controller.beginPreviousWordRefinement(1)!!
            f.type("след"); f.fail = failure
            val reply = ScoringReply(input.token, 0, 1, input.token.candidateIds.map { NumericScore(it, if (it == 0) -1.0 else -8.0, 1) })
            assertFalse(f.controller.acceptPreviousWordRefinement(reply, f.execute))
            assertFalse(f.controller.state.enabled)
            assertFalse(f.controller.canRefinePreviousWord)
        }
    }

    @Test fun `refinement aborts when deadline expires between batch commands and never rolls text back`() {
        for (failLastRegion in listOf(false, true)) {
            val f = Fixture(refinement = true); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("рроверка"); f.publish("проверка"); f.type(" ")
            val input = f.controller.beginPreviousWordRefinement(1)!!
            f.type("след")
            f.afterCall = { name ->
                if (!failLastRegion && name == "setComposingRegion") f.now = 1_000_000_000
                if (failLastRegion && name == "commitText") f.fail = "setComposingRegion"
            }
            val reply = ScoringReply(input.token, 0, 1, input.token.candidateIds.map { NumericScore(it, if (it == 0) -1.0 else -8.0, 1) })
            assertFalse(f.controller.acceptPreviousWordRefinement(reply, f.execute))
            assertEquals((if (failLastRegion) "рроверка" else "проверка") + " след", f.document)
            assertFalse(f.controller.state.enabled)
            assertFalse(f.controller.acceptPreviousWordRefinement(reply, f.execute))
        }
    }

    @Test fun `oversized live suffix refuses refinement and leaves next word intact`() {
        val f = Fixture(refinement = true); f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        f.raw("рроверка"); f.publish("проверка"); f.type(" ")
        val input = f.controller.beginPreviousWordRefinement(1)!!
        f.type("я".repeat(120))
        val before = f.document; val calls = f.calls.size
        assertFalse(f.controller.acceptPreviousWordRefinement(ScoringReply(input.token, 0, 1,
            input.token.candidateIds.map { NumericScore(it, if (it == 0) -1.0 else -8.0, 1) }), f.execute))
        assertEquals(before, f.document); assertEquals(calls, f.calls.size)
    }

    @Test fun `shifted composing word is finished before plain fallback preserves its text`() {
        val f = Fixture(); f.raw("hello")
        val oldSession = f.controller.state.sessionId
        f.document = "X " + f.document; f.caret += 2; f.composingStart += 2; f.composingEnd += 2
        val calls = f.calls.size
        assertTrue(f.controller.updateSelection(f.caret, f.caret, f.composingStart, f.composingEnd, f.execute))
        assertEquals(listOf("finishComposingText"), f.calls.drop(calls))
        assertFalse(f.controller.state.enabled)
        assertNull(f.controller.state.composing)
        assertEquals("", f.controller.state.contextText)
        assertEquals(oldSession, f.controller.state.sessionId)
        assertEquals(TypingTextResult.BYPASS, f.type("x"))
        assertTrue(f.execute(TypingEdit.CommitText("x")))
        assertEquals("X hellox", f.document)
    }

    @Test fun `prefix rewrite keeps pending owned space before plain fallback`() {
        val f = Fixture(initial = "a-- ").apply { synchronous = true }; f.raw("b"); f.type(" ")
        assertEquals("a-- b ", f.document)
        assertEquals(5, f.composingStart)
        f.document = f.document.replace("--", "—"); f.caret--; f.composingStart--; f.composingEnd--
        assertTrue(f.controller.updateSelection(f.caret, f.caret, f.composingStart, f.composingEnd, f.execute))
        assertFalse(f.controller.state.enabled)
        assertEquals(-1, f.composingStart)
        assertEquals(TypingTextResult.BYPASS, f.type("x"))
        assertTrue(f.execute(TypingEdit.CommitText("x")))
        assertEquals("a— b x", f.document)
    }

    @Test fun `unknown reported span without Rune composition is finished without adopting it`() {
        val f = Fixture(initial = "editor")
        f.composingStart = 0; f.composingEnd = 6
        assertTrue(f.controller.updateSelection(6, 6, 0, 6, f.execute))
        assertEquals(listOf("finishComposingText"), f.calls)
        assertFalse(f.controller.state.enabled)
        assertEquals(TypingTextResult.BYPASS, f.type("x"))
        assertTrue(f.execute(TypingEdit.CommitText("x")))
        assertEquals("editorx", f.document)
    }

    private class Fixture(qualified: Boolean? = true, modelOnly: Boolean = false, initial: String = "", refinement: Boolean = false,
        refinementQualified: Boolean? = null, rescueQualified: Boolean? = null, wordContextQualified: Boolean? = null, grammarRevisionQualified: Boolean? = null, nounCaseQualified: Boolean? = null) {
        var now = 0L
        val controller = TypingSessionController(jvmGraphemes, qualified?.let { allowed ->
            SpellingQualification { _, model -> if (model == SpellingSource.MODEL_REFINEMENT && refinementQualified != null)
                refinementQualified else if (model == SpellingSource.NOUN_CASE_REVISION && nounCaseQualified != null)
                nounCaseQualified else if (model == SpellingSource.INFINITIVE_REVISION && grammarRevisionQualified != null)
                grammarRevisionQualified else if (model == SpellingSource.WORD_CONTEXT && wordContextQualified != null)
                wordContextQualified else if (model == SpellingSource.JOINT_RESCUE && rescueQualified != null)
                rescueQualified else allowed && (!modelOnly || model == SpellingSource.MODEL) }
        } ?: SpellingQualification.CURRENT, nanoTime = { now },
            refinementThresholds = if (refinement) RecoveryThresholds(-3.0, 0.5) else null)
            .apply { startSession(EditorContext.from(1, 0), initial.length, initial.length) }
        var document = initial
        var caret = initial.length
        var composingStart = -1
        var composingEnd = -1
        var batchDepth = 0
        var fail: String? = null
        var throwAll = false
        var synchronous = false
        var afterCall: ((String) -> Unit)? = null
        var mode = AutocorrectionMode.HIGH_CONFIDENCE
        var keyboard = KeyboardState(KeyboardLanguage.ENGLISH)
        var policy = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, false)
        val calls = mutableListOf<String>()
        private var requestId = 0L
        private val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java)) { _, method, args ->
            val name = method.name
            calls.add(name)
            if (throwAll) throw IllegalStateException("Synthetic dead connection")
            if (name == fail) false else {
                val result = when (name) {
                    "beginBatchEdit" -> { batchDepth++; true }
                    "endBatchEdit" -> { batchDepth--; check(batchDepth >= 0); false }
                    "setComposingRegion" -> {
                        composingStart = args!![0] as Int; composingEnd = args[1] as Int
                        check(composingStart >= 0 && composingEnd <= document.length)
                        acknowledge(); true
                    }
                    "commitText", "setComposingText" -> {
                        val value = args!![0].toString()
                        val start = if (composingStart >= 0) composingStart else caret
                        val end = if (composingStart >= 0) composingEnd else caret
                        document = document.substring(0, start) + value + document.substring(end)
                        caret = start + value.length
                        composingStart = if (name == "setComposingText") start else -1
                        composingEnd = if (composingStart >= 0) caret else -1
                        acknowledge(); true
                    }
                    "finishComposingText" -> { composingStart = -1; composingEnd = -1; acknowledge(); true }
                    else -> throw AssertionError("Forbidden editor read/delete or unexpected operation: $name")
                }
                afterCall?.invoke(name)
                result
            }
        } as InputConnection
        private fun acknowledge() {
            if (synchronous) assertFalse(controller.updateSelection(caret, caret, composingStart, composingEnd) { true })
        }
        private fun command(edit: TypingEdit): EditorCommand = when (edit) {
            is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
            is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
            TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
            is TypingEdit.SetComposingRegion -> EditorCommand.SetComposingRegion(edit.start, edit.end)
            is TypingEdit.Batch -> EditorCommand.Batch(edit.edits.map(::command), edit.isCurrent)
        }
        val execute: (TypingEdit) -> Boolean = { edit ->
            EditorCommandExecutor.execute(command(edit), connection, false, false).handled
        }
        fun type(text: String, doubleSpace: Boolean = false) = controller.typeText(text, policy, keyboard,
            doubleSpaceGesture = doubleSpace, autocorrectionMode = mode, execute = execute)
        fun raw(text: String) = controller.typeText(text, execute)
        fun undo() = controller.deletePrevious(execute)
        fun pendingLocalSpace(original: String, target: String): LocalCandidateReply {
            raw(original)
            val request = checkNotNull(controller.beginCandidateRequest(++requestId, keyboard.language))
            val lexicon = object : CandidateLexicon {
                override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
                    if (language == keyboard.language && key == target) ExactMembership.PRESENT else ExactMembership.ABSENT
                override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                    control: CandidateSearchControl, visitor: CandidateVisitor) = LexiconScanStatus.COMPLETE
            }
            val generation = CandidateGenerator(lexicon).generate(original, keyboard.language)
            controller.retainCandidateAcrossSpace { type(" ") }
            return LocalCandidateReply(request.sessionId, request.revision, request.requestId, generation)
        }

        fun pendingSpace(): ScoringInput {
            raw("helllo"); publish("hello")
            val input = controller.beginModelRanking(1)!!
            controller.retainRankingAcrossSpace { type(" ") }
            return input
        }
        fun publish(word: String, completion: CandidateCompletion = CandidateCompletion.COMPLETE) {
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val item = GeneratedCandidate(word, TokenUnicode.folded(word), TokenUnicode.folded(word), keyboard.language,
                false, 4, 1, 1, EditFeatures(1.0, 0, 0.0),
                kotlin.math.abs(word.length - request.token.length), CasePattern.analyze(request.token))
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(item), completion, false, null, 1, 1,
                    LocalSearchEvidence(completion, listOf(item), 1, 1)))))
        }
        fun publishMany(vararg words: String) {
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val items = words.map { word -> GeneratedCandidate(word, TokenUnicode.folded(word), TokenUnicode.folded(word), keyboard.language,
                false, 4, 1, 1, EditFeatures(1.0, 0, 0.0),
                kotlin.math.abs(word.length - request.token.length), CasePattern.analyze(request.token)) }
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, items, CandidateCompletion.COMPLETE, false, null, 1, items.size))))
        }
        fun publishCommon(target: String, completion: CandidateCompletion = CandidateCompletion.COMPLETE) {
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val lexicon = object : CandidateLexicon {
                override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
                    if (language == keyboard.language && key == target) ExactMembership.PRESENT else ExactMembership.ABSENT
                override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                    control: CandidateSearchControl, visitor: CandidateVisitor) = LexiconScanStatus.COMPLETE
            }
            val result = CandidateGenerator(lexicon).generate(request.token, keyboard.language)
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
                request.requestId, result.copy(completion = completion))))
        }
        fun publishCanonical(word: String, unambiguous: Boolean, eligible: Boolean = unambiguous) {
            assertTrue(controller.acceptCandidates(canonicalReply(word, unambiguous, eligible)))
        }
        fun pendingCanonicalSpace(word: String): LocalCandidateReply {
            val reply = canonicalReply(word, true, true)
            controller.retainCandidateAcrossSpace { type(" ") }
            return reply
        }
        private fun canonicalReply(word: String, unambiguous: Boolean, eligible: Boolean): LocalCandidateReply {
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val item = GeneratedCandidate(word, word, TokenUnicode.folded(word), keyboard.language,
                false, 4, 1, 0, EditFeatures(0.0, 0, 0.0), 0, CasePattern.TITLE,
                GeneratedCandidateKind.CANONICAL_CASE, canonicalCaseUnambiguous = unambiguous,
                canonicalCaseAutoEligible = eligible)
            return LocalCandidateReply(request.sessionId, request.revision,
                request.requestId, CandidateGeneration(request.token, listOf(item),
                    CandidateCompletion.VALID_WORD, true, null, 1, 0))
        }
    }
}
