package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import java.lang.reflect.Proxy
import org.junit.Assert.*
import org.junit.Test

/** Real owner/executor with an independent editor document. Synthetic quality admission only. */
class CorrectionBoundaryTest {
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
            Triple(KeyboardLanguage.ENGLISH, "Cafe\u0301ss", "Cafés"),
            Triple(KeyboardLanguage.RUSSIAN, "Превет", "Привет"),
            Triple(KeyboardLanguage.SPANISH, "holaa", "hola"))) {
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

    @Test fun `missing model uses ready deterministic decision and late callback cannot rewrite boundary`() {
        val f = Fixture(); f.raw("helllo"); f.publish("hello")
        val pending = f.controller.beginModelRanking(1)!!
        f.type(" ")
        assertEquals("hello ", f.document)
        f.calls.clear()
        assertFalse(f.controller.acceptModelRanking(ScoringReply(pending.token, ScoringCode.OK, 0,
            listOf(NumericScore(0, -100.0, 1), NumericScore(1, -1.0, 1)))))
        assertTrue(f.calls.isEmpty()); assertEquals("hello ", f.document)
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
        val veto = Fixture(); veto.raw("helllo"); veto.publish("hello")
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

    @Test fun `canonical case auto replaces on boundary and Undo restores lowercase original`() {
        for (unambiguous in listOf(true, false)) {
            val f = Fixture(qualified = false)
            f.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
            f.raw("москва")
            f.publishCanonical("Москва", unambiguous)

            assertEquals(TypingTextResult.HANDLED, f.type(" "))
            assertEquals("Москва ", f.document)
            assertNotNull(f.controller.state.lastAutoEdit)
            assertEquals(TypingTextResult.HANDLED, f.undo())
            assertEquals("москва", f.document)
            assertEquals("москва", f.controller.state.composing?.typedWord)
            assertTrue(f.controller.state.originalSelected)
        }
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

    private class Fixture(qualified: Boolean? = true, modelOnly: Boolean = false, initial: String = "") {
        val controller = TypingSessionController(jvmGraphemes, qualified?.let { allowed ->
            SpellingQualification { _, model -> allowed && (!modelOnly || model) }
        } ?: SpellingQualification.CURRENT)
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
        fun publish(word: String, completion: CandidateCompletion = CandidateCompletion.COMPLETE) {
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val item = GeneratedCandidate(word, TokenUnicode.folded(word), TokenUnicode.folded(word), keyboard.language,
                false, 4, 1, 1, EditFeatures(1.0, 0, 0.0),
                kotlin.math.abs(word.length - request.token.length), CasePattern.analyze(request.token))
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(item), completion, false, null, 1, 1))))
        }
        fun publishCanonical(word: String, unambiguous: Boolean) {
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val item = GeneratedCandidate(word, word, TokenUnicode.folded(word), keyboard.language,
                false, 4, 1, 0, EditFeatures(0.0, 0, 0.0), 0, CasePattern.TITLE,
                GeneratedCandidateKind.CANONICAL_CASE, canonicalCaseUnambiguous = unambiguous)
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
                request.requestId, CandidateGeneration(request.token, listOf(item),
                    CandidateCompletion.VALID_WORD, true, null, 1, 0))))
        }
    }
}
