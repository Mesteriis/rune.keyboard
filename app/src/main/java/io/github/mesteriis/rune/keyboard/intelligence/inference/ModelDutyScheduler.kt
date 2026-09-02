package io.github.mesteriis.rune.keyboard.intelligence.inference

import java.util.concurrent.ScheduledFuture
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit

/** A single active/cleanup check. Idle work has no scheduled timer. No stop/close joins. */
internal interface ModelDutyScheduler : AutoCloseable {
    fun start(task: Runnable)
    fun stop()
}
internal class ScheduledModelDutyChecks : ModelDutyScheduler {
    private val executor = ScheduledThreadPoolExecutor(1) { task ->
        Thread(task, "rune-scoring-duty").apply { isDaemon = true }
    }.apply { removeOnCancelPolicy = true }
    private var timer: ScheduledFuture<*>? = null
    override fun start(task: Runnable) {
        check(timer == null)
        // Do not replay missed checks in a burst after Android freezes a cached process.
        timer = executor.scheduleWithFixedDelay(task, ModelDutyProfile.CHECK_MILLIS,
            ModelDutyProfile.CHECK_MILLIS, TimeUnit.MILLISECONDS)
    }
    override fun stop() { timer?.cancel(false); timer = null }
    override fun close() { stop(); executor.shutdown() }
}
