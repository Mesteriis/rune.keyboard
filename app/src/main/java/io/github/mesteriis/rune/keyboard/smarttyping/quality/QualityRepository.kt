package io.github.mesteriis.rune.keyboard.smarttyping.quality

import java.util.concurrent.Executor

/** Storage methods run only on the supplied serial I/O executor. Null means no existing file. */
interface QualityStorage {
    fun read(): QualitySnapshot?
    fun write(snapshot: QualitySnapshot): Boolean
}

/** Serial, coalesced persistence. No submitted task captures editor text. */
class QualityRepository(private val storage: QualityStorage, private val worker: Executor) : QualityRecorder {
    enum class Readiness { LOADING, READY, RESETTING, FAILED }
    private val lock = Any()
    private val model = QualityModel()
    private var generation = 0L
    private var writeScheduled = false
    @Volatile var readiness = Readiness.LOADING
        private set
    @Volatile var lastWriteSucceeded: Boolean? = null
        private set
    val isReady: Boolean get() = readiness == Readiness.READY

    init {
        val initialGeneration = generation
        worker.execute {
            val loaded = try { storage.read() ?: QualitySnapshot() } catch (_: Exception) { null }
            synchronized(lock) {
                if (generation == initialGeneration) {
                    if (loaded == null) readiness = Readiness.FAILED
                    else { model.restore(loaded); readiness = Readiness.READY }
                }
            }
        }
    }

    override fun configure(metricsEnabled: Boolean, shadowEnabled: Boolean, eligible: Boolean) = synchronized(lock) {
        model.configure(metricsEnabled, shadowEnabled, eligible)
    }

    override fun record(event: QualityEvent) = update { record(event) }
    override fun candidateResponseNanos(durationNanos: Long) = update { candidateResponseNanos(durationNanos) }
    override fun compare(revision: Long, source: String, primaryChoice: String, experimentalChoice: String) =
        update { compare(revision, source, primaryChoice, experimentalChoice) }
    override fun explicitChoice(revision: Long, chosen: String) = update { explicitChoice(revision, chosen) }
    override fun invalidatePending() = synchronized(lock) { model.invalidatePending() }
    fun snapshot(): QualitySnapshot = synchronized(lock) { model.snapshot() }

    private inline fun update(change: QualityModel.() -> Boolean) {
        synchronized(lock) {
            if (!isReady || !model.change()) return
            lastWriteSucceeded = null
            if (writeScheduled) return
            writeScheduled = true
            worker.execute {
                val snapshot = synchronized(lock) {
                    writeScheduled = false
                    if (isReady) model.snapshot() else null
                }
                if (snapshot != null) {
                    val success = writeSafely(snapshot)
                    synchronized(lock) {
                        lastWriteSucceeded = success
                        if (!success && readiness == Readiness.READY) {
                            readiness = Readiness.FAILED
                            model.invalidatePending()
                        }
                    }
                }
            }
        }
    }

    /**
     * Clears memory immediately and blocks collection until the empty snapshot is durable.
     * One reset may run at a time. Callback is outside the lock; completion success means disk saved.
     */
    fun reset(onComplete: (Boolean) -> Unit = {}) {
        val accepted = synchronized(lock) {
            if (readiness == Readiness.RESETTING) false else {
                generation++
                readiness = Readiness.RESETTING
                lastWriteSucceeded = null
                model.reset()
                worker.execute {
                    val success = writeSafely(QualitySnapshot())
                    synchronized(lock) {
                        lastWriteSucceeded = success
                        readiness = if (success) Readiness.READY else Readiness.FAILED
                    }
                    onComplete(success)
                }
                true
            }
        }
        if (!accepted) onComplete(false)
    }

    private fun writeSafely(snapshot: QualitySnapshot): Boolean =
        try { storage.write(snapshot) } catch (_: Exception) { false }
}
