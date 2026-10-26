package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.app.job.JobParameters
import android.app.job.JobService
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager
import android.os.SystemClock
import android.os.storage.StorageManager
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import java.time.ZonedDateTime
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/** Evaluates an inactive compact candidate; only a complete passing snapshot can be committed. */
class LearningEvaluationJobService : JobService() {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "rune-learning-evaluation").apply { priority = Thread.NORM_PRIORITY - 1 }
    }
    @Volatile private var running: Future<*>? = null
    @Volatile private var stopped = false
    private var lastConditionCheck = Long.MIN_VALUE
    private var lastConditionResult = false

    override fun onStartJob(params: JobParameters): Boolean {
        stopped = false
        running = executor.submit {
            val enabled = learningEnabled()
            val inWindow = LearningJobPolicy.isNight(ZonedDateTime.now())
            if (!enabled) return@submit finish(params, retry = false, scheduleNext = false)
            if (!inWindow) return@submit finish(params, retry = false, scheduleNext = true)
            if (!runtimeConditionsHold(force = true))
                return@submit finish(params, retry = true, scheduleNext = false)
            val store = LearningStore.get(applicationContext)
            if (!awaitStore(store)) return@submit finish(params, retry = !stopped, scheduleNext = false)
            val snapshot = store.snapshot()
            val cancelled = { stopped || Thread.currentThread().isInterrupted || !runtimeConditionsHold() }
            val rollbackEvaluation = if (snapshot.rollbackPolicy == null) null else try {
                AndroidLearningEvaluation.runRollback(applicationContext.assets, snapshot, cancelled)
            } catch (_: Exception) {
                return@submit finish(params, retry = true, scheduleNext = false)
            }
            if (rollbackEvaluation?.cancelled == true) {
                val stillNight = LearningJobPolicy.isNight(ZonedDateTime.now())
                return@submit finish(params, retry = !stopped && stillNight,
                    scheduleNext = !stopped && !stillNight)
            }
            if (rollbackEvaluation != null && !LearningEvaluator.completePolicyEvidence(rollbackEvaluation)) {
                return@submit finish(params, retry = rollbackEvaluation.unavailable != 0,
                    scheduleNext = rollbackEvaluation.unavailable == 0)
            }
            if (rollbackEvaluation != null && LearningEvaluator.rollbackQualified(rollbackEvaluation)) {
                if (stopped || Thread.currentThread().isInterrupted || !runtimeConditionsHold(force = true)) {
                    val stillNight = LearningJobPolicy.isNight(ZonedDateTime.now())
                    return@submit finish(params, retry = !stopped && stillNight,
                        scheduleNext = !stopped && !stillNight)
                }
                val committed = CountDownLatch(1)
                var rolledBack = false
                store.rollback(snapshot) { success -> rolledBack = success; committed.countDown() }
                val completed = awaitCommit(committed)
                return@submit finish(params, retry = !completed || !rolledBack,
                    scheduleNext = completed && rolledBack)
            }
            if (snapshot.candidatePolicy() == snapshot.activePolicy) {
                return@submit finish(params, retry = false, scheduleNext = true)
            }
            val result = try {
                AndroidLearningEvaluation.run(applicationContext.assets, snapshot, cancelled)
            } catch (_: Exception) {
                null
            }
            if (result == null || result.cancelled) {
                val stillNight = LearningJobPolicy.isNight(ZonedDateTime.now())
                return@submit finish(params, retry = !stopped && stillNight,
                    scheduleNext = !stopped && !stillNight)
            }
            if (!result.promotion.promotionApproved) {
                return@submit finish(params, retry = false, scheduleNext = true)
            }
            if (stopped || Thread.currentThread().isInterrupted || !runtimeConditionsHold(force = true)) {
                val stillNight = LearningJobPolicy.isNight(ZonedDateTime.now())
                return@submit finish(params, retry = !stopped && stillNight,
                    scheduleNext = !stopped && !stillNight)
            }
            val committed = CountDownLatch(1)
            var promoted = false
            store.promoteCandidate(snapshot) { success -> promoted = success; committed.countDown() }
            val completed = awaitCommit(committed)
            finish(params, retry = !completed || !promoted, scheduleNext = completed && promoted)
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        stopped = true
        running?.cancel(true)
        return true
    }

    override fun onDestroy() {
        stopped = true
        running?.cancel(true)
        executor.shutdownNow()
        super.onDestroy()
    }

    private fun awaitStore(store: LearningStore): Boolean {
        val deadline = SystemClock.elapsedRealtime() + STORE_TIMEOUT_MILLIS
        while (!stopped && store.readiness == LearningStore.Readiness.LOADING &&
            SystemClock.elapsedRealtime() < deadline) {
            try { Thread.sleep(25) } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                return false
            }
        }
        return !stopped && store.isReady
    }

    private fun learningEnabled(): Boolean = KeyboardPreferences(applicationContext).readSettings().let {
        it.collectExamples && it.typoPatterns
    }

    private fun awaitCommit(latch: CountDownLatch): Boolean = try {
        latch.await(COMMIT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
    } catch (_: InterruptedException) {
        Thread.currentThread().interrupt()
        false
    }

    private fun runtimeConditionsHold(force: Boolean = false): Boolean {
        val now = SystemClock.elapsedRealtime()
        if (!force && now - lastConditionCheck in 0 until CONDITION_RECHECK_MILLIS)
            return lastConditionResult
        lastConditionCheck = now
        lastConditionResult = computeRuntimeConditions()
        return lastConditionResult
    }

    private fun computeRuntimeConditions(): Boolean {
        val power = getSystemService(PowerManager::class.java)
        val battery = registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return false
        val status = battery.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        val level = battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = battery.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        val storageNotLow = try {
            val storage = getSystemService(StorageManager::class.java)
            storage.getAllocatableBytes(storage.getUuidForPath(filesDir)) >= MINIMUM_STORAGE_BYTES
        } catch (_: Exception) {
            false
        }
        return LearningJobPolicy.allowsRun(LearningJobPolicy.RuntimeConditions(
            enabled = learningEnabled(),
            night = LearningJobPolicy.isNight(ZonedDateTime.now()),
            idle = power.isDeviceIdleMode,
            thermallySafe = thermallySafe(power),
            charging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                status == BatteryManager.BATTERY_STATUS_FULL,
            batteryNotLow = level >= 0 && scale > 0 &&
                level * 100L >= scale * MINIMUM_BATTERY_PERCENT,
            storageNotLow = storageNotLow,
        ))
    }

    private fun thermallySafe(power: PowerManager): Boolean {
        if (Build.VERSION.SDK_INT >= 29) return power.currentThermalStatus <= PowerManager.THERMAL_STATUS_LIGHT
        val battery = registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return false
        val tenthsCelsius = battery.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1)
        return tenthsCelsius in 0..MAXIMUM_BATTERY_TEMPERATURE_TENTHS
    }

    private fun finish(params: JobParameters, retry: Boolean, scheduleNext: Boolean) {
        if (stopped) return
        val nextReady = !scheduleNext || LearningJobScheduler.scheduleFollowing(applicationContext, params.jobId)
        jobFinished(params, retry || !nextReady)
    }

    private companion object {
        const val STORE_TIMEOUT_MILLIS = 5_000L
        const val COMMIT_TIMEOUT_SECONDS = 10L
        const val CONDITION_RECHECK_MILLIS = 1_000L
        const val MINIMUM_BATTERY_PERCENT = 20L
        const val MINIMUM_STORAGE_BYTES = 64L * 1024L * 1024L
        const val MAXIMUM_BATTERY_TEMPERATURE_TENTHS = 380
    }
}
