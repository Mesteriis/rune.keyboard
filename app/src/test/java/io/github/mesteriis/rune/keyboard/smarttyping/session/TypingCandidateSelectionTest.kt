package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.text.InputType
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.NumericScore
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateSearchControl
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateVisitor
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.ExactMembership
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LexiconScanStatus
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateRequest
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import java.lang.ref.WeakReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class TypingCandidateSelectionTest {
    private val controller = TypingSessionController(jvmGraphemes)
    private val edits = mutableListOf<TypingEdit>()
    private val execute: (TypingEdit) -> Boolean = { edits.add(it); true }
    private var requestId = 0L

    @Test fun `only latest registered reply for exact composition can publish`() {
        start("helo")
        val old = request()
        val latest = request()
        assertFalse(controller.acceptCandidates(reply(old, "hello")))
        assertFalse(controller.acceptCandidates(reply(latest, "hello").copy(revision = latest.revision + 1)))
        assertTrue(controller.acceptCandidates(reply(latest, "hello")))
        assertFalse(controller.acceptCandidates(reply(latest, "help")))
        assertEquals(listOf("helo", "hello"), labels())
        assertNull(controller.beginCandidateRequest(latest.requestId, KeyboardLanguage.ENGLISH))
    }

    @Test fun `wrong original is consumed without publishing or editor changes`() {
        start("helo")
        val request = request()
        val wrong = reply(request, "hello").let { it.copy(generation = it.generation.copy(original = "other")) }
        assertFalse(controller.acceptCandidates(wrong))
        assertFalse(controller.acceptCandidates(reply(request, "hello")))
        assertEquals(listOf("helo"), labels())
        assertEquals(1, edits.size)
    }

    @Test fun `projection keeps source original and calibrated alternatives without editing`() {
        start("helo")
        val before = controller.state
        publish("hello", "help", "held", "hero", "halo", "hell", "helm")
        assertEquals(before, controller.state)
        assertEquals(listOf("helo", "help", "held"), labels())
        val view = controller.candidateViewState
        assertTrue(view.candidates.first() is CandidateUiItem.Original)
        assertEquals(view.candidates[0].id, view.selectedCandidateId)
        assertEquals(1, edits.size)
        assertTrue(view.candidates.all { it.id.length <= CandidateUiItem.MAX_ID_LENGTH })
    }

    @Test fun `manual length changing tap and original restoration each replace whole owned segment once`() {
        start("I")
        controller.typeText(" ", execute)
        controller.typeText("helo", execute)
        publish("hello", "help")
        val originalId = controller.originalCandidateId!!
        val correctionId = controller.candidateViewState.candidates.single { it.text == "hello" }.id
        edits.clear()
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(correctionId, execute))
        assertEquals(listOf(TypingEdit.SetComposingText(" hello")), edits)
        assertEquals(ComposingSegment(" ", "hello"), controller.state.composing)
        assertEquals("I hello", controller.state.contextText)
        assertEquals(listOf("helo", "help", "hello"), labels())
        assertFalse(controller.canRequestCandidates)
        assertFalse(controller.selectOriginal(controller.originalCandidateId!!))
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(originalId, execute))
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(correctionId, execute))
        edits.clear()
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(controller.originalCandidateId!!, execute))
        assertEquals(listOf(TypingEdit.SetComposingText(" helo")), edits)
        assertEquals("I helo", controller.state.contextText)
        assertEquals(ComposingSegment(" ", "helo"), controller.state.composing)
        assertTrue(controller.state.originalSelected)
        assertEquals(controller.originalCandidateId, controller.candidateViewState.selectedCandidateId)
        assertNull(controller.state.lastAutoEdit)
    }

    @Test fun `case preserved Unicode source restores exact original bytes including decomposed marks`() {
        start("Cafe\u0301")
        publish("Cafés")
        controller.selectCandidate(correction(), execute)
        assertEquals("Cafés", controller.state.composing!!.text)
        assertEquals("Cafe\u0301", labels().first())
        controller.selectCandidate(controller.originalCandidateId!!, execute)
        assertEquals("Cafe\u0301", controller.state.composing!!.text)
        assertEquals("Cafe\u0301", controller.state.contextText)
    }

    @Test fun `shorter Title Case alternative preserves boundary and original spelling`() {
        start("The")
        controller.typeText(" ", execute)
        controller.typeText("Helllo", execute)
        publish("Hello")
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(correction(), execute))
        assertEquals(" Hello", controller.state.composing!!.text)
        controller.selectCandidate(controller.originalCandidateId!!, execute)
        assertEquals("The Helllo", controller.state.contextText)
    }

    @Test fun `multi character pending boundary is preserved and previous auto Undo is retired`() {
        start("First")
        controller.typeText(" ", execute)
        controller.doubleSpace(execute)
        assertEquals(". ", controller.state.composing!!.leadingBoundary)
        controller.typeText("helo", execute)
        publish("hello")
        edits.clear()
        controller.selectCandidate(correction(), execute)
        assertEquals(listOf(TypingEdit.SetComposingText(". hello")), edits)
        assertEquals("First. hello", controller.state.contextText)
        assertNull(controller.state.lastAutoEdit)
        controller.selectCandidate(controller.originalCandidateId!!, execute)
        assertEquals("First. helo", controller.state.contextText)
    }

    @Test fun `no-edit original API remains a veto and keeps display original`() {
        start("helo")
        publish("hello")
        val size = edits.size
        assertTrue(controller.selectOriginal(controller.originalCandidateId!!))
        assertEquals(size, edits.size)
        assertTrue(controller.state.originalSelected)
        assertFalse(controller.canRequestCandidates)
        assertEquals(controller.originalCandidateId, controller.candidateViewState.selectedCandidateId)
        assertEquals(listOf("helo", "hello"), labels())
    }

    @Test fun `manual alternative after original veto does not clear veto`() {
        start("helo")
        publish("hello")
        controller.selectOriginal(controller.originalCandidateId!!)
        controller.selectCandidate(correction(), execute)
        assertTrue(controller.state.originalSelected)
        assertEquals("hello", controller.state.composing!!.typedWord)
        assertEquals(correction(), controller.candidateViewState.selectedCandidateId)
        controller.typeText("s", execute)
        assertTrue(controller.state.originalSelected)
        assertEquals(listOf("hellos"), labels())
        controller.typeText(" ", execute)
        assertFalse(controller.state.originalSelected)
    }

    @Test fun `next text edit retires manual source and permits a new request`() {
        start("helo")
        publish("hello")
        controller.selectCandidate(correction(), execute)
        controller.typeText("s", execute)
        assertEquals(listOf("hellos"), labels())
        assertTrue(controller.canRequestCandidates)
        assertEquals("hellos", request().token)
    }

    @Test fun `manual choice does not create auto Undo and Backspace edits replacement normally`() {
        start("helo")
        publish("hello")
        controller.selectCandidate(correction(), execute)
        assertNull(controller.state.lastAutoEdit)
        edits.clear()
        controller.deletePrevious(execute)
        assertEquals(listOf(TypingEdit.SetComposingText("hell")), edits)
        assertEquals(listOf("hell"), labels())
        assertNull(controller.state.lastAutoEdit)
    }

    @Test fun `boundary uses chosen text once and clears candidates`() {
        start("helo")
        publish("hello")
        controller.selectCandidate(correction(), execute)
        edits.clear()
        controller.typeText(" ", execute)
        assertEquals(listOf(TypingEdit.FinishComposingText, TypingEdit.SetComposingText(" ")), edits)
        assertEquals("hello ", controller.state.contextText)
        assertTrue(controller.candidateViewState.candidates.isEmpty())
        assertFalse(controller.canRequestCandidates)
    }

    @Test fun `current owned acknowledgments retain selection but external caret changes reject taps`() {
        start("helo")
        publish("hello")
        val id = correction()
        assertFalse(controller.updateSelection(4, 4, 0, 4, execute))
        assertEquals(id, correction())
        assertTrue(controller.ownsCandidateComposition)
        assertTrue(controller.updateSelection(2, 2, 0, 4, execute))
        val size = edits.size
        assertFalse(controller.ownsCandidateComposition)
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(id, execute))
        assertEquals(size, edits.size)
        assertTrue(controller.candidateViewState.candidates.isEmpty())
    }

    @Test fun `external selection or composing loss cannot replace unknown span`() {
        for (selection in listOf(intArrayOf(1, 3, 0, 4), intArrayOf(4, 4, -1, -1), intArrayOf(8, 8, 6, 8))) {
            start("helo")
            publish("hello")
            val id = correction()
            controller.updateSelection(selection[0], selection[1], selection[2], selection[3], execute)
            edits.clear()
            assertNull(controller.beginCandidateRequest(++requestId, KeyboardLanguage.ENGLISH))
            assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(id, execute))
            assertTrue(edits.isEmpty())
        }
    }

    @Test fun `failed replacement disables session with finish cleanup but never replay`() {
        start("helo")
        publish("hello")
        val id = correction()
        edits.clear()
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(id) { edits.add(it); false })
        assertEquals(listOf(TypingEdit.SetComposingText("hello"), TypingEdit.FinishComposingText), edits)
        assertFalse(controller.state.enabled)
        assertEquals("", controller.state.contextText)
        assertTrue(controller.candidateViewState.candidates.isEmpty())
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(id, execute))
        assertEquals(2, edits.size)
    }

    @Test fun `reentrant external callback during replacement wins without replay`() {
        start("helo")
        publish("hello")
        edits.clear()
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(correction()) {
            edits.add(it)
            controller.updateSelection(12, 12, -1, -1, execute)
            true
        })
        assertEquals(listOf(TypingEdit.SetComposingText("hello")), edits)
        assertNull(controller.state.composing)
        assertFalse(controller.state.enabled)
        assertTrue(controller.candidateViewState.candidates.isEmpty())
    }

    @Test fun `reentrant sensitive session cannot acquire old candidate or context`() {
        start("helo")
        publish("hello")
        edits.clear()
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(correction()) {
            edits.add(it)
            controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_PASSWORD, 0), 0, 0)
            true
        })
        assertEquals(1, edits.size)
        assertEquals("", controller.state.contextText)
        assertFalse(controller.candidateViewState.enabled)
    }

    @Test fun `reentrant owner clear without session change cannot republish a manual allowlist`() {
        start("helo")
        publish("hello")
        edits.clear()
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(correction()) {
            edits.add(it)
            controller.clearCandidates()
            true
        })
        assertEquals(listOf(TypingEdit.SetComposingText("hello"), TypingEdit.FinishComposingText), edits)
        assertFalse(controller.state.enabled)
        assertTrue(controller.candidateViewState.candidates.isEmpty())
        assertNull(controller.state.composing)
    }

    @Test fun `in flight replacement does not authorize reentrant admission or selection`() {
        start("helo")
        publish("help")
        val original = controller.originalCandidateId!!
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(correction()) {
            assertFalse(controller.ownsCandidateComposition)
            assertFalse(controller.canRequestCandidates)
            assertFalse(controller.selectOriginal(original))
            assertNull(controller.beginCandidateRequest(++requestId, KeyboardLanguage.ENGLISH))
            true
        })
        assertEquals("help", controller.state.composing!!.typedWord)
    }

    @Test fun `new request or explicit invalidation rejects an old original ID without editing`() {
        start("helo")
        publish("hello")
        val oldOriginal = controller.originalCandidateId!!
        val oldCorrection = correction()
        controller.clearCandidates()
        assertFalse(controller.selectOriginal(oldOriginal))
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(oldCorrection, execute))
        assertEquals(listOf("helo"), labels())
        val beforeRequest = controller.originalCandidateId!!
        request()
        assertFalse(controller.selectOriginal(beforeRequest))
        assertEquals(1, edits.size)
    }

    @Test fun `reply after text boundary end or new session is discarded`() {
        val actions: List<() -> Unit> = listOf(
            { controller.typeText("s", execute) }, { controller.typeText(" ", execute) },
            { controller.invalidate(execute) }, { controller.awaitEditorSelection(execute) },
            { controller.endSession() }, { start("next") },
        )
        for (action in actions) {
            start("helo")
            val request = request()
            action()
            assertFalse(controller.acceptCandidates(reply(request, "hello")))
        }
    }

    @Test fun `partial verified suggestions preserve completion without any automatic transaction`() {
        for (completion in listOf(CandidateCompletion.STATES_EXHAUSTED, CandidateCompletion.VERIFIED_EXHAUSTED)) {
            start("helo")
            val request = request()
            val result = reply(request, "hello").let { it.copy(generation = it.generation.copy(completion = completion)) }
            assertTrue(controller.acceptCandidates(result))
            assertEquals(completion, controller.candidateCompletion)
            assertTrue(result.generation.prohibitsAutoReplace)
            assertEquals(listOf("helo", "hello"), labels())
            assertEquals("helo", controller.state.composing!!.typedWord)
            assertNull(controller.state.lastAutoEdit)
        }
    }

    @Test fun `failure and valid word replies cannot inject suggestions`() {
        for (completion in listOf(CandidateCompletion.READER_FAILURE, CandidateCompletion.UNAVAILABLE,
            CandidateCompletion.VALID_WORD, CandidateCompletion.PROTECTED, CandidateCompletion.CANCELLED)) {
            start("helo")
            val request = request()
            val result = reply(request, "hello").let { it.copy(generation = it.generation.copy(completion = completion)) }
            assertFalse(controller.acceptCandidates(result))
            assertEquals(listOf("helo"), labels())
        }
    }

    @Test fun `valid lowercase proper noun can expose and apply one canonical case suggestion`() {
        start("london")
        val request = request()
        val candidate = GeneratedCandidate("London", "London", "london",
            KeyboardLanguage.ENGLISH, false, 4, 1, 0, EditFeatures(0.0, 0, 0.0), 0,
            CasePattern.TITLE, GeneratedCandidateKind.CANONICAL_CASE)
        val generation = CandidateGeneration(request.token, listOf(candidate),
            CandidateCompletion.VALID_WORD, true, null, 1, 0)
        assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
            request.requestId, generation)))
        assertEquals(listOf("london", "London"), labels())
        assertEquals(controller.originalCandidateId, controller.candidateViewState.selectedCandidateId)
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(correction(), execute))
        assertEquals("London", controller.state.composing!!.typedWord)
    }

    @Test fun `protected overlong and inactive words never enter request snapshot`() {
        for (word in listOf("A".repeat(2), "x".repeat(33), "cAmel", "aя")) {
            start(word)
            assertFalse(controller.canRequestCandidates)
            assertNull(controller.beginCandidateRequest(++requestId, KeyboardLanguage.ENGLISH))
            assertEquals(listOf(word), labels())
        }
        controller.endSession()
        assertFalse(controller.canRequestCandidates)
        assertFalse(controller.candidateViewState.enabled)
    }

    @Test fun `duplicate malformed or oversized candidate sets fail closed`() {
        for (words in listOf(arrayOf("hello", "hello"), arrayOf("helo"), arrayOf("x".repeat(33)),
            arrayOf("secret/path"), arrayOf("\uD800"), Array(8) { "hello" })) {
            start("helo")
            assertFalse(controller.acceptCandidates(reply(request(), *words)))
            assertEquals(listOf("helo"), labels())
        }
    }

    @Test fun `payload diagnostics and IDs contain no source or replacement text`() {
        start("privatetoken")
        val request = request()
        val reply = reply(request, "privateword")
        assertTrue(controller.acceptCandidates(reply))
        for (description in listOf(request.toString(), reply.toString(), controller.state.toString(),
            controller.candidateViewState.toString()) + controller.candidateViewState.candidates.map { it.toString() }) {
            assertFalse(description.contains("privatetoken"))
            assertFalse(description.contains("privateword"))
        }
        for (item in controller.candidateViewState.candidates) {
            assertFalse(item.id.contains("private"))
        }
    }

    @Test fun `actual generator uppercase expansion from eligible single letter is selectable and restorable`() {
        start("İ")
        assertTrue(controller.canRequestCandidates)
        val request = request()
        // Full finite lexicon: EN has one terminal, ES has none. No dictionary/quality claim.
        val lexicon = object : CandidateLexicon {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
                if (!control.inspectState()) return ExactMembership.UNAVAILABLE
                return if (language == KeyboardLanguage.ENGLISH && key == "in") ExactMembership.PRESENT
                else ExactMembership.ABSENT
            }

            override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
                if (!control.checkpoint()) return LexiconScanStatus.UNAVAILABLE
                if (language == KeyboardLanguage.ENGLISH) {
                    if (!control.inspectState() || !visitor.visit("in", 6)) return LexiconScanStatus.UNAVAILABLE
                }
                return if (control.checkpoint()) LexiconScanStatus.COMPLETE else LexiconScanStatus.UNAVAILABLE
            }
        }
        val generation = CandidateGenerator(lexicon).generate(request.token, request.activeLanguage)
        assertEquals(CandidateCompletion.COMPLETE, generation.completion)
        val alternative = generation.alternatives.single()
        assertEquals("IN", alternative.text)
        assertEquals(CasePattern.UPPER, alternative.casePattern)
        assertEquals(1, alternative.unitDistance)
        assertEquals(1.0, alternative.editFeatures.editCost, 0.0)
        assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
            request.requestId, generation)))
        assertEquals(listOf("İ", "IN"), labels())
        edits.clear()
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(correction(), execute))
        assertEquals(listOf(TypingEdit.SetComposingText("IN")), edits)
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(controller.originalCandidateId!!, execute))
        assertEquals("İ", controller.state.composing!!.typedWord)
        assertEquals(TypingEdit.SetComposingText("İ"), edits.last())
        assertTrue(controller.state.originalSelected)
    }

    @Test fun `uppercase output exception does not admit protected uppercase original`() {
        for (source in listOf("IN", "HTTP", "Aİ")) {
            start(source)
            assertFalse(controller.canRequestCandidates)
            assertNull(controller.beginCandidateRequest(++requestId, KeyboardLanguage.ENGLISH))
            assertEquals(listOf(source), labels())
        }
    }

    @Test fun `uppercase output exception still rejects paths identifiers lengths malformed and duplicates`() {
        for (words in listOf(arrayOf("IN/OUT"), arrayOf("IN_OUT"), arrayOf("IN@OUT"),
            arrayOf("IN2"), arrayOf("IN-А"), arrayOf("IN\uD800"), arrayOf("I".repeat(33)),
            arrayOf("IN", "IN"))) {
            start("İ")
            assertFalse(controller.acceptCandidates(reply(request(), *words)))
            assertEquals(listOf("İ"), labels())
        }
        for (source in listOf("helo", "Helo")) {
            start(source)
            assertFalse(controller.acceptCandidates(reply(request(), "HELLO")))
            assertEquals(listOf(source), labels())
        }
    }

    @Test fun `ended session releases manual source and result payload while controller stays alive`() {
        val retained = String(charArrayOf('p', 'o', 's', 'i', 't', 'i', 'v', 'e'))
        val control = WeakReference(retained)
        val refs = makeRetiredSelection()
        repeat(40) {
            if (refs.any { it.get() != null }) { System.gc(); Thread.sleep(10) }
        }
        assertTrue(refs.all { it.get() == null })
        assertSame(retained, control.get())
        assertFalse(controller.state.enabled)
    }

    private fun makeRetiredSelection(): List<WeakReference<Any>> {
        val source = String(charArrayOf('h', 'e', 'l', 'o'))
        val alternative = String(charArrayOf('h', 'e', 'l', 'l', 'o'))
        start(source)
        val request = request()
        val reply = reply(request, alternative)
        assertTrue(controller.acceptCandidates(reply))
        controller.selectCandidate(correction(), execute)
        val refs = listOf(source, alternative, request, reply, reply.generation).map { WeakReference<Any>(it) }
        controller.endSession()
        edits.clear()
        return refs
    }

    @Test fun `model snapshot includes full candidate set and only owned prefix`() {
        start("I")
        controller.typeText(" ", execute); controller.typeText("helo", execute)
        publish("hello", "help", "held", "hero", "halo", "hell", "helm")
        val before = controller.state
        val snapshot = controller.beginModelRanking(1)!!
        assertEquals("I ", snapshot.prefix)
        assertEquals(listOf("helo", "hello", "help", "held", "hero", "halo", "hell", "helm"), snapshot.continuations)
        assertEquals((0..7).toList(), snapshot.token.candidateIds)
        assertEquals(listOf("helo", "help", "held"), labels())
        assertEquals(before, controller.state)
        assertNull(controller.beginModelRanking(1))
    }

    @Test fun `model ordering keeps original and stable identities without editing`() {
        start("helo"); publish("hello", "help", "held", "hero", "halo", "hell", "helm")
        val before = controller.state
        val original = controller.originalCandidateId
        val help = correction()
        // The model may promote an alternative that was outside the visible deterministic strip.
        val input = controller.beginModelRanking(1)!!
        edits.clear()
        assertTrue(controller.acceptModelRanking(modelReply(input, 7)))
        assertEquals(listOf("helo", "helm", "hello"), labels())
        assertEquals(before, controller.state)
        assertEquals(original, controller.originalCandidateId)
        val hello = controller.candidateViewState.candidates[2].id
        assertEquals("hello", controller.candidateViewState.candidates[2].text)
        assertTrue(edits.isEmpty())
        assertFalse(controller.acceptModelRanking(modelReply(input, 1)))
        assertNull(controller.beginModelRanking(2))
        assertEquals(TypingTextResult.REJECTED, controller.selectCandidate(help, execute))
        assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(hello, execute))
        assertEquals("hello", controller.state.composing!!.typedWord)
    }

    @Test fun `model uses averages but original remains preferred below calibrated margin`() {
        start("helo"); publish("hello", "help")
        var input = controller.beginModelRanking(1)!!
        assertTrue(controller.acceptModelRanking(ScoringReply(input.token, ScoringCode.OK, 0,
            listOf(NumericScore(0, -4.0, 1), NumericScore(1, -2.0, 1), NumericScore(2, -3.0, 3)))))
        assertEquals(listOf("helo", "help", "hello"), labels())
        assertEquals(controller.originalCandidateId, controller.candidateViewState.selectedCandidateId)
        start("helo"); publish("hello", "help"); input = controller.beginModelRanking(2)!!
        assertTrue(controller.acceptModelRanking(ScoringReply(input.token, ScoringCode.OK, 0,
            input.token.candidateIds.map { NumericScore(it, -1.0, 1) })))
        assertEquals(controller.originalCandidateId, controller.candidateViewState.selectedCandidateId)
        assertFalse(controller.state.originalSelected) // only an explicit Original tap sets the veto
    }

    @Test fun `ranking rejects every changed token identity and then accepts current reply once`() {
        start("helo"); publish("hello", "help")
        val input = controller.beginModelRanking(1)!!
        val t = input.token
        for (wrong in listOf(ScoringToken(t.sessionId + 1, t.revision, t.requestId, t.candidateIds),
            ScoringToken(t.sessionId, t.revision + 1, t.requestId, t.candidateIds),
            ScoringToken(t.sessionId, t.revision, t.requestId + 1, t.candidateIds),
            ScoringToken(t.sessionId, t.revision, t.requestId, listOf(0, 2, 1)))) {
            assertFalse(controller.acceptModelRanking(ScoringReply(wrong, ScoringCode.OK, 0,
                wrong.candidateIds.map { NumericScore(it, -1.0, 1) })))
        }
        assertTrue(controller.acceptModelRanking(modelReply(input, 2)))
        assertFalse(controller.acceptModelRanking(modelReply(input, 1)))
    }

    @Test fun `ranking cancellation text edits original taps and errors preserve deterministic fallback`() {
        for (action in 0..4) {
            start("helo"); publish("hello", "help")
            val input = controller.beginModelRanking((action + 1).toLong())!!
            when (action) {
                0 -> controller.cancelModelRanking()
                1 -> controller.typeText("s", execute)
                2 -> controller.selectOriginal(controller.originalCandidateId!!)
                3 -> controller.endSession()
                else -> assertFalse(controller.acceptModelRanking(ScoringReply(input.token, ScoringCode.UNAVAILABLE, 0, emptyList())))
            }
            val before = controller.candidateViewState.candidates
            assertFalse(controller.acceptModelRanking(modelReply(input, 2)))
            assertEquals(before, controller.candidateViewState.candidates)
        }
    }

    @Test fun `combined ordering can reject the raw model favorite using generated features`() {
        start("helo")
        val request = request()
        val response = reply(request, "hello", "help")
        val alternatives = response.generation.alternatives.mapIndexed { index, candidate ->
            if (index == 0) candidate.copy(frequencyRank = 32768, editFeatures = EditFeatures(2.0, 0, 0.0)) else candidate
        }
        assertTrue(controller.acceptCandidates(response.copy(generation = response.generation.copy(alternatives = alternatives))))
        val input = controller.beginModelRanking(1)!!
        edits.clear()
        assertTrue(controller.acceptModelRanking(modelReply(input, 1)))
        assertEquals(listOf("helo", "help", "hello"), labels())
        assertEquals(controller.candidateViewState.candidates[1].id, controller.candidateViewState.selectedCandidateId)
        assertTrue(edits.isEmpty())
        controller.typeText(" ", execute)
        assertEquals("helo ", controller.state.contextText) // Calibration alone never enables AutoReplace.
    }

    @Test fun `request language fixes coefficients without inferring language from candidate output`() {
        for ((index, language) in listOf(KeyboardLanguage.ENGLISH, KeyboardLanguage.RUSSIAN, KeyboardLanguage.SPANISH).withIndex()) {
            start("helo")
            val request = controller.beginCandidateRequest(++requestId, language)!!
            assertTrue(controller.acceptCandidates(reply(request, "hello", "help")))
            val input = controller.beginModelRanking((index + 1).toLong())!!
            assertTrue(controller.acceptModelRanking(modelReply(input, 1)))
            val view = controller.candidateViewState
            assertEquals(if (language == KeyboardLanguage.ENGLISH) view.candidates[1].id else controller.originalCandidateId,
                view.selectedCandidateId)
            assertEquals("helo", controller.state.composing?.typedWord)
        }
    }

    @Test fun `partial generation may reorder suggestions but cannot select a calibrated winner`() {
        for ((index, completion) in listOf(CandidateCompletion.STATES_EXHAUSTED, CandidateCompletion.VERIFIED_EXHAUSTED).withIndex()) {
            start("helo")
            val response = reply(request(), "hello", "help")
            assertTrue(controller.acceptCandidates(response.copy(generation = response.generation.copy(completion = completion))))
            val input = controller.beginModelRanking((index + 1).toLong())!!
            assertTrue(controller.acceptModelRanking(modelReply(input, 1)))
            assertEquals(listOf("helo", "hello", "help"), labels())
            assertEquals(controller.originalCandidateId, controller.candidateViewState.selectedCandidateId)
            assertEquals(completion, controller.candidateCompletion)
            assertNull(controller.state.lastAutoEdit)
        }
    }

    private fun modelReply(input: ScoringInput, winner: Int) = ScoringReply(input.token, ScoringCode.OK, 0,
        input.token.candidateIds.map { NumericScore(it, if (it == winner) -1.0 else -10.0, 1) })

    private fun start(word: String) {
        controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0)
        edits.clear()
        controller.typeText(word, execute)
    }

    private fun request(): LocalCandidateRequest = checkNotNull(
        controller.beginCandidateRequest(++requestId, KeyboardLanguage.ENGLISH),
    )

    private fun publish(vararg words: String) {
        assertTrue(controller.acceptCandidates(reply(request(), *words)))
    }

    private fun labels() = controller.candidateViewState.candidates.map { it.text }
    private fun correction() = controller.candidateViewState.candidates[1].id

    private fun reply(request: LocalCandidateRequest, vararg words: String): LocalCandidateReply {
        val alternatives = words.map { word ->
            // Intentionally permit malformed display fixtures without invoking the distance engine.
            val key = if (TokenUnicode.bounded(word)) TokenUnicode.folded(word) else "invalid"
            GeneratedCandidate(word, key, key,
                KeyboardLanguage.ENGLISH, false, 4, 1, 1, EditFeatures(1.0, 0, 0.0),
                kotlin.math.abs(word.length - request.token.length), CasePattern.analyze(request.token))
        }
        return LocalCandidateReply(request.sessionId, request.revision, request.requestId,
            CandidateGeneration(request.token, alternatives, CandidateCompletion.COMPLETE,
                false, null, 10, words.size))
    }
}
