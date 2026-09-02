package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.text.InputType
import android.view.inputmethod.EditorInfo
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
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

    private class Harness(ready: Boolean = true) : AutoCloseable {
        val controller = TypingSessionController(jvmGraphemes)
        val lexicon = FixtureLexicon()
        var ready = ready
        var routeRequests = 0
        var invalidatedLoads = 0
        var closedLoads = 0
        var published = 0
        var lastRoute: LanguageRoute? = null
        var owner = CandidateOwnerState(true, true, KeyboardLayer.LETTERS, KeyboardLanguage.ENGLISH, false)
        val commands = mutableListOf<TypingEdit>()
        val execute: (TypingEdit) -> Boolean = { commands.add(it); true }
        private val queue = ConcurrentLinkedQueue<Runnable>()
        val coordinator = LocalCandidateCoordinator(controller, lexicon,
            { routeRequests++; lastRoute = it; this.ready }, { this.ready },
            { invalidatedLoads++ }, { closedLoads++ }, Executor { queue.add(it) },
            { owner }, { published++ })

        init { controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0) }
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
                val words = when (key) { "helo" -> listOf("hello", "help"); "helos" -> listOf("hellos"); else -> emptyList() }
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
