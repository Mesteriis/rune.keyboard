package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import java.util.concurrent.Executor
import java.util.concurrent.ThreadFactory
import java.util.concurrent.atomic.AtomicBoolean

/** Caller-owned bounded token only; eligibility must come from the live owner, never inferred here. */
data class LocalCandidateRequest(
    val sessionId: Long,
    val revision: Long,
    val requestId: Long,
    val token: String,
    val activeLanguage: KeyboardLanguage,
    val eligible: Boolean,
) {
    override fun toString(): String =
        "LocalCandidateRequest(sessionId=$sessionId, revision=$revision, requestId=$requestId, redacted)"
}

/** Owner must still check its live session, revision, owned composition and eligibility before use. */
data class LocalCandidateReply(
    val sessionId: Long,
    val revision: Long,
    val requestId: Long,
    val generation: CandidateGeneration,
) {
    override fun toString(): String =
        "LocalCandidateReply(sessionId=$sessionId, revision=$revision, requestId=$requestId, redacted)"
}

enum class LocalCandidateWorkerFailure { OWNER_DISPATCH, OWNER_CALLBACK, WORKER_STOPPED }

/**
 * One dedicated serial compute thread; at most one active and one replacing pending request.
 * Construct, submit, cancel, close and owner delivery all belong to the constructing thread.
 * Dispatcher must promptly post each accepted Runnable exactly once to that same owner thread.
 *
 * Transfer exclusive use of an already validated generator here. Index loading/ownership and
 * eventual index close are separate; this worker neither opens assets nor calls a model/editor.
 * Cancellation flags change directly, never behind computation. Reader checkpoints determine
 * how soon an active stack returns; close does not join or forcibly kill an uncooperative reader.
 */
class LocalCandidateWorker internal constructor(
    private val generator: CandidateGenerator,
    private val ownerDispatcher: Executor,
    listener: (LocalCandidateReply) -> Unit,
    threadFactory: ThreadFactory,
) : AutoCloseable {
    constructor(
        generator: CandidateGenerator,
        ownerDispatcher: Executor,
        listener: (LocalCandidateReply) -> Unit,
    ) : this(generator, ownerDispatcher, listener, ThreadFactory { action ->
        Thread(action, "rune-local-candidates").apply { isDaemon = true }
    })

    private class Work(request: LocalCandidateRequest) {
        val sessionId = request.sessionId
        val revision = request.revision
        val requestId = request.requestId
        val cancelled = AtomicBoolean(false)
        var payload: LocalCandidateRequest? = request
    }

    private class Delivery(val work: Work, val reply: LocalCandidateReply)

    private val ownerThread = Thread.currentThread()
    private val lock = Object()
    private var listener: ((LocalCandidateReply) -> Unit)? = listener
    private var active: Work? = null
    private var pending: Work? = null
    private var latest: Work? = null
    private var delivery: Delivery? = null
    private var deliveryScheduled = false
    @Volatile private var closed = false
    @Volatile var lastFailure: LocalCandidateWorkerFailure? = null
        private set

    /** A queued owner action holds only this worker, never a request, result or callback snapshot. */
    private val deliverAction = Runnable { deliver() }

    init {
        val thread = threadFactory.newThread(Runnable { workLoop() })
        check(thread.state == Thread.State.NEW) { "Candidate worker requires a new thread" }
        thread.start()
    }

    /**
     * Every call invalidates older work, including a rejected/ineligible replacement.
     * Invalid/protected/overlength tokens are rejected without retention or truncation.
     * Numeric IDs are caller identities; internal object identity prevents reuse from reviving work.
     */
    fun submit(request: LocalCandidateRequest): Boolean {
        checkOwner()
        synchronized(lock) {
            invalidateLocked()
            if (closed || !request.eligible || request.sessionId < 0 || request.revision < 0 ||
                request.requestId < 0 || ProtectedTokenPolicy.isProtected(request.token)) return false
            val work = Work(request)
            latest = work
            pending = work
            lock.notifyAll()
            return true
        }
    }

    fun cancel() {
        checkOwner()
        synchronized(lock) { invalidateLocked() }
    }

    override fun close() {
        checkOwner()
        synchronized(lock) {
            closed = true
            invalidateLocked()
            listener = null
            lock.notifyAll()
        }
    }

    private fun checkOwner() {
        check(Thread.currentThread() === ownerThread) { "Candidate worker owner thread required" }
    }

    /** Lock contains only bounded state/admission work, never generator, dispatcher or user code. */
    private fun invalidateLocked() {
        active?.cancelled?.set(true)
        active?.payload = null
        pending?.cancelled?.set(true)
        pending?.payload = null
        pending = null
        latest = null
        delivery = null
        // Keep one already-posted empty action; it may deliver a newer completed result later.
    }

    private fun workLoop() {
        try {
            // A separate invocation owns each payload. No last request lives across idle wait.
            while (runNext()) Unit
        } catch (_: Throwable) {
            // Fatal/unexpected worker failures stop this worker and never reach the default
            // uncaught handler with a reader's potentially text-bearing exception message.
            synchronized(lock) {
                lastFailure = LocalCandidateWorkerFailure.WORKER_STOPPED
                closed = true
                invalidateLocked()
                listener = null
            }
        }
    }

    private fun runNext(): Boolean {
        val work = synchronized(lock) {
            while (!closed && pending == null) lock.wait()
            if (closed) return false
            pending!!.also {
                pending = null
                active = it
            }
        }
        compute(work)
        return true
    }

    private fun compute(work: Work) {
        val request = synchronized(lock) {
            work.payload.also { work.payload = null }
        }
        val result = request?.let {
            generator.generate(it.token, it.activeLanguage, CandidateCancellation { work.cancelled.get() })
        }
        val post = synchronized(lock) {
            active = null
            if (!closed && latest === work && !work.cancelled.get() && result != null &&
                result.completion != CandidateCompletion.CANCELLED) {
                delivery = Delivery(work, LocalCandidateReply(work.sessionId, work.revision, work.requestId, result))
                if (!deliveryScheduled) {
                    deliveryScheduled = true
                    true
                } else false
            } else false
        }
        if (post) {
            try {
                ownerDispatcher.execute(deliverAction)
            } catch (_: Exception) {
                synchronized(lock) {
                    lastFailure = LocalCandidateWorkerFailure.OWNER_DISPATCH
                    delivery = null
                    deliveryScheduled = false
                }
            }
        }
    }

    private fun deliver() {
        checkOwner()
        val ready = synchronized(lock) {
            deliveryScheduled = false
            val current = delivery
            delivery = null
            if (closed || current == null || latest !== current.work || current.work.cancelled.get()) null
            else {
                latest = null
                current.reply
            }
        } ?: return
        // Owner confinement makes the final guard and callback indivisible with respect to
        // submit/cancel/close. User code runs without the worker lock and may submit reentrantly.
        try {
            listener?.invoke(ready)
        } catch (_: Exception) {
            lastFailure = LocalCandidateWorkerFailure.OWNER_CALLBACK
        }
    }
}
