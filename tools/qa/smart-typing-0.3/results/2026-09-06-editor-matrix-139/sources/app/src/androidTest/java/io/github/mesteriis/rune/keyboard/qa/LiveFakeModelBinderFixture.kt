package io.github.mesteriis.rune.keyboard.qa

import android.content.ComponentName
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.ServiceConnection
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Process
import android.os.RemoteException
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.intelligence.client.BoundModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessSource
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.inference.ILifecycleControl
import io.github.mesteriis.rune.keyboard.intelligence.inference.ILifecyclePublicSnapshot
import io.github.mesteriis.rune.keyboard.intelligence.inference.ILifecycleSnapshot
import io.github.mesteriis.rune.keyboard.intelligence.inference.LifecycleModelInferenceService
import io.github.mesteriis.rune.keyboard.intelligence.inference.ModelInferenceService
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedRanking
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateSearchControl
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateVisitor
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.ExactMembership
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRoute
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LexiconScanStatus
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PrefixDistance
import io.github.mesteriis.rune.keyboard.smarttyping.session.CandidateOwnerState
import io.github.mesteriis.rune.keyboard.smarttyping.session.LocalCandidateCoordinator
import io.github.mesteriis.rune.keyboard.smarttyping.session.ModelCandidateCoordinator
import io.github.mesteriis.rune.keyboard.smarttyping.session.ModelPauseScheduler
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import java.lang.reflect.Modifier
import java.util.Collections
import java.util.IdentityHashMap
import java.util.concurrent.Callable
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.FutureTask
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.junit.Assert.*

/** Test-owned composition root only. Controller, owner/render callbacks and all execution remain real. */
internal class LiveFakeModelBinderFixture private constructor(private val driver: ImeTestDriver) : AutoCloseable {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private var service: RuneInputMethodService? = null
    private var controller: TypingSessionController? = null
    private var parked: LocalCandidateCoordinator? = null
    private var parkedModel: ModelCandidateCoordinator? = null
    private var injected: LocalCandidateCoordinator? = null
    private var model: ModelCandidateCoordinator? = null
    private var client: BoundModelScoringClient? = null
    private var owner: (() -> CandidateOwnerState)? = null
    private var readiness: ReadyMetadata? = null
    private var lexicon: PublicLexicon? = null
    private val redirected = RedirectingContext(context)
    private var control: Control? = null
    private val replies = ConcurrentLinkedQueue<ReplyStamp>()
    private val availability = ConcurrentLinkedQueue<Boolean>()
    private var installed = false
    private var closed = false

    private fun install() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        val visible = keyboardSnapshot()
        onMain {
            service = resident(visible)
            controller = field(requireNotNull(service), "typingSession") as TypingSessionController
            parked = field(requireNotNull(service), "candidates") as LocalCandidateCoordinator
            parkedModel = field(requireNotNull(parked), "modelRanking") as ModelCandidateCoordinator
            @Suppress("UNCHECKED_CAST")
            val callback = field(requireNotNull(parked), "ownerState") as (() -> CandidateOwnerState)
            owner = callback
            check(!flag(requireNotNull(parked), "closed") && !flag(requireNotNull(parkedModel), "closed"))
        }
        hide()
        onMain {
            val original = requireNotNull(parked)
            original.invalidate() // Park; never close an object that will be restored.
            val controller = requireNotNull(controller)
            val owner = requireNotNull(owner)
            @Suppress("UNCHECKED_CAST")
            val render = field(original, "onCandidatesChanged") as (() -> Unit)
            val handler = Handler(Looper.getMainLooper())
            val ready = ReadyMetadata().also { readiness = it }
            val source = PublicLexicon().also { lexicon = it }
            val ranking = ModelCandidateCoordinator(controller, { delegate ->
                BoundModelScoringClient(redirected, object : ModelScoringListener {
                    override fun currentCompositionRevision() = delegate.currentCompositionRevision()
                    override fun isCurrentRequest(token: ScoringToken) = delegate.isCurrentRequest(token)
                    override fun onReply(reply: ScoringReply) {
                        delegate.onReply(reply)
                        check(replies.size < 64) { "Bounded reply observations exceeded" }
                        replies.add(ReplyStamp(Token.of(reply.token), reply.code))
                    }
                    override fun onAvailabilityChanged(available: Boolean) {
                        delegate.onAvailabilityChanged(available)
                        check(availability.size < 64) { "Bounded availability observations exceeded" }
                        availability.add(available)
                    }
                }).also { client = it }
            }, object : ModelPauseScheduler {
                override fun postDelayed(task: Runnable, millis: Long) { check(handler.postDelayed(task, millis)) }
                override fun remove(task: Runnable) { handler.removeCallbacks(task) }
            }, owner, ready, render).also { model = it }
            val local = LocalCandidateCoordinator(controller, source, source::ready, source::ready,
                {}, source::close, Executor { check(handler.post(it)) }, owner, render, ranking)
                .also { injected = it }
            advance(local, "requestId", controller, "lastCandidateRequestId")
            advance(ranking, "requestId", controller, "lastModelRequestId")
            setMutable(requireNotNull(service), "candidates", local)
            check(field(requireNotNull(service), "candidates") === local) { "Coordinator installation failed" }
            installed = true
        }
        control = Control(context)
        requireNotNull(control).command(LifecycleModelInferenceService.RELEASE)
        requireNotNull(control).awaitIdle()
        requireNotNull(control).assertPrivateRemote()
    }

    /** Fresh editor, actual keys, real local work, exact public remote request held behind its latch. */
    fun blockedWord(mode: Int): ScoringToken {
        val remote = requireNotNull(control)
        remote.command(mode)
        driver.launchComposingQa()
        assertResident()
        onMain {
            val facts = requireNotNull(owner).invoke()
            check(facts.baseEligible && facts.canRequestModelSpelling && facts.modelRuntimeQualified &&
                facts.modelAutoReplaceQualified && !facts.deterministicAutoReplaceQualified &&
                facts.autocorrectionMode == AutocorrectionMode.HIGH_CONFIDENCE &&
                !facts.contextualPunctuationEnabled && facts.language == KeyboardLanguage.ENGLISH) {
                "Actual resident production qualification does not permit this matrix"
            }
        }
        remote.command(LifecycleModelInferenceService.BLOCK_NEXT_PUBLIC)
        assertEquals(1, remote.publicSnapshot().armed)
        driver.tapKey("a")
        await("Actual scoring client did not bind") { onMain { requireNotNull(client).available } }
        space()
        for (key in listOf("h", "e", "l", "l", "l", "o")) driver.tapKey(key)
        editor("a helllo", 8, 1, 8)
        var token: ScoringToken? = null
        await("Exact public request did not enter remote engine") {
            val observed = remote.publicSnapshot()
            val pending = onMain { pendingToken() }
            if (pending != null && observed.active == 1 && observed.token == Token.of(pending)) {
                assertEquals(listOf(0, 1), pending.candidateIds)
                assertEquals(0, observed.armed)
                assertEquals(if (mode == LifecycleModelInferenceService.SCORES_PUBLIC_ORIGINAL)
                    LifecycleModelInferenceService.MODE_PUBLIC_ORIGINAL else LifecycleModelInferenceService.MODE_PUBLIC_CORRECTION,
                    observed.admittedMode)
                token = pending
                true
            } else false
        }
        onMain {
            val view = requireNotNull(injected).viewState
            assertEquals(listOf("helllo", "hello"), view.candidates.map { it.text })
            assertEquals(CandidateCompletion.COMPLETE, requireNotNull(controller).candidateCompletion)
            check(requireNotNull(readiness).active && !requireNotNull(readiness).closed)
        }
        remote.assertHealthy()
        return requireNotNull(token)
    }

    fun setMode(mode: Int) { requireNotNull(control).command(mode) }
    fun release() { requireNotNull(control).command(LifecycleModelInferenceService.RELEASE) }

    fun awaitCompletion(token: ScoringToken, mode: Int) {
        await("Exact remote completion did not arrive") {
            val snapshot = requireNotNull(control).publicSnapshot()
            snapshot.completedToken == Token.of(token) && snapshot.active == 0 && snapshot.completedMode == mode
        }
        requireNotNull(control).assertHealthy()
    }

    fun awaitRanking(token: ScoringToken, preferred: Int) {
        await("Actual coordinator did not accept matching numeric ranking") {
            val reply = replies.firstOrNull { it.token == Token.of(token) }
            if (reply != null) assertEquals("Public request was not OK", ScoringCode.OK, reply.code)
            reply != null && onMain {
                val selection = field(requireNotNull(controller), "candidateSelection") ?: return@onMain false
                val ranking = field(selection, "ranking") as? CalibratedRanking ?: return@onMain false
                flag(selection, "modelRanked") && ranking.usedModel && ranking.preferredId == preferred
            }
        }
        candidate(preferred == 0).let { assertTrue("Model-ranked candidate is not selected", it.isSelected) }
    }

    fun originalTap(token: ScoringToken) {
        val originalId = onMain { requireNotNull(controller).originalCandidateId }
        checkNotNull(originalId) { "Original candidate is absent" }
        candidate(true).click() // Real resident candidate callback; never call the controller from the test.
        await("Original tap did not veto the captured request") { onMain {
            requireNotNull(controller).state.originalSelected &&
                !requireNotNull(controller).isCurrentModelRanking(token) &&
                requireNotNull(controller).originalCandidateId != originalId
        } }
        assertTrue(candidate(true).isSelected)
    }

    fun assertStale(token: ScoringToken) {
        onMain {
            check(requireNotNull(controller).state.originalSelected)
            check(!requireNotNull(controller).isCurrentModelRanking(token))
            check(pendingToken() == null)
        }
        assertFalse("Stale reply reached accepted coordinator callback", replies.any { it.token == Token.of(token) })
        assertTrue(candidate(true).isSelected)
    }

    fun killAndAwaitClientLoss(token: ScoringToken) {
        availability.clear()
        requireNotNull(control).kill()
        await("Actual bound client did not invalidate after Binder death") { onMain {
            availability.contains(false) && !requireNotNull(client).available &&
                field(requireNotNull(client), "latest") == null && pendingToken() == null &&
                !requireNotNull(controller).isCurrentModelRanking(token)
        } }
        assertFalse(replies.any { it.token == Token.of(token) })
    }

    fun awaitReconnectWithoutReplay() {
        requireNotNull(control).reconnect()
        await("Production bounded retry did not reconnect") { onMain { requireNotNull(client).available } }
        val remote = requireNotNull(control).publicSnapshot()
        assertEquals(0, remote.starts)
        assertEquals(0, remote.active)
        requireNotNull(control).assertNoStarts()
        onMain {
            check(field(requireNotNull(client), "latest") == null && pendingToken() == null &&
                field(requireNotNull(model), "timer") == null && field(requireNotNull(model), "pendingKind") == null) {
                "Reconnect retained an earlier request or timer"
            }
        }
    }

    fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    fun backspace() = driver.tapDelete()
    fun typeZ() = driver.tapKey("z")
    fun assertOriginalSelected() = assertTrue(candidate(true).isSelected)

    fun editor(text: String, caret: Int, start: Int, end: Int): EditorSnapshot {
        var result: EditorSnapshot? = null
        await("Public editor text/selection/span did not settle") {
            val current = snapshot()
            val acknowledged = onMain { !flag(requireNotNull(controller), "awaitingEditorSelection") }
            val matches = current.text == text && current.stats["selectionStart"] == caret &&
                current.stats["selectionEnd"] == caret && current.stats["start"] == start && current.stats["end"] == end
            if (matches && acknowledged && current == result) true else { result = current; false }
        }
        return requireNotNull(result).also(::noPayloadReads)
    }

    fun assertUnchanged(before: EditorSnapshot) {
        instrumentation.waitForIdleSync()
        driver.device.waitForIdle()
        val after = snapshot()
        assertEquals("Score/lifecycle event changed public editor or counters", before, after)
        noPayloadReads(after)
        assertResident()
    }

    fun assertCommandDelta(before: EditorSnapshot, after: EditorSnapshot, expected: Map<String, Int>) {
        for (key in listOf("connections", "compose", "region", "finish", "commit", "keyDown", "keyUp", "deleteKeyDown")) {
            assertEquals("Unexpected editor command delta: $key", expected[key] ?: 0,
                after.stats.getValue(key) - before.stats.getValue(key))
        }
        noPayloadReads(after)
    }

    private fun noPayloadReads(snapshot: EditorSnapshot) {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor payload read", 0, snapshot.stats.getValue(key))
        }
    }

    private fun snapshot(): EditorSnapshot {
        val text = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_text")))
            .text.orEmpty()
        val stats = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats")))
            .text.orEmpty().split(' ').associate { value ->
                val (key, number) = value.split('='); key to number.toInt()
            }
        return EditorSnapshot(text, stats)
    }

    private fun candidate(original: Boolean) = checkNotNull(driver.device.wait(Until.findObject(By.desc(
        context.getString(if (original) R.string.candidate_original else R.string.candidate_correction,
            if (original) "helllo" else "hello"))), ImeTestDriver.WAIT_MILLIS)) { "Public candidate unavailable" }

    private fun assertResident() {
        val keyboard = keyboardSnapshot()
        onMain {
            check(resident(keyboard) === service && field(requireNotNull(service), "typingSession") === controller &&
                field(requireNotNull(service), "candidates") === injected && !flag(requireNotNull(injected), "closed")) {
                "Resident IME or injected composition root changed"
            }
        }
    }

    private fun pendingToken(): ScoringToken? {
        val pending = field(requireNotNull(controller), "pendingModelRanking") ?: return null
        return field(pending, "token") as ScoringToken
    }

    private fun hide() {
        driver.device.pressHome()
        check(driver.device.wait(Until.gone(By.desc(context.getString(R.string.key_delete))), ImeTestDriver.WAIT_MILLIS))
        await("Resident input view did not finish") { onMain { requireNotNull(owner).invoke().inputViewActive.not() } }
    }

    override fun close() {
        if (closed) return
        closed = true
        var failure: Throwable? = null
        fun attempt(action: () -> Unit) {
            try { action() } catch (next: Throwable) {
                if (failure == null) failure = next else failure!!.addSuppressed(next)
            }
        }
        try {
            if (service != null && owner != null) attempt { hide() }
            attempt { control?.releaseIfAlive() }
            attempt { onMain {
                val original = parked
                val replacement = injected
                val live = service?.let { field(it, "keyboardView") != null } == true
                val owns = service?.let { field(it, "candidates") === replacement } == true
                val restorable = installed && live && owns && replacement != null && !flag(replacement, "closed")
                replacement?.invalidate(); replacement?.close()
                if (replacement == null) { model?.close(); lexicon?.close() }
                if (restorable) {
                    check(original != null && !flag(original, "closed") && !flag(requireNotNull(parkedModel), "closed"))
                    advance(original, "requestId", requireNotNull(controller), "lastCandidateRequestId")
                    advance(requireNotNull(parkedModel), "requestId", requireNotNull(controller), "lastModelRequestId")
                    setMutable(requireNotNull(service), "candidates", original)
                    check(field(requireNotNull(service), "candidates") === original)
                } else if (installed) {
                    original?.close()
                    error("Captured IME was destroyed/replaced; parked resources closed without restoration")
                }
                check(readiness?.closed != false && lexicon?.closed?.get() != false)
            } }
            // Model creation may have failed before its local coordinator was installed.
            if (!installed) attempt { onMain { model?.close(); lexicon?.close() } }
            attempt { control?.close() }
            attempt { onMain { redirected.assertBalanced() } }
        } finally {
            service = null; controller = null; parked = null; parkedModel = null; injected = null
            model = null; client = null; owner = null; readiness = null; lexicon = null; control = null
            replies.clear(); availability.clear()
        }
        failure?.let { throw it }
    }

    internal data class EditorSnapshot(val text: String, val stats: Map<String, Int>)
    private data class Token(val session: Long, val revision: Long, val request: Long) {
        companion object { fun of(token: ScoringToken) = Token(token.sessionId, token.revision, token.requestId) }
    }
    private data class ReplyStamp(val token: Token, val code: Int)
    private data class PublicSnapshot(val armed: Int, val starts: Int, val active: Int, val token: Token,
        val admittedMode: Int, val completedToken: Token, val completedMode: Int)

    private class ReadyMetadata : ModelReadinessSource {
        var active = false; private set
        var closed = false; private set
        override val hint get() = if (closed) ModelReadinessHint.MISSING else ModelReadinessHint.READY
        override fun setActive(active: Boolean) { check(!closed); this.active = active }
        override fun close() { active = false; closed = true }
    }

    /** Exhaustive fixed public table, not packaged-lexicon coverage. Scratch is cleared on every exit. */
    private class PublicLexicon : CandidateLexicon, AutoCloseable {
        val closed = AtomicBoolean(false)
        fun ready(route: LanguageRoute) = !closed.get() && route.primary != null && route.protectedReason == null
        private fun entries(language: KeyboardLanguage) = if (language == KeyboardLanguage.ENGLISH)
            listOf("a" to 1, "hello" to 2) else emptyList()
        override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
            for ((word, _) in entries(language)) {
                if (closed.get() || !control.inspectState()) return ExactMembership.UNAVAILABLE
                if (word == key) return if (control.checkpoint()) ExactMembership.PRESENT else ExactMembership.UNAVAILABLE
            }
            return if (!closed.get() && control.checkpoint()) ExactMembership.ABSENT else ExactMembership.UNAVAILABLE
        }
        override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
            control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
            val distance = PrefixDistance()
            try {
                distance.begin(key)
                for ((word, rank) in entries(language)) {
                    if (closed.get() || !control.inspectState()) return LexiconScanStatus.UNAVAILABLE
                    distance.resetPath()
                    for (cp in word.codePoints().toArray()) {
                        if (!distance.append(cp, language, control)) return LexiconScanStatus.UNAVAILABLE
                    }
                    if (word != key && distance.terminalUnit <= unitRadius && !visitor.visit(word, rank)) {
                        return LexiconScanStatus.UNAVAILABLE
                    }
                }
                return if (!closed.get() && control.checkpoint()) LexiconScanStatus.COMPLETE else LexiconScanStatus.UNAVAILABLE
            } finally { distance.clear() }
        }
        override fun close() { closed.set(true) }
    }

    private class RedirectingContext(base: Context) : ContextWrapper(base) {
        private val registrations = Collections.newSetFromMap(IdentityHashMap<ServiceConnection, Boolean>())
        private var attempts = 0
        private var unbinds = 0
        override fun getApplicationContext(): Context = this
        override fun bindService(intent: Intent, connection: ServiceConnection, flags: Int): Boolean {
            check(intent.component?.className == ModelInferenceService::class.java.name)
            attempts++; check(registrations.add(connection))
            return baseContext.bindService(Intent(intent).setComponent(
                ComponentName(baseContext, LifecycleModelInferenceService::class.java)), connection, flags)
        }
        override fun unbindService(connection: ServiceConnection) {
            check(registrations.remove(connection)); unbinds++
            baseContext.unbindService(connection)
        }
        fun assertBalanced() { check(registrations.isEmpty() && attempts == unbinds) { "Unbalanced scoring bindings" } }
    }

    private class Control(private val context: Context) : AutoCloseable {
        private val component = ComponentName(context, LifecycleModelInferenceService::class.java)
        private var binding = Binding(context, Intent().setComponent(component).setAction(LifecycleModelInferenceService.CONTROL_ACTION))
        private var killed = false
        private data class Health(val pid: Int, val uid: Int, val starts: Int, val active: Int,
            val peak: Int, val order: Int, val timeouts: Int)
        private fun health(operation: Int): Health {
            val queue = LinkedBlockingQueue<Health>(1)
            ILifecycleControl.Stub.asInterface(binding.binder()).command(operation, object : ILifecycleSnapshot.Stub() {
                override fun onSnapshot(processId: Int, uid: Int, starts: Int, previousId: Long, lastId: Long,
                    active: Int, peakActive: Int, cancels: Int, cancelledCompletions: Int, completions: Int,
                    unloads: Int, unloadedCompletions: Int, orderViolations: Int, timeouts: Int) {
                    queue.offer(Health(processId, uid, starts, active, peakActive, orderViolations, timeouts))
                }
            })
            return checkNotNull(queue.poll(3, TimeUnit.SECONDS)) { "Debug numeric control timeout" }
                .also { check(it.order == 0 && it.timeouts == 0 && it.peak <= 1) { "Remote worker contract failed" } }
        }
        fun command(operation: Int) { health(operation) }
        fun assertHealthy() { health(LifecycleModelInferenceService.SNAPSHOT) }
        fun assertNoStarts() { assertEquals(0, health(LifecycleModelInferenceService.SNAPSHOT).starts) }
        fun awaitIdle() { await("Remote worker did not become idle") { health(LifecycleModelInferenceService.SNAPSHOT).active == 0 } }
        fun assertPrivateRemote() {
            @Suppress("DEPRECATION")
            val info = context.packageManager.getServiceInfo(component, 0)
            check(!info.exported && info.permission == null && info.processName == context.packageName + ":model_runtime")
            val current = health(LifecycleModelInferenceService.SNAPSHOT)
            assertEquals(Process.myUid(), current.uid); assertNotEquals(Process.myPid(), current.pid)
            assertNull(binding.binder().queryLocalInterface("io.github.mesteriis.rune.keyboard.intelligence.inference.ILifecycleControl"))
        }
        fun publicSnapshot(): PublicSnapshot {
            val queue = LinkedBlockingQueue<PublicSnapshot>(1)
            ILifecycleControl.Stub.asInterface(binding.binder()).observePublic(object : ILifecyclePublicSnapshot.Stub() {
                override fun onSnapshot(mode: Int, armed: Int, starts: Int, completions: Int, active: Int,
                    sessionId: Long, revision: Long, requestId: Long, admittedMode: Int,
                    completedSessionId: Long, completedRevision: Long, completedRequestId: Long,
                    completedMode: Int, invalidRequests: Int) {
                    queue.offer(PublicSnapshot(armed, starts, active, Token(sessionId, revision, requestId), admittedMode,
                        Token(completedSessionId, completedRevision, completedRequestId), completedMode))
                }
            })
            return checkNotNull(queue.poll(3, TimeUnit.SECONDS)) { "Debug public token observation timeout" }
        }
        fun kill() {
            val binder = binding.binder()
            val death = CountDownLatch(1)
            val recipient = IBinder.DeathRecipient { death.countDown() }
            binder.linkToDeath(recipient, 0)
            try {
                killed = true
                try { ILifecycleControl.Stub.asInterface(binder).command(LifecycleModelInferenceService.KILL_PROCESS, null) }
                catch (_: RemoteException) { /* The death recipient remains the required barrier. */ }
                check(death.await(3, TimeUnit.SECONDS)) { "Remote process did not die" }
            } finally { binder.unlinkToDeath(recipient, 0) }
        }
        fun reconnect() {
            binding.close()
            binding = Binding(context, Intent().setComponent(component).setAction(LifecycleModelInferenceService.CONTROL_ACTION))
            binding.binder(); killed = false
            assertPrivateRemote()
        }
        fun releaseIfAlive() {
            if (!killed && binding.binder().isBinderAlive) command(LifecycleModelInferenceService.RELEASE)
        }
        override fun close() {
            try {
                if (!killed && binding.binder().isBinderAlive) {
                    command(LifecycleModelInferenceService.RELEASE)
                    command(LifecycleModelInferenceService.SCORES_EQUAL)
                    command(LifecycleModelInferenceService.INVALIDATE)
                    awaitIdle()
                }
            } finally { binding.close() }
        }
    }

    private class Binding(private val context: Context, intent: Intent) : AutoCloseable {
        private val ready = LinkedBlockingQueue<IBinder>(1)
        private var endpoint: IBinder? = null
        private var closed = false
        private val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, service: IBinder) { ready.offer(service) }
            override fun onServiceDisconnected(name: ComponentName) = Unit
        }
        init {
            try { check(onMain { context.bindService(intent, connection, Context.BIND_AUTO_CREATE) }) }
            catch (failure: Throwable) {
                try { close() } catch (cleanup: Throwable) { failure.addSuppressed(cleanup) }
                throw failure
            }
        }
        fun binder() = endpoint ?: checkNotNull(ready.poll(4, TimeUnit.SECONDS)) { "Control binding timeout" }.also { endpoint = it }
        override fun close() { if (!closed) { closed = true; onMain { context.unbindService(connection) } } }
    }

    companion object {
        fun install(driver: ImeTestDriver): LiveFakeModelBinderFixture {
            val fixture = LiveFakeModelBinderFixture(driver)
            try { fixture.install(); return fixture }
            catch (failure: Throwable) {
                try { fixture.close() } catch (cleanup: Throwable) { failure.addSuppressed(cleanup) }
                throw failure
            }
        }
        private fun resident(snapshot: KeyboardSnapshot): RuneInputMethodService {
            var context: Context = snapshot.keyboard.context
            while (context !is RuneInputMethodService && context is ContextWrapper) context = context.baseContext
            return checkNotNull(context as? RuneInputMethodService) { "Resident IME context unavailable" }
        }
        private fun field(owner: Any, name: String): Any? = owner.javaClass.getDeclaredField(name)
            .apply { isAccessible = true }.get(owner)
        private fun flag(owner: Any, name: String) = field(owner, name) as Boolean
        private fun setMutable(owner: Any, name: String, value: Any) {
            val field = owner.javaClass.getDeclaredField(name).apply { isAccessible = true }
            check(!Modifier.isFinal(field.modifiers)) { "Reflection contract requires mutable field" }
            field.set(owner, value)
        }
        private fun advance(owner: Any, name: String, controller: Any, highWaterName: String) {
            val current = field(owner, name) as Long
            val highWater = field(controller, highWaterName) as Long
            check(current in 0 until Long.MAX_VALUE && highWater in -1 until Long.MAX_VALUE) { "Request counter bounds changed" }
            val next = maxOf(current, highWater, 0L)
            setMutable(owner, name, next)
            check(field(owner, name) == next) { "Request high-water seeding failed" }
        }
        private fun <T> onMain(action: () -> T): T {
            val task = FutureTask(Callable(action))
            InstrumentationRegistry.getInstrumentation().runOnMainSync(task)
            return task.get(5, TimeUnit.SECONDS)
        }
        private fun await(message: String, condition: () -> Boolean) {
            val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
            do {
                if (condition()) return
                SystemClock.sleep(25) // Bounded condition polling, not a device-specific inference delay.
            } while (SystemClock.uptimeMillis() < deadline)
            throw AssertionError(message)
        }
    }
}
