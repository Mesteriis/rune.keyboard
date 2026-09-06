package io.github.mesteriis.rune.keyboard.intelligence.readiness

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessSource
import java.util.concurrent.Executor
import java.util.concurrent.ThreadFactory
import java.util.concurrent.atomic.AtomicLong

/** One metadata reader and one replacing numeric demand. No editor/model payload crosses this boundary. */
class ActiveModelReadiness internal constructor(
    private val probe: (() -> Boolean) -> ModelReadinessHint,
    private val ownerDispatcher: Executor,
    private val threadFactory: ThreadFactory,
) : ModelReadinessSource {
    constructor(probe: (() -> Boolean) -> ModelReadinessHint, ownerDispatcher: Executor) : this(
        probe, ownerDispatcher, ThreadFactory { task -> Thread(task, "rune-model-readiness").apply { isDaemon = true } })

    private val ownerThread = Thread.currentThread()
    private val epoch = AtomicLong()
    private val monitor = Object()
    private var next: Long? = null
    private var running: Long? = null
    private var worker: Thread? = null
    private var closed = false
    private var active = false
    override var hint = ModelReadinessHint.UNKNOWN
        private set

    override fun setActive(active: Boolean) {
        checkOwner()
        synchronized(monitor) {
            if (closed) return
            if (this.active != active) {
                this.active = active; epoch.incrementAndGet(); next = null
                hint = ModelReadinessHint.UNKNOWN
            }
            if (!active || hint != ModelReadinessHint.UNKNOWN || next == epoch.get() || running == epoch.get()) return
            next = epoch.get()
            if (worker == null) worker = threadFactory.newThread(::run).also { it.start() }
            monitor.notifyAll()
        }
    }
    override fun close() {
        checkOwner()
        synchronized(monitor) {
            if (closed) return
            closed = true; active = false; epoch.incrementAndGet(); next = null
            hint = ModelReadinessHint.UNKNOWN; monitor.notifyAll()
        }
    }
    private fun run() {
        while (true) {
            val admitted = synchronized(monitor) {
                while (!closed && next == null) monitor.wait()
                if (closed) return
                checkNotNull(next).also { next = null; running = it }
            }
            val result = try { probe { epoch.get() != admitted } }
            catch (_: Exception) { ModelReadinessHint.BROKEN }
            try {
                ownerDispatcher.execute {
                    checkOwner()
                    synchronized(monitor) {
                        if (!closed && active && epoch.get() == admitted) hint = result
                        if (running == admitted) running = null
                    }
                }
            } catch (_: RuntimeException) {
                synchronized(monitor) {
                    // A lost owner cannot safely publish or retry; retire until the owner closes.
                    closed = true; active = false; next = null; epoch.incrementAndGet()
                }
                return
            }
        }
    }
    private fun checkOwner() = check(Thread.currentThread() === ownerThread) { "Readiness owner thread required" }
}
