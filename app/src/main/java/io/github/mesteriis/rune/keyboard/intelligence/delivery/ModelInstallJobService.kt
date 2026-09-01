package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.app.job.JobParameters
import android.app.job.JobService
import java.util.concurrent.Executors
import java.util.concurrent.Future

class ModelInstallJobService : JobService() {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "rune-model-install").apply { priority = Thread.NORM_PRIORITY - 1 }
    }
    @Volatile private var running: Future<*>? = null

    override fun onStartJob(params: JobParameters): Boolean {
        running = executor.submit {
            try {
                ModelInstallCoordinator(applicationContext).run()
            } finally {
                jobFinished(params, false)
            }
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        running?.cancel(true)
        return true
    }

    override fun onDestroy() {
        running?.cancel(true)
        executor.shutdownNow()
        super.onDestroy()
    }
}
