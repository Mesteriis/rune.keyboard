package io.github.mesteriis.rune.keyboard.intelligence.client

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.RemoteException
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringCallback
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreReplyParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreRequestParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken

/** Main-thread lifecycle, only oneway IPC; IME/controller integration belongs to PR7. */
class BoundModelScoringClient(context: Context, private val listener: ModelScoringListener) : ModelScoringClient {
    private val context = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val guard = LatestReplyGuard()
    private var endpoint: IModelScoringService? = null
    private var connection: ServiceConnection? = null
    private var latest: ScoringToken? = null
    private var generation = 0L
    private var retry: Runnable? = null
    override val available get() = endpoint != null && guard.shouldBind()
    private val callback = object : IModelScoringCallback.Stub() {
        override fun onResult(reply: ScoreReplyParcel?) {
            val result = reply?.value ?: return
            main.post {
                if (guard.accepts(result.token, listener.currentCompositionRevision())) {
                    guard.invalidate(); latest = null; listener.onReply(result)
                }
            }
        }
    }
    override fun attachSession(sessionId: Long?, effectiveAvailability: Boolean) {
        onMain(); cancel(); generation++; stopBinding()
        guard.attach(sessionId, effectiveAvailability)
        if (guard.shouldBind()) bind()
    }
    override fun score(input: ScoringInput) {
        onMain()
        val service = endpoint ?: return
        if (!guard.begin(input.token)) return
        latest?.let { try { service.cancel(it.sessionId, it.requestId) } catch (_: RemoteException) { } }
        latest = input.token
        try { service.score(ScoreRequestParcel(input), callback) }
        catch (_: RemoteException) { lost() }
    }
    override fun cancel() {
        onMain(); guard.invalidate()
        latest?.let { try { endpoint?.cancel(it.sessionId, it.requestId) } catch (_: RemoteException) { } }
        latest = null
    }
    override fun close() { attachSession(null, false) }
    private fun bind() {
        if (!guard.shouldBind() || connection != null) return
        val admittedGeneration = generation
        val candidate = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                if (generation != admittedGeneration || connection !== this || !guard.shouldBind()) return
                endpoint = IModelScoringService.Stub.asInterface(binder)
                listener.onAvailabilityChanged(true)
            }
            override fun onServiceDisconnected(name: ComponentName) { if (connection === this) lost() }
            override fun onBindingDied(name: ComponentName) { if (connection === this) lost() }
            override fun onNullBinding(name: ComponentName) { if (connection === this) lost() }
        }
        connection = candidate
        val intent = Intent().setComponent(ComponentName(context.packageName,
            "io.github.mesteriis.rune.keyboard.intelligence.inference.ModelInferenceService"))
        val bound = try { context.bindService(intent, candidate, Context.BIND_AUTO_CREATE) }
        catch (_: SecurityException) { false }
        if (!bound) lost() // Preserve candidate until stopBinding unbinds this attempt.
    }
    private fun lost() {
        onMain(); guard.invalidate(); latest = null; generation++; stopBinding()
        if (guard.shouldBind()) {
            val admittedGeneration = generation
            val task = Runnable { retry = null; if (generation == admittedGeneration && guard.shouldBind()) bind() }
            retry = task; main.postDelayed(task, 1000)
        }
    }
    private fun stopBinding() {
        retry?.let(main::removeCallbacks); retry = null
        val previous = connection; connection = null; endpoint = null
        if (previous != null) context.unbindService(previous)
        listener.onAvailabilityChanged(false)
    }
    private fun onMain() { check(Looper.myLooper() == Looper.getMainLooper()) }
}
