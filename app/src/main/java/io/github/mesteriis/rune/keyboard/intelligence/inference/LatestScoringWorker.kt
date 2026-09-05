package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import java.util.concurrent.atomic.AtomicBoolean

sealed interface ModelPreparation {
    data object NotSupported : ModelPreparation
    data object Ready : ModelPreparation
    data class Failure(val code: Int) : ModelPreparation { init { require(code in 1..15) } }
}

interface ScoringEngine : AutoCloseable {
    /** No input payload. Unsupported engines retain the ordinary score contract. */
    fun prepare(cancelled: AtomicBoolean): ModelPreparation = ModelPreparation.NotSupported
    fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply
    /** Must be nonblocking and safe from the Binder/control threads. */
    fun cancel()
    fun unload()
}

/** One active + one replacing pending. No request runnable is placed into an executor queue. */
class LatestScoringWorker internal constructor(
    private val engine: ScoringEngine,
    private val idleMillis: Long,
    private val duty: ModelDutyOwner,
    private val checks: ModelDutyScheduler,
) : AutoCloseable {
    constructor(engine: ScoringEngine, idleMillis: Long = 60_000) :
        this(engine, idleMillis, ProcessModelDuty.owner, ScheduledModelDutyChecks())

    private class Work(val input: ScoringInput, val deliver: (ScoringReply) -> Unit,
        val finished: () -> Unit, val receivedAt: Long, val cancelled: AtomicBoolean = AtomicBoolean()) {
        private val finishedOnce = AtomicBoolean()
        fun finish() {
            if (finishedOnce.compareAndSet(false, true)) try { finished() } catch (_: Exception) { }
        }
        fun reply(value: ScoringReply) { try { deliver(value) } catch (_: Exception) { } }
    }
    /** Timers carry only operation identity/numbers/flag, never a Work or editor payload. */
    private class Operation(val generation: Long, val startedAt: Long, val cancelled: AtomicBoolean?)
    /** Preparation and its first score share one admission and the same wall deadline. */
    private class PreparationWindow(val generation: Long, val startedAt: Long)
    private val monitor = Object()
    private val lifecycle = duty.registerLifecycle()
    private var lease = duty.acquireLease()
    private var pending: Work? = null
    private var active: Work? = null
    private var operation: Operation? = null
    private var prepareRequested = false
    private var preparationSupported = true
    private var preparing: AtomicBoolean? = null
    private var preparationWindow: PreparationWindow? = null
    private var stopped = false
    private var bound = true
    private var unloadRequested = false
    private var unloaded = true
    private var idleAt = 0L
    private val worker = Thread(::run, "rune-scoring").apply { start() }

    fun submit(input: ScoringInput, deliver: (ScoringReply) -> Unit, finished: () -> Unit = {}) {
        val receivedAt = duty.account().elapsedMillis
        synchronized(monitor) {
            // Numeric request identity cannot renew its queue age, even with changed revision/candidates.
            val earlier = pending?.takeIf { it.input.token.sessionId == input.token.sessionId &&
                it.input.token.requestId == input.token.requestId }?.receivedAt
            val receipt = if (earlier == null) receivedAt else minOf(earlier, receivedAt)
            val work = Work(input, deliver, finished, receipt)
            val previous = pending; pending = null
            previous?.let { it.cancelled.set(true); it.finish() }
            cancelActive()
            if (stopped || !bound || !workAdmission().admitted) {
                reject(work); monitor.notifyAll(); return
            }
            pending = work
            requestPreparationLocked()
            monitor.notifyAll()
        }
    }
    fun cancel(sessionId: Long, requestId: Long) = synchronized(monitor) {
        fun Work.matches() = input.token.sessionId == sessionId && input.token.requestId == requestId
        pending?.takeIf { it.matches() }?.let { pending = null; it.cancelled.set(true); it.finish() }
        active?.takeIf { it.matches() }?.let { cancelActive() }
    }
    fun invalidate() = synchronized(monitor) { invalidateLocked() }
    fun suspendForMemoryPressure() {
        duty.suspendForPressure() // first: concurrent admissions fail before the worker lock is taken
        synchronized(monitor) { invalidateLocked() }
    }
    fun onBind() = synchronized(monitor) {
        if (!stopped && duty.onBind(lifecycle)) { bound = true; requestPreparationLocked() }
    }
    fun onUnbind() = synchronized(monitor) {
        duty.onUnbind(lifecycle); bound = false; invalidateLocked()
    }
    override fun close() = synchronized(monitor) {
        if (!stopped) { stopped = true; bound = false; invalidateLocked(); monitor.notifyAll() }
        // No main/Binder wait for scoring, watchdog or native teardown.
    }
    private fun invalidateLocked() {
        prepareRequested = false
        preparationWindow = null
        preparing?.let { flag ->
            flag.set(true)
            if (operation?.cancelled === flag) try { engine.cancel() } catch (_: Exception) { }
        }
        val previous = pending; pending = null
        previous?.let { it.cancelled.set(true); it.finish() }
        cancelActive(); unloadRequested = true; monitor.notifyAll()
    }
    private fun cancelActive() {
        active?.let {
            // Preserve the existing signal on every replacement/cancel; always set the flag first.
            it.cancelled.set(true)
            if (operation?.cancelled === it.cancelled) try { engine.cancel() } catch (_: Exception) { }
        }
    }
    private fun admitted(): ModelDutyAdmission {
        if (lease == 0L) lease = duty.acquireLease()
        return duty.admit(lease)
    }
    private fun workAdmission(): ModelDutyAdmission {
        val window = preparationWindow
        if (window != null && duty.owns(lease)) {
            val state = duty.account()
            if (!state.faulted && !state.suspended && state.generation == window.generation &&
                state.creditUnits > 0 && state.elapsedMillis - window.startedAt in 0 until ModelDutyProfile.ACTIVE_MILLIS) {
                return ModelDutyAdmission(true, state)
            }
        }
        return admitted()
    }
    private fun requestPreparationLocked() {
        if (preparationSupported && !stopped && bound && (unloaded || unloadRequested) && preparing == null &&
            !prepareRequested && admitted().admitted) {
            prepareRequested = true
            monitor.notifyAll()
        }
    }
    private fun reject(work: Work, code: Int = ScoringCode.UNAVAILABLE) {
        try { work.reply(ScoringReply(work.input.token, code, 0, emptyList())) }
        finally { work.finish() }
    }
    private fun run() {
        try {
            while (runNext()) { /* Each completed request frame is discarded before the next wait. */ }
        } finally {
            try {
                synchronized(monitor) {
                    stopped = true; bound = false
                    val abandoned = pending; pending = null
                    abandoned?.let { it.cancelled.set(true); it.finish() }
                }
                cleanup(close = true)
            } finally {
                // Release through exceptional cleanup, after final CPU accounting, exactly once.
                duty.release(lease); lease = 0
                checks.close()
            }
        }
    }
    private fun runNext(): Boolean {
        var unload = false
        var prepare = false
        val work = synchronized(monitor) {
            while (!stopped && pending == null && !unloadRequested && !prepareRequested) {
                if (unloaded) monitor.wait()
                else {
                    val state = duty.account()
                    val age = state.elapsedMillis - idleAt
                    if (state.faulted || age >= idleMillis) { unloadRequested = true; break }
                    monitor.wait(maxOf(1, idleMillis - age))
                }
            }
            if (stopped) return false
            if (unloadRequested) { unloadRequested = false; unload = true }
            if (!unload && pending != null && unloaded) requestPreparationLocked()
            if (!unload && prepareRequested) { prepareRequested = false; prepare = true }
            if (unload || prepare) null else pending?.also { pending = null; active = it }
        }
        if (unload) cleanup(close = false) else if (prepare) prepare() else if (work != null) perform(work)
        return true
    }
    /** No Work is captured here: cancellation/replacement can release pending input during load. */
    private fun prepare() {
        val flag = AtomicBoolean()
        synchronized(monitor) {
            val admission = admitted()
            if (stopped || !bound || unloadRequested || !admission.admitted) return
            preparing = flag; unloaded = false
            preparationWindow = PreparationWindow(admission.state.generation, admission.state.elapsedMillis)
            startOperation(Operation(admission.state.generation, admission.state.elapsedMillis, flag))
        }
        var result: ModelPreparation = ModelPreparation.Failure(ScoringCode.INTERNAL)
        try {
            result = engine.prepare(flag)
        } catch (_: Exception) {
            // Deliver the stable numeric failure below; never expose exception payloads.
        } finally {
            synchronized(monitor) {
                checkOperation(operation)
                if (result != ModelPreparation.Ready || flag.get()) preparationWindow = null
                if (result == ModelPreparation.NotSupported) {
                    preparationSupported = false
                    unloaded = true // No runtime was created by an unsupported preparation.
                }
                if (result is ModelPreparation.Failure || flag.get()) {
                    // Never retry a failed load for the same queued word. Another actual
                    // request/bind is required; cancellation/cleanup still receive full accounting.
                    val failed = pending; pending = null
                    val code = if (flag.get()) ScoringCode.CANCELLED else (result as ModelPreparation.Failure).code
                    failed?.let { reject(it, code) }
                    unloadRequested = true
                }
                retireOperation(); preparing = null
                idleAt = duty.account().elapsedMillis
            }
        }
    }
    /** Separate request frame: neither the idle wait nor cleanup retains completed input. */
    private fun perform(work: Work) {
        synchronized(monitor) {
            if (work.cancelled.get()) { active = null; work.finish(); return }
            val admission = workAdmission()
            if (stopped || !bound || !admission.admitted ||
                admission.state.elapsedMillis - work.receivedAt >= ModelDutyProfile.QUEUE_MILLIS) {
                active = null; reject(work); return
            }
            active = work; unloaded = false
            val window = preparationWindow?.takeIf { admission.state.generation == it.generation &&
                admission.state.elapsedMillis - it.startedAt in 0 until ModelDutyProfile.ACTIVE_MILLIS }
            preparationWindow = null // exactly one score may consume the preparation admission
            startOperation(Operation(admission.state.generation, window?.startedAt ?: admission.state.elapsedMillis, work.cancelled))
        }
        try {
            val reply = try { engine.score(work.input, work.cancelled) }
            catch (_: Exception) { ScoringReply(work.input.token, ScoringCode.INTERNAL, 0, emptyList()) }
            synchronized(monitor) {
                checkOperation(operation)
                if (!stopped && !work.cancelled.get()) work.reply(reply)
            }
        } finally {
            synchronized(monitor) {
                retireOperation()
                active = null
                try { work.finish() } finally { idleAt = duty.account().elapsedMillis }
            }
        }
    }
    private fun cleanup(close: Boolean) {
        // An engine with no granted lease has never entered score/unload/close and owns no runtime.
        if (lease == 0L) return
        synchronized(monitor) {
            preparationWindow = null
            val state = duty.account()
            startOperation(Operation(state.generation, state.elapsedMillis, null))
        }
        try {
            if (close) engine.close() else engine.unload()
        } catch (_: Exception) {
            // Mandatory cleanup was attempted; no exception text or callback payload is logged.
        } finally {
            synchronized(monitor) { retireOperation(); duty.account(); unloaded = true }
        }
    }
    private fun startOperation(current: Operation) {
        check(operation == null)
        operation = current
        checks.start(Runnable { synchronized(monitor) { checkOperation(current) } })
    }
    private fun checkOperation(current: Operation?) {
        if (current == null || operation !== current || !duty.owns(lease)) return
        val state = duty.account()
        val flag = current.cancelled ?: return // cleanup samples but is never cancelled
        if (!flag.get() && (state.faulted || state.suspended || state.generation != current.generation ||
                state.creditUnits <= 0 || state.elapsedMillis - current.startedAt >= ModelDutyProfile.ACTIVE_MILLIS)) {
            flag.set(true)
            try { engine.cancel() } catch (_: Exception) { }
        }
    }
    private fun retireOperation() { operation = null; checks.stop() }
}
