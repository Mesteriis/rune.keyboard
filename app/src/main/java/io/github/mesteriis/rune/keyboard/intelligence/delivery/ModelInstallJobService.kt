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
    @Volatile private var coordinator: ModelInstallCoordinator? = null
    @Volatile private var stopped = false

    override fun onStartJob(params: JobParameters): Boolean {
        stopped = false
        running = executor.submit {
            val current = ModelInstallCoordinator(applicationContext).also { coordinator = it }
            try {
                current.run()
            } finally {
                current.close()
                coordinator = null
                if (!stopped) jobFinished(params, false)
            }
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        stopped = true
        coordinator?.cancelCurrentOperation()
        running?.cancel(true)
        // Journal/private files are reconciled explicitly when Model Settings opens again.
        return false
    }

    override fun onDestroy() {
        running?.cancel(true)
        executor.shutdownNow()
        super.onDestroy()
    }
}
