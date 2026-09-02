package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import java.util.concurrent.atomic.AtomicBoolean

interface ScoringEngine : AutoCloseable {
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
    private val monitor = Object()
    private val lifecycle = duty.registerLifecycle()
    private var lease = duty.acquireLease()
    private var pending: Work? = null
    private var active: Work? = null
    private var operation: Operation? = null
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
            if (stopped || !bound || !admitted().admitted) {
                reject(work); monitor.notifyAll(); return
            }
            pending = work
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
        if (!stopped && duty.onBind(lifecycle)) bound = true
    }
    fun onUnbind() = synchronized(monitor) {
        duty.onUnbind(lifecycle); bound = false; invalidateLocked()
    }
    override fun close() = synchronized(monitor) {
        if (!stopped) { stopped = true; bound = false; invalidateLocked(); monitor.notifyAll() }
        // No main/Binder wait for scoring, watchdog or native teardown.
    }
    private fun invalidateLocked() {
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
    private fun reject(work: Work) {
        try { work.reply(ScoringReply(work.input.token, ScoringCode.UNAVAILABLE, 0, emptyList())) }
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
        val work = synchronized(monitor) {
            while (!stopped && pending == null && !unloadRequested) {
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
            if (unload) null else pending?.also { pending = null; active = it }
        }
        if (unload) cleanup(close = false) else if (work != null) perform(work)
        return true
    }
    /** Separate request frame: neither the idle wait nor cleanup retains completed input. */
    private fun perform(work: Work) {
        synchronized(monitor) {
            if (work.cancelled.get()) { active = null; work.finish(); return }
            val admission = admitted()
            if (stopped || !bound || !admission.admitted ||
                admission.state.elapsedMillis - work.receivedAt >= ModelDutyProfile.QUEUE_MILLIS) {
                active = null; reject(work); return
            }
            active = work; unloaded = false
            startOperation(Operation(admission.state.generation, admission.state.elapsedMillis, work.cancelled))
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
