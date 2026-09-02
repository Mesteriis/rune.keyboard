package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.app.Service
import android.content.ComponentCallbacks2
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import android.os.Process
import android.os.RemoteException
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringCallback
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreReplyParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreRequestParcel
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

open class ModelInferenceService : Service() {
    private lateinit var worker: LatestScoringWorker
    protected open val idleMillis: Long get() = 60_000
    protected open fun createEngine(onInvalidated: () -> Unit): ScoringEngine =
        ActiveModelScoringEngine(File(noBackupFilesDir, "model-delivery"), changed = onInvalidated)

    override fun onCreate() {
        super.onCreate()
        val duty = ProcessModelDuty.owner // establish the process baseline before engine construction
        worker = LatestScoringWorker(createEngine { worker.invalidate() }, idleMillis, duty, ScheduledModelDutyChecks())
    }
    private val endpoint = object : IModelScoringService.Stub() {
        override fun score(request: ScoreRequestParcel?, callback: IModelScoringCallback?) {
            requireSameUid()
            val input = request?.value ?: return
            val receiver = callback ?: return
            val binder = receiver.asBinder()
            val dead = AtomicBoolean()
            val death = IBinder.DeathRecipient {
                dead.set(true); worker.cancel(input.token.sessionId, input.token.requestId)
            }
            try { binder.linkToDeath(death, 0) } catch (_: RemoteException) { return }
            if (dead.get()) { binder.unlinkToDeath(death, 0); return }
            worker.submit(input, { reply ->
                if (!dead.get()) try { receiver.onResult(ScoreReplyParcel(reply)) } catch (_: RemoteException) { }
            }, { binder.unlinkToDeath(death, 0) })
            // Death between registration and queue admission still cancels its admitted work.
            if (dead.get()) worker.cancel(input.token.sessionId, input.token.requestId)
        }
        override fun cancel(sessionId: Long, requestId: Long) {
            requireSameUid(); worker.cancel(sessionId, requestId)
        }
    }
    override fun onBind(intent: Intent?): IBinder { worker.onBind(); return endpoint }
    // Android may retain this Service and its Binder after the last scoring client leaves.
    override fun onUnbind(intent: Intent?): Boolean { worker.onUnbind(); return true }
    override fun onRebind(intent: Intent?) { super.onRebind(intent); worker.onBind() }
    @Suppress("DEPRECATION")
    override fun onTrimMemory(level: Int) {
        if (level == ComponentCallbacks2.TRIM_MEMORY_RUNNING_CRITICAL || level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND) {
            worker.suspendForMemoryPressure()
        }
        super.onTrimMemory(level)
    }
    override fun onLowMemory() { worker.suspendForMemoryPressure(); super.onLowMemory() }
    override fun onDestroy() { worker.close(); super.onDestroy() }
    private fun requireSameUid() { check(Binder.getCallingUid() == Process.myUid()) { "private scoring service" } }
}
