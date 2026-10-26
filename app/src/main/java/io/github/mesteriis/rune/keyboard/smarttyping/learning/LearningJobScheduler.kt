package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import java.time.ZonedDateTime

/** One-shot jobs keep the execution window anchored to local night across DST changes. */
object LearningJobScheduler {
    private const val JOB_A = 0x52554c31
    private const val JOB_B = 0x52554c32

    fun sync(context: Context, enabled: Boolean): Boolean {
        val scheduler = context.getSystemService(JobScheduler::class.java)
        if (!enabled) {
            scheduler.cancel(JOB_A)
            scheduler.cancel(JOB_B)
            return true
        }
        if (scheduler.getPendingJob(JOB_A) != null || scheduler.getPendingJob(JOB_B) != null) return true
        return schedule(context, JOB_A, LearningJobPolicy.delayUntilNight(ZonedDateTime.now(), true))
    }

    internal fun scheduleFollowing(context: Context, completedJobId: Int): Boolean {
        val next = if (completedJobId == JOB_A) JOB_B else JOB_A
        val scheduler = context.getSystemService(JobScheduler::class.java)
        scheduler.cancel(next)
        return schedule(context, next, LearningJobPolicy.delayUntilNight(ZonedDateTime.now(), false))
    }

    private fun schedule(context: Context, jobId: Int, delayMillis: Long): Boolean {
        val info = JobInfo.Builder(jobId, ComponentName(context, LearningEvaluationJobService::class.java))
            .setPersisted(false)
            .setRequiresCharging(true)
            .setRequiresDeviceIdle(true)
            .setRequiresBatteryNotLow(true)
            .setRequiresStorageNotLow(true)
            .setMinimumLatency(delayMillis)
            .build()
        return context.getSystemService(JobScheduler::class.java).schedule(info) == JobScheduler.RESULT_SUCCESS
    }
}
