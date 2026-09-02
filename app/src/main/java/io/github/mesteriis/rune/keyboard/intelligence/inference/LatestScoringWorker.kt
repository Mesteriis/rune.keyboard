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
class LatestScoringWorker(private val engine: ScoringEngine, private val idleMillis: Long = 60_000,
    private val now: () -> Long = { System.nanoTime() / 1_000_000 }) : AutoCloseable {
    private class Work(val input: ScoringInput, val deliver: (ScoringReply) -> Unit,
        val finished: () -> Unit, val cancelled: AtomicBoolean = AtomicBoolean())
    private val monitor = Object()
    private var pending: Work? = null
    private var active: Work? = null
    private var stopped = false
    private var unloadRequested = false
    private val worker = Thread(::run, "rune-scoring").apply { start() }

    fun submit(input: ScoringInput, deliver: (ScoringReply) -> Unit, finished: () -> Unit = {}) {
        val rejected = synchronized(monitor) {
            if (stopped) true else {
                pending?.let { it.cancelled.set(true); it.finished() }
                pending = Work(input, deliver, finished)
                cancelActive(); monitor.notifyAll(); false
            }
        }
        if (rejected) finished()
    }
    fun cancel(sessionId: Long, requestId: Long) = synchronized(monitor) {
        fun Work.matches() = input.token.sessionId == sessionId && input.token.requestId == requestId
        pending?.takeIf { it.matches() }?.let { pending = null; it.cancelled.set(true); it.finished() }
        active?.takeIf { it.matches() }?.let { cancelActive() }
    }
    fun invalidate() = synchronized(monitor) {
        pending?.let { pending = null; it.cancelled.set(true); it.finished() }
        cancelActive(); unloadRequested = true; monitor.notifyAll()
    }
    override fun close() = synchronized(monitor) {
        if (!stopped) { stopped = true; invalidate(); monitor.notifyAll() }
        // Lifecycle owner never waits on scoring/native teardown on main or Binder threads.
    }
    private fun cancelActive() {
        active?.let { it.cancelled.set(true); engine.cancel() }
    }
    private fun run() {
        var idleAt = now()
        var unloaded = false
        try {
            while (true) {
                var unload = false
                val work = synchronized(monitor) {
                    while (!stopped && pending == null && !unloadRequested) {
                        val remaining = idleMillis - (now() - idleAt)
                        if (!unloaded && remaining <= 0) { unloadRequested = true; break }
                        monitor.wait(if (unloaded) 0 else maxOf(1, remaining))
                    }
                    if (stopped) return
                    if (unloadRequested) { unloadRequested = false; unload = true }
                    if (unload) null else pending?.also { pending = null; active = it }
                }
                if (unload) { engine.unload(); unloaded = true; continue }
                if (work == null) continue
                unloaded = false
                val reply = try { engine.score(work.input, work.cancelled) }
                catch (_: Exception) { ScoringReply(work.input.token, ScoringCode.INTERNAL, 0, emptyList()) }
                synchronized(monitor) {
                    // Delivery is nonblocking (oneway Binder or a test callback).
                    if (!stopped && !work.cancelled.get()) work.deliver(reply)
                    active = null; work.finished(); idleAt = now()
                }
            }
        } finally {
            engine.close()
        }
    }
}
