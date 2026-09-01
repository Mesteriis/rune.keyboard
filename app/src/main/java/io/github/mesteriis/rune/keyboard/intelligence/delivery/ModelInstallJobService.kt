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
    @Volatile private var stopped = false

    override fun onStartJob(params: JobParameters): Boolean {
        stopped = false
        running = executor.submit {
            try {
                val store = DeliveryStateStore.forApplication(applicationContext)
                ModelOperationGate(store.stateFile.parentFile!!).withLock {
                    ModelInstallCoordinator(applicationContext).run()
                }
            } finally {
                if (!stopped) jobFinished(params, false)
            }
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        stopped = true
        running?.cancel(true)
        // Reconciliation resumes when Model Settings opens or DownloadManager wakes the receiver.
        return false
    }

    override fun onDestroy() {
        stopped = true
        running?.cancel(true)
        executor.shutdownNow()
        super.onDestroy()
    }
}
