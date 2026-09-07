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
class BoundModelScoringClient internal constructor(
    context: Context,
    private val listener: ModelScoringListener,
    private val retryScheduler: ModelRetryScheduler,
) : ModelScoringClient {
    constructor(context: Context, listener: ModelScoringListener) : this(context, listener, HandlerRetryScheduler())

    private val context = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val guard = LatestReplyGuard()
    private var endpoint: IModelScoringService? = null
    private var connection: ServiceConnection? = null
    private var latest: ScoringToken? = null
    private var generation = 0L
    private var retry: Runnable? = null
    private var attempts = 0
    private var closed = false
    private var publishedAvailable = false
    override val available get() = !closed && endpoint != null && guard.shouldBind()

    override fun attachSession(sessionId: Long?, effectiveAvailability: Boolean) {
        onMain()
        if (closed || !guard.attach(sessionId, effectiveAvailability)) return
        cancel(); generation++
        val attachment = generation
        stopBinding()
        attempts = 0
        publishAvailability()
        if (generation == attachment && !closed && guard.shouldBind()) bind()
    }
    override fun score(input: ScoringInput) {
        onMain()
        val service = endpoint ?: return
        val admittedConnection = connection ?: return
        if (closed || !guard.begin(input.token)) return
        latest?.let { try { service.cancel(it.sessionId, it.requestId) } catch (_: RemoteException) { } }
        latest = input.token
        try { service.score(ScoreRequestParcel(input), callback(generation, admittedConnection)) }
        catch (_: RemoteException) { lost() }
    }
    override fun cancel() {
        onMain(); guard.invalidate()
        val previous = latest; latest = null
        previous?.let { try { endpoint?.cancel(it.sessionId, it.requestId) } catch (_: RemoteException) { } }
    }
    override fun close() {
        onMain()
        if (closed) return
        closed = true
        cancel(); guard.attach(null, false); generation++
        stopBinding(); publishAvailability()
    }
    private fun callback(admittedGeneration: Long, admittedConnection: ServiceConnection) =
        object : IModelScoringCallback.Stub() {
            override fun onResult(reply: ScoreReplyParcel?) {
                val result = reply?.value ?: return
                main.post {
                    if (generation != admittedGeneration || connection !== admittedConnection || !available) {
                        try { listener.onDiscardedReply(result) } catch (_: Throwable) { }
                        return@post
                    }
                    val currentRequest = listener.isCurrentRequest(result.token)
                    if (guard.accepts(result.token) && currentRequest) {
                        guard.invalidate(); latest = null; listener.onReply(result)
                    } else {
                        try { listener.onDiscardedReply(result) } catch (_: Throwable) { }
                    }
                }
            }
        }
    private fun bind() {
        if (closed || !guard.shouldBind() || connection != null || attempts >= MAX_ATTEMPTS) return
        attempts++
        val admittedGeneration = generation
        val candidate = object : ServiceConnection {
            private fun current(): Boolean {
                onMain()
                return generation == admittedGeneration && connection === this && !closed && guard.shouldBind()
            }
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                if (!current() || endpoint != null) return
                if (!binder.isBinderAlive) { lost(); return }
                endpoint = IModelScoringService.Stub.asInterface(binder)
                if (endpoint == null) lost() else publishAvailability()
            }
            override fun onServiceDisconnected(name: ComponentName) { if (current()) lost() }
            override fun onBindingDied(name: ComponentName) { if (current()) lost() }
            override fun onNullBinding(name: ComponentName) { if (current()) lost() }
        }
        connection = candidate
        val intent = Intent().setComponent(ComponentName(context.packageName,
            "io.github.mesteriis.rune.keyboard.intelligence.inference.ModelInferenceService"))
        val bound = try { context.bindService(intent, candidate, Context.BIND_AUTO_CREATE) }
        catch (_: SecurityException) { false }
        // Preserve even a failed attempt until stopBinding releases its registration.
        if (!bound && generation == admittedGeneration && connection === candidate) lost()
    }
    private fun lost() {
        onMain(); guard.invalidate(); latest = null; generation++; stopBinding()
        if (!closed && guard.shouldBind() && attempts < MAX_ATTEMPTS) {
            val admittedGeneration = generation
            val task = object : Runnable {
                override fun run() {
                    onMain()
                    if (retry !== this || generation != admittedGeneration || closed || !guard.shouldBind()) return
                    retry = null
                    bind()
                }
            }
            retry = task
            retryScheduler.postDelayed(task, attempts * 1000L)
        }
        publishAvailability()
    }
    private fun stopBinding() {
        retry?.let(retryScheduler::remove); retry = null
        val previous = connection; connection = null; endpoint = null
        if (previous != null) context.unbindService(previous)
    }
    private fun publishAvailability() {
        val current = available
        if (current == publishedAvailable) return
        publishedAvailable = current
        listener.onAvailabilityChanged(current)
    }
    private fun onMain() { check(Looper.myLooper() == Looper.getMainLooper()) }

    private companion object { const val MAX_ATTEMPTS = 3 }
}

/** Only retry time is injectable; result callbacks always use the real main Handler. */
internal interface ModelRetryScheduler {
    fun postDelayed(task: Runnable, delayMillis: Long)
    fun remove(task: Runnable)
}
private class HandlerRetryScheduler : ModelRetryScheduler {
    private val main = Handler(Looper.getMainLooper())
    override fun postDelayed(task: Runnable, delayMillis: Long) { main.postDelayed(task, delayMillis) }
    override fun remove(task: Runnable) { main.removeCallbacks(task) }
}
