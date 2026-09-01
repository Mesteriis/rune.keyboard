package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context

object ModelDeliveryJobScheduler {
    private const val JOB_ID = 0x52554e45

    fun schedule(context: Context): Boolean {
        val scheduler = context.getSystemService(JobScheduler::class.java)
        val result = scheduler.schedule(
            JobInfo.Builder(JOB_ID, ComponentName(context, ModelInstallJobService::class.java))
                .setPersisted(false)
                .setMinimumLatency(0)
                .build(),
        )
        return result == JobScheduler.RESULT_SUCCESS
    }

    fun cancel(context: Context) {
        context.getSystemService(JobScheduler::class.java).cancel(JOB_ID)
    }
}
