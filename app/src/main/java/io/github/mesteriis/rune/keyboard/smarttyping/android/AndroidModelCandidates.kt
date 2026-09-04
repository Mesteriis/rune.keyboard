package io.github.mesteriis.rune.keyboard.smarttyping.android

import android.content.Context
import android.os.Handler
import android.os.Looper
import io.github.mesteriis.rune.keyboard.intelligence.client.BoundModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.readiness.ActiveModelReadiness
import io.github.mesteriis.rune.keyboard.intelligence.readiness.DiskModelReadinessProbe
import io.github.mesteriis.rune.keyboard.smarttyping.session.CandidateOwnerState
import io.github.mesteriis.rune.keyboard.smarttyping.session.ModelCandidateCoordinator
import io.github.mesteriis.rune.keyboard.smarttyping.session.ModelPauseScheduler
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.NoopSmartTypingTracer
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTracer
import java.io.File
import java.util.concurrent.Executor

/** Composition root only. Storage receives no typing/controller/owner payload or callback. */
object AndroidModelCandidates {
    fun create(context: Context, controller: TypingSessionController,
        ownerState: () -> CandidateOwnerState, changed: () -> Unit,
        trace: SmartTypingTracer = NoopSmartTypingTracer): ModelCandidateCoordinator {
        val app = context.applicationContext
        val handler = Handler(Looper.getMainLooper())
        val readiness = ActiveModelReadiness(
            DiskModelReadinessProbe { File(app.noBackupFilesDir, "model-delivery") }::read,
            Executor { task -> check(handler.post(task)) { "Readiness owner dispatcher stopped" } },
        )
        val pause = object : ModelPauseScheduler {
            override fun postDelayed(task: Runnable, millis: Long) {
                check(handler.postDelayed(task, millis)) { "Model candidate dispatcher stopped" }
            }
            override fun remove(task: Runnable) { handler.removeCallbacks(task) }
        }
        return ModelCandidateCoordinator(controller, { listener -> BoundModelScoringClient(app, listener) },
            pause, ownerState, readiness, changed, trace)
    }
}
