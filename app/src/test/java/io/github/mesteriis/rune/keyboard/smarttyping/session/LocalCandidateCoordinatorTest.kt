package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.text.InputType
import android.view.inputmethod.EditorInfo
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessSource
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.NumericScore
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.TopCandidateSelection
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateSearchControl
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateVisitor
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.ExactMembership
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRoute
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LexiconScanStatus
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Test

class LocalCandidateCoordinatorTest {
    @Test fun `loading requests only enum route and readiness or render cannot submit saved text`() {
        Harness(ready = false).use { h ->
            h.type("helo")
            assertEquals(1, h.routeRequests)
            assertEquals(KeyboardLanguage.ENGLISH, h.lastRoute?.primary)
            assertEquals(KeyboardLanguage.SPANISH, h.lastRoute?.fallback)
            assertEquals(0, h.lexicon.exactCalls.get())
            repeat(5) { assertEquals(listOf("helo"), h.labels()) }
            h.ready = true
            repeat(5) { h.coordinator.viewState }
            assertEquals(0, h.lexicon.exactCalls.get())
            h.type("s")
            h.deliver()
            assertEquals(1, h.published)
            assertEquals(2, h.routeRequests)
        }
    }

    @Test fun `each accepted composing edit requests once and render never resubmits`() {
        Harness().use { h ->
            h.type("helo")
            h.deliver()
            assertEquals(listOf("helo", "help", "hello"), h.labels())
            assertEquals(1, h.routeRequests)
            assertEquals(1, h.published)
            repeat(5) { h.coordinator.viewState }
            assertEquals(1, h.routeRequests)
            h.coordinator.edit { TypingTextResult.HANDLED }
            assertEquals(1, h.routeRequests)
            h.type("s")
            h.deliver()
            assertEquals(2, h.routeRequests)
        }
    }

    @Test fun `pending boundary does not query and late load never infers an old word`() {
        Harness(ready = false).use { h ->
            h.type("helo")
            h.type(" ")
            assertEquals(1, h.routeRequests)
            assertTrue(h.invalidatedLoads > 0)
            h.ready = true
            assertTrue(h.coordinator.viewState.candidates.isEmpty())
            assertEquals(0, h.lexicon.exactCalls.get())
            h.type("helo")
            h.deliver()
            assertEquals(listOf("helo", "help", "hello"), h.labels())
            assertEquals("helo helo", h.controller.state.contextText)
        }
    }

    @Test fun `failed bypass and empty edits cannot schedule candidates`() {
        Harness().use { h ->
            h.coordinator.edit { h.controller.typeText("helo") { false } }
            assertEquals(0, h.routeRequests)
            h.type("x")
            assertEquals(0, h.routeRequests)
        }
        Harness().use { h ->
            h.coordinator.edit { h.controller.typeText("", h.execute) }
            assertEquals(0, h.routeRequests)
        }
    }

    @Test fun `original tap cancels active work without clearing current original allowlist`() {
        Harness().use { h ->
            h.lexicon.hold = Hold()
            h.type("helo")
            h.lexicon.hold!!.entered.awaitChecked()
            val original = h.coordinator.viewState.candidates.single().id
            h.commands.clear()
            assertEquals(TypingTextResult.HANDLED, h.coordinator.selectCandidate(original, h.execute))
            h.lexicon.hold!!.stopped.awaitChecked()
            assertTrue(h.commands.isEmpty())
            assertTrue(h.controller.state.originalSelected)
            assertEquals(listOf("helo"), h.labels())
            h.type("s")
            assertEquals(1, h.routeRequests)
        }
    }

    @Test fun `manual correction then Original restores exact segment without a second generation`() {
        Harness().use { h ->
            h.type("a")
            h.type(" ")
            h.type("helo")
            h.deliver()
            val requests = h.routeRequests
            val correction = h.coordinator.viewState.candidates.single { it.text == "hello" }.id
            h.commands.clear()
            assertEquals(TypingTextResult.HANDLED, h.coordinator.selectCandidate(correction, h.execute))
            assertEquals(listOf(TypingEdit.SetComposingText(" hello")), h.commands)
            assertEquals(listOf("helo", "help", "hello"), h.labels())
            assertEquals(TypingTextResult.HANDLED,
                h.coordinator.selectCandidate(h.coordinator.viewState.candidates[0].id, h.execute))
            assertEquals("a helo", h.controller.state.contextText)
            assertEquals(requests, h.routeRequests)
            assertNull(h.controller.state.lastAutoEdit)
        }
    }

    @Test fun `stale tap does not cancel the latest active request`() {
        Harness().use { h ->
            h.type("helo")
            h.deliver()
            val stale = h.coordinator.viewState.candidates[1].id
            h.lexicon.hold = Hold()
            h.type("s")
            h.lexicon.hold!!.entered.awaitChecked()
            assertEquals(TypingTextResult.REJECTED, h.coordinator.selectCandidate(stale, h.execute))
            h.lexicon.hold!!.release.countDown()
            h.deliver()
            assertEquals(2, h.published)
            assertEquals("helos", h.labels().first())
        }
    }

    @Test fun `replacement cancels active and serially delivers only the latest edit`() {
        Harness().use { h ->
            val hold = Hold()
            h.lexicon.hold = hold
            h.type("helo")
            hold.entered.awaitChecked()
            h.type("s")
            hold.stopped.awaitChecked()
            hold.release.countDown()
            h.deliver()
            assertEquals(1, h.published)
            assertEquals("helos", h.labels().first())
            assertEquals(1, h.lexicon.maximumConcurrent.get())
        }
    }

    @Test fun `queued callback after owner invalidation cannot publish`() {
        Harness().use { h ->
            h.type("helo")
            h.awaitQueued()
            h.coordinator.invalidate()
            h.drain()
            assertEquals(0, h.published)
            assertEquals(listOf("helo"), h.labels())
            assertTrue(h.invalidatedLoads > 0)
        }
    }

    @Test fun `queued callback after close cannot retain presentation or recreate worker`() {
        Harness().use { h ->
            h.type("helo")
            h.awaitQueued()
            h.coordinator.close()
            h.drain()
            assertEquals(0, h.published)
            assertFalse(h.coordinator.viewState.enabled)
            assertEquals(1, h.closedLoads)
            h.type("s")
            assertEquals(1, h.routeRequests)
        }
    }

    @Test fun `callback checks current language even if an external caller omitted invalidation`() {
        Harness().use { h ->
            h.type("helo")
            h.awaitQueued()
            h.owner = h.owner.copy(language = KeyboardLanguage.RUSSIAN)
            h.drain()
            assertEquals(0, h.published)
            assertEquals(listOf("helo"), h.labels())
        }
    }

    @Test fun `callback checks view layer selection privacy and ready route again`() {
        val changes: List<(Harness) -> Unit> = listOf(
            { it.owner = it.owner.copy(inputViewActive = false) },
            { it.owner = it.owner.copy(layer = KeyboardLayer.SYMBOLS) },
            { it.owner = it.owner.copy(hasSelection = true) },
            { it.owner = it.owner.copy(editorAllowsSmartTyping = false) },
            { it.ready = false },
        )
        for (change in changes) Harness().use { h ->
            h.type("helo")
            h.awaitQueued()
            change(h)
            h.drain()
            assertEquals(0, h.published)
            assertEquals(1, h.routeRequests)
            assertTrue(h.coordinator.viewState.candidates.size <= 1)
        }
    }

    @Test fun `controller revision composition session and original veto are rechecked on delivery`() {
        val changes: List<(Harness) -> Unit> = listOf(
            { it.controller.typeText("s", it.execute) },
            { it.controller.finishComposition(it.execute) },
            { it.controller.endSession() },
            { it.controller.selectOriginal(it.controller.originalCandidateId!!) },
            { it.controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0) },
        )
        for (change in changes) Harness().use { h ->
            h.type("helo")
            h.awaitQueued()
            change(h)
            h.drain()
            assertEquals(0, h.published)
        }
    }

    @Test fun `real editor policy rejects password NPL raw and nontext admissions`() {
        val editors = listOf(
            EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD, 0),
            EditorContext.from(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING),
            EditorContext.from(InputType.TYPE_NULL, 0),
            EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS, 0),
            EditorContext.from(InputType.TYPE_CLASS_NUMBER, 0),
        )
        for (editor in editors) Harness().use { h ->
            h.owner = h.owner.copy(editorAllowsSmartTyping = editor.supportsSmartTyping)
            h.controller.startSession(editor, 0, 0)
            h.type("helo")
            assertEquals(0, h.routeRequests)
            assertEquals(0, h.lexicon.exactCalls.get())
            assertFalse(h.coordinator.viewState.enabled)
        }
    }

    @Test fun `protected overlong sources and absent input view never start loads`() {
        for (word in listOf("HTTP", "cAmel", "x".repeat(33), "aя")) Harness().use { h ->
            h.type(word)
            assertEquals(0, h.routeRequests)
            assertEquals(listOf(word), h.labels())
        }
        Harness().use { h ->
            h.owner = h.owner.copy(inputViewActive = false)
            h.type("helo")
            assertEquals(0, h.routeRequests)
        }
    }

    @Test fun `own selection acknowledgment during edit does not invalidate or starve the result`() {
        Harness().use { h ->
            h.coordinator.edit {
                h.controller.typeText("helo") {
                    assertFalse(h.controller.updateSelection(4, 4, 0, 4, h.execute))
                    true
                }
            }
            h.deliver()
            assertEquals(1, h.published)
        }
    }

    @Test fun `reentrant lifecycle boundary after command does not submit into the next session`() {
        Harness().use { h ->
            h.coordinator.edit {
                h.controller.typeText("helo") {
                    h.coordinator.invalidate()
                    h.controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0)
                    true
                }
            }
            assertEquals(0, h.routeRequests)
            assertTrue(h.labels().isEmpty())
        }
    }

    @Test fun `reader failure then next valid edit succeeds without replacing worker`() {
        Harness().use { h ->
            h.lexicon.fail = true
            h.type("helo")
            h.deliver()
            assertEquals(listOf("helo"), h.labels())
            h.lexicon.fail = false
            h.type("s")
            h.deliver()
            assertTrue(h.labels().size > 1)
            assertEquals(2, h.published)
        }
    }

    @Test fun `all six mode and strip combinations admit only the current manual consumer`() {
        for (mode in AutocorrectionMode.entries) for (strip in listOf(false, true)) Harness().use { h ->
            h.configure(mode, strip)
            h.type("helo")
            val work = mode != AutocorrectionMode.OFF && strip
            if (work) h.deliver()
            assertEquals(if (work) 1 else 0, h.routeRequests)
            assertEquals(if (work) 2 else 0, h.lexicon.exactCalls.get())
            assertEquals(if (work) 1 else 0, h.published)
            assertEquals(listOf(TypingEdit.SetComposingText("helo")), h.commands)
            assertEquals(strip, h.coordinator.viewState.enabled)
            assertEquals(if (!strip) emptyList() else if (work) listOf("helo", "help", "hello") else listOf("helo"), h.labels())
            val view = h.coordinator.viewState
            assertTrue(view.selectedCandidateId == null || view.candidates.any { it.id == view.selectedCandidateId })
            assertNull(h.controller.state.lastAutoEdit)
        }
    }

    @Test fun `disable policy cancels blocked search preserves composition and rejects stale correction`() {
        for (disableMode in listOf(true, false)) Harness().use { h ->
            h.type("helo"); h.deliver()
            val stale = h.coordinator.viewState.candidates[1].id
            val hold = Hold(); h.lexicon.hold = hold
            h.type("s"); hold.entered.awaitChecked()
            val before = h.controller.state
            h.commands.clear()
            h.configure(if (disableMode) AutocorrectionMode.OFF else AutocorrectionMode.SUGGESTIONS, disableMode)
            hold.stopped.awaitChecked(); hold.release.countDown()
            h.drain()
            assertEquals(1, h.published)
            assertEquals(before, h.controller.state)
            assertEquals(TypingTextResult.REJECTED, h.coordinator.selectCandidate(stale, h.execute))
            assertTrue(h.commands.isEmpty())
            assertEquals(if (disableMode) listOf("helos") else emptyList(), h.labels())
        }
    }

    @Test fun `queued reply checks disabled mode and strip even without caller invalidation`() {
        for (modeOff in listOf(true, false)) Harness().use { h ->
            h.type("helo"); h.awaitQueued()
            h.owner = h.owner.copy(autocorrectionMode = if (modeOff) AutocorrectionMode.OFF else AutocorrectionMode.SUGGESTIONS,
                candidateStripEnabled = modeOff)
            h.drain()
            assertEquals(0, h.published)
            assertEquals(if (modeOff) listOf("helo") else emptyList(), h.labels())
        }
    }

    @Test fun `enable and Ready and rendering wait for the next accepted composing edit`() {
        for (modeOff in listOf(true, false)) Harness(ready = false).use { h ->
            h.configure(if (modeOff) AutocorrectionMode.OFF else AutocorrectionMode.SUGGESTIONS, modeOff)
            h.type("helo")
            h.configure(AutocorrectionMode.HIGH_CONFIDENCE, true)
            h.ready = true
            repeat(5) { h.coordinator.viewState }
            assertEquals(0, h.routeRequests); assertEquals(0, h.lexicon.exactCalls.get())
            h.type("s"); h.deliver()
            assertEquals(1, h.routeRequests); assertEquals(2, h.lexicon.exactCalls.get())
            assertEquals(listOf("helos", "hellos"), h.labels())
        }
    }

    @Test fun `OFF Original after manual correction keeps the currently displayed composing word`() {
        Harness().use { h ->
            h.type("helo"); h.deliver()
            val correction = h.coordinator.viewState.candidates.single { it.text == "hello" }.id
            assertEquals(TypingTextResult.HANDLED, h.coordinator.selectCandidate(correction, h.execute))
            h.commands.clear()
            h.configure(AutocorrectionMode.OFF, true)
            assertEquals(listOf("hello"), h.labels())
            assertEquals(h.coordinator.viewState.candidates.single().id, h.coordinator.viewState.selectedCandidateId)
            assertEquals(TypingTextResult.REJECTED, h.coordinator.selectCandidate(correction, h.execute))
            assertEquals(TypingTextResult.HANDLED,
                h.coordinator.selectCandidate(h.coordinator.viewState.candidates.single().id, h.execute))
            assertEquals("hello", h.controller.state.contextText)
            assertTrue(h.commands.isEmpty()); assertEquals(1, h.routeRequests)
        }
    }

    @Test fun `unfiltered controller allowlist cannot bypass current spelling or strip policy`() {
        for (modeOff in listOf(true, false)) Harness().use { h ->
            h.type("helo"); h.deliver()
            val correction = h.coordinator.viewState.candidates[1].id
            h.owner = h.owner.copy(autocorrectionMode = if (modeOff) AutocorrectionMode.OFF else AutocorrectionMode.SUGGESTIONS,
                candidateStripEnabled = modeOff)
            h.commands.clear()
            assertEquals(TypingTextResult.REJECTED, h.coordinator.selectCandidate(correction, h.execute))
            assertTrue(h.commands.isEmpty())
            assertEquals("helo", h.controller.state.contextText)
        }
    }

    @Test fun `spelling settings preserve mechanical transaction and its immediate raw Undo`() {
        for (mode in AutocorrectionMode.entries) for (strip in listOf(false, true)) Harness(ready = false).use { h ->
            h.type("hello"); h.type(" "); h.type(",")
            h.coordinator.edit { h.controller.typeText("world",
                MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, false),
                KeyboardState(KeyboardLanguage.ENGLISH), execute = h.execute) }
            assertEquals("hello, world", h.controller.state.contextText)
            val undo = h.controller.state.lastAutoEdit
            assertNotNull(undo)
            h.commands.clear(); h.configure(mode, strip)
            assertEquals(undo, h.controller.state.lastAutoEdit); assertTrue(h.commands.isEmpty())
            h.coordinator.edit { h.controller.deletePrevious(h.execute) }
            assertEquals("hello ,world", h.controller.state.contextText)
            assertEquals(listOf(TypingEdit.SetComposingText(" ,world")), h.commands)
        }
    }

    @Test fun `base ownership guard wins across every mode and strip combination`() {
        for (mode in AutocorrectionMode.entries) for (strip in listOf(false, true)) {
            for (change in listOf<(CandidateOwnerState) -> CandidateOwnerState>(
                { it.copy(editorAllowsSmartTyping = false) }, { it.copy(inputViewActive = false) },
                { it.copy(hasSelection = true) }, { it.copy(layer = KeyboardLayer.SYMBOLS) })) Harness().use { h ->
                h.configure(mode, strip); h.owner = change(h.owner); h.type("helo")
                assertEquals(0, h.routeRequests); assertEquals(0, h.lexicon.exactCalls.get())
                assertFalse(h.coordinator.viewState.enabled)
            }
        }
    }

    @Test fun `production coordinator requests four total candidates before search and model submission`() {
        Harness(withModel = true).use { h ->
            h.lexicon.extraNeighbors = true
            h.type("helo"); h.deliver(); h.pause.fire()
            val request = h.model.requests.single()
            assertEquals("helo", request.continuations.first())
            assertEquals(4, request.continuations.size)
            assertEquals(listOf(0, 1, 2, 3), request.token.candidateIds)
            assertEquals(3, h.coordinator.viewState.candidates.size)
            assertEquals(listOf(3), h.lexicon.requestedWidths.toList())
        }
    }

    @Test fun `local generation renders before model pause then numeric reply reorders without editor work`() {
        Harness(withModel = true).use { h ->
            h.type("helo"); h.deliver()
            assertEquals(listOf("helo", "help", "hello"), h.labels())
            assertTrue(h.model.requests.isEmpty())
            assertEquals(400L, h.pause.delay)
            h.pause.fire()
            val request = h.model.requests.single()
            assertEquals(listOf("helo", "help", "hello"), request.continuations)
            h.commands.clear()
            h.model.reply(request, 2)
            assertEquals(listOf("helo", "hello", "help"), h.labels())
            assertTrue(h.commands.isEmpty())
            assertEquals(2, h.published)
            h.model.reply(request, 1)
            assertEquals(2, h.published)
            repeat(3) { h.coordinator.viewState }
            assertEquals(1, h.model.requests.size)
        }
    }

    @Test fun `typing retires pause and stale model callbacks cannot cross word boundary`() {
        Harness(withModel = true).use { h ->
            h.type("helo"); h.deliver()
            val retired = h.pause.task!!
            h.type("s"); retired.run()
            assertTrue(h.model.requests.isEmpty())
            h.deliver(); h.pause.fire()
            val input = h.model.requests.single()
            h.type(" ")
            val view = h.labels(); val count = h.published
            h.model.reply(input, 1)
            assertEquals(view, h.labels()); assertEquals(count, h.published)
            assertEquals("helos ", h.controller.state.contextText)
            assertNull(h.pause.task)
        }
    }

    @Test fun `model readiness connection and render never replay old composition`() {
        Harness(withModel = true).use { h ->
            h.modelReady = false
            h.type("helo"); h.deliver()
            assertNull(h.pause.task); assertTrue(h.model.attachments.none { it.second })
            h.modelReady = true; h.model.listener.onAvailabilityChanged(true)
            assertNull(h.pause.task); assertTrue(h.model.requests.isEmpty())
            h.type("s"); h.deliver(); h.model.available = false; h.pause.fire()
            assertTrue(h.model.requests.isEmpty())
            h.model.available = true; h.model.listener.onAvailabilityChanged(true)
            assertTrue(h.model.requests.isEmpty())
        }
    }

    @Test fun `original tap policy change and language change reject pending model results`() {
        for (mode in 0..3) Harness(withModel = true).use { h ->
            h.type("helo"); h.deliver(); h.pause.fire()
            val input = h.model.requests.single()
            when (mode) {
                0 -> h.coordinator.selectCandidate(h.coordinator.viewState.candidates[0].id, h.execute)
                1 -> h.configure(AutocorrectionMode.OFF, true)
                2 -> h.owner = h.owner.copy(language = KeyboardLanguage.RUSSIAN)
                else -> h.owner = h.owner.copy(editorAllowsSmartTyping = false)
            }
            val before = h.labels(); val count = h.published
            h.model.reply(input, 2)
            assertEquals(before, h.labels()); assertEquals(count, h.published)
        }
    }

    @Test fun `valid word has no model demand and close retires delayed work`() {
        Harness(withModel = true).use { valid ->
            valid.type("hello"); valid.deliver()
            assertTrue(valid.model.attachments.none { it.second })
        }
        val h = Harness(withModel = true)
        h.type("helo"); h.deliver()
        val retired = checkNotNull(h.pause.task)
        h.close(); retired.run()
        assertTrue(h.model.closed); assertTrue(h.model.requests.isEmpty())
    }

    @Test fun `stale missing model error cannot detach a newer request`() {
        Harness(withModel = true).use { h ->
            h.type("helo"); h.deliver(); h.pause.fire()
            val old = h.model.requests.single()
            h.type("s"); h.deliver(); h.pause.fire()
            val current = h.model.requests.last()
            val attempts = h.model.attachments.size
            h.model.listener.onReply(ScoringReply(old.token, ScoringCode.NO_MODEL, 0, emptyList()))
            assertEquals(attempts, h.model.attachments.size)
            assertTrue(h.model.attachments.last().second)
            h.model.listener.onReply(ScoringReply(current.token, ScoringCode.NO_MODEL, 0, emptyList()))
            assertFalse(h.model.attachments.last().second)
            val published = h.published
            h.model.reply(current, 1)
            assertEquals(published, h.published)
        }
    }

    private class Pause : ModelPauseScheduler {
        var task: Runnable? = null
        var delay = 0L
        override fun postDelayed(task: Runnable, millis: Long) { check(this.task == null); this.task = task; delay = millis }
        override fun remove(task: Runnable) { if (this.task === task) this.task = null }
        fun fire() { val next = task; task = null; next?.run() }
    }
    private class FakeModel : ModelScoringClient {
        lateinit var listener: ModelScoringListener
        val requests = mutableListOf<ScoringInput>()
        val attachments = mutableListOf<Pair<Long?, Boolean>>()
        var closed = false
        override var available = true
        override fun attachSession(sessionId: Long?, effectiveAvailability: Boolean) { attachments += sessionId to effectiveAvailability }
        override fun score(input: ScoringInput) { requests += input }
        override fun cancel() = Unit
        override fun close() { closed = true }
        fun reply(input: ScoringInput, winner: Int) = listener.onReply(ScoringReply(input.token, ScoringCode.OK, 0,
            input.token.candidateIds.map { NumericScore(it, if (it == winner) -1.0 else -10.0, 1) }))
    }

    private class Harness(ready: Boolean = true, withModel: Boolean = false) : AutoCloseable {
        val controller = TypingSessionController(jvmGraphemes)
        val lexicon = FixtureLexicon()
        var ready = ready
        var routeRequests = 0
        var invalidatedLoads = 0
        var closedLoads = 0
        var published = 0
        var lastRoute: LanguageRoute? = null
        var owner = CandidateOwnerState(true, true, KeyboardLayer.LETTERS, KeyboardLanguage.ENGLISH, false)
        var modelReady = true
        val model = FakeModel()
        val pause = Pause()
        private val ranking = if (withModel) ModelCandidateCoordinator(controller,
            { model.listener = it; model }, pause, { owner }, object : ModelReadinessSource {
                override val hint get() = if (modelReady) ModelReadinessHint.READY else ModelReadinessHint.MISSING
                override fun setActive(active: Boolean) = Unit
                override fun close() = Unit
            }, { published++ }) else null
        val commands = mutableListOf<TypingEdit>()
        val execute: (TypingEdit) -> Boolean = { commands.add(it); true }
        private val queue = ConcurrentLinkedQueue<Runnable>()
        val coordinator = LocalCandidateCoordinator(controller, lexicon,
            { routeRequests++; lastRoute = it; this.ready }, { this.ready },
            { invalidatedLoads++ }, { closedLoads++ }, Executor { queue.add(it) },
            { owner }, { published++ }, ranking)

        init { controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0) }
        fun configure(mode: AutocorrectionMode, strip: Boolean) {
            val next = owner.copy(autocorrectionMode = mode, candidateStripEnabled = strip)
            if (next != owner) { owner = next; coordinator.invalidate() }
        }
        fun type(value: String) = coordinator.edit { controller.typeText(value, execute) }
        fun labels() = coordinator.viewState.candidates.map { it.text }
        fun awaitQueued() = eventually { queue.isNotEmpty() }
        fun drain() { while (true) (queue.poll() ?: return).run() }
        fun deliver() {
            val next = published + 1
            eventually { drain(); published >= next }
        }
        override fun close() { coordinator.close(); lexicon.hold?.release?.countDown(); drain() }
    }

    private class Hold {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val stopped = CountDownLatch(1)
    }

    private class FixtureLexicon : CandidateLexicon {
        val exactCalls = AtomicInteger()
        val maximumConcurrent = AtomicInteger()
        private val concurrent = AtomicInteger()
        @Volatile var hold: Hold? = null
        @Volatile var fail = false
        @Volatile var extraNeighbors = false
        val requestedWidths = ConcurrentLinkedQueue<Int>()

        override fun selectTop(key: String, route: LanguageRoute, pattern: CasePattern,
            control: CandidateSearchControl, maximumAlternatives: Int): TopCandidateSelection? {
            requestedWidths.add(maximumAlternatives)
            return null // Exercise the real generator's generic fallback after checking admission width.
        }

        override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
            exactCalls.incrementAndGet()
            if (!control.inspectState()) return ExactMembership.UNAVAILABLE
            if (fail) throw IllegalStateException("public fixture failure")
            return ExactMembership.ABSENT
        }

        override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
            control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
            val active = concurrent.incrementAndGet()
            maximumConcurrent.accumulateAndGet(active, ::maxOf)
            try {
                hold?.let { gate ->
                    gate.entered.countDown()
                    while (!gate.release.await(5, TimeUnit.MILLISECONDS)) {
                        if (!control.checkpoint()) { gate.stopped.countDown(); return LexiconScanStatus.UNAVAILABLE }
                    }
                }
                // Valid radius neighbors for the only tested spellings. Each language emits once.
                val words = when (key) {
                    "helo" -> if (extraNeighbors) listOf("hello", "help", "held", "hero", "halo", "hell", "helm") else listOf("hello", "help")
                    "helos" -> listOf("hellos")
                    else -> emptyList()
                }
                for ((index, word) in words.withIndex()) {
                    if (!control.inspectState() || !visitor.visit(word, index + 1)) return LexiconScanStatus.UNAVAILABLE
                }
                return if (control.checkpoint()) LexiconScanStatus.COMPLETE else LexiconScanStatus.UNAVAILABLE
            } finally { concurrent.decrementAndGet() }
        }
    }

    private companion object {
        fun CountDownLatch.awaitChecked() { assertTrue("Worker checkpoint did not arrive", await(3, TimeUnit.SECONDS)) }
        fun eventually(condition: () -> Boolean) {
            val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
            while (!condition() && System.nanoTime() < end) Thread.sleep(5)
            assertTrue("Owner delivery did not arrive", condition())
        }
    }
}
