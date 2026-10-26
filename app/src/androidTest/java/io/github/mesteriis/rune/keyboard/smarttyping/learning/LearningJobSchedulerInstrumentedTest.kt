package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.app.job.JobScheduler
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LearningJobSchedulerInstrumentedTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()
    private val scheduler get() = context.getSystemService(JobScheduler::class.java)

    @After fun cleanUp() {
        scheduler.allPendingJobs.filter { it.service.className == LearningEvaluationJobService::class.java.name }
            .forEach { scheduler.cancel(it.id) }
    }

    @Test fun schedulesNightWorkerWithEverySystemConstraint() {
        cleanUp()
        assertTrue(LearningJobScheduler.sync(context, enabled = true))
        val job = scheduler.allPendingJobs.singleOrNull {
            it.service.className == LearningEvaluationJobService::class.java.name
        }
        assertNotNull(job)
        checkNotNull(job)
        assertTrue(!job.isPersisted)
        assertTrue(job.isRequireCharging)
        assertTrue(job.isRequireDeviceIdle)
        assertTrue(job.isRequireBatteryNotLow)
        assertTrue(job.isRequireStorageNotLow)
        assertEquals(LearningEvaluationJobService::class.java.name, job.service.className)
        assertTrue(LearningJobScheduler.sync(context, enabled = false))
        assertTrue(scheduler.allPendingJobs.none {
            it.service.className == LearningEvaluationJobService::class.java.name
        })
    }
}
