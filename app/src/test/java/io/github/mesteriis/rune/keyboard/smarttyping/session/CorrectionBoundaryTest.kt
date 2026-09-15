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
import java.lang.reflect.Proxy
import org.junit.Assert.*
import org.junit.Test

/** Real owner/executor with an independent editor document. Synthetic quality admission only. */
class CorrectionBoundaryTest {
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
        Triple(KeyboardLanguage.ENGLISH, "teh", "the"),
        Triple(KeyboardLanguage.ENGLISH, "recieve", "receive"),
        Triple(KeyboardLanguage.ENGLISH, "adress", "address"),
        Triple(KeyboardLanguage.SPANISH, "mensage", "mensaje"),
        Triple(KeyboardLanguage.SPANISH, "correcion", "corrección"),
    )

    private class Fixture(qualified: Boolean? = true, modelOnly: Boolean = false, initial: String = "") {
        val controller = TypingSessionController(jvmGraphemes, qualified?.let { allowed ->
            SpellingQualification { _, model -> allowed && (!modelOnly || model == SpellingSource.MODEL) }
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
            val request = controller.beginCandidateRequest(++requestId, keyboard.language)!!
            val item = GeneratedCandidate(word, word, TokenUnicode.folded(word), keyboard.language,
                false, 4, 1, 0, EditFeatures(0.0, 0, 0.0), 0, CasePattern.TITLE,
                GeneratedCandidateKind.CANONICAL_CASE, canonicalCaseUnambiguous = unambiguous,
                canonicalCaseAutoEligible = eligible)
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
                request.requestId, CandidateGeneration(request.token, listOf(item),
                    CandidateCompletion.VALID_WORD, true, null, 1, 0))))
        }
    }
}
