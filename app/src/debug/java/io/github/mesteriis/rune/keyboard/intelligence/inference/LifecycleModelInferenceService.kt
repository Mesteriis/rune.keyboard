package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.ComponentCallbacks2
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import android.os.Process
import android.os.RemoteException
import io.github.mesteriis.rune.keyboard.intelligence.ipc.NumericScore
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Only the engine is synthetic. Scoring uses the unchanged production Binder and worker. */
class LifecycleModelInferenceService : ModelInferenceService() {
    private val engine = ControlledEngine()
    private lateinit var invalidate: () -> Unit
    @Volatile private var scoringUnbound = CountDownLatch(1)
    @Volatile private var scoringBound = CountDownLatch(1)
    override val idleMillis: Long get() = 750
    override fun createEngine(onInvalidated: () -> Unit): ScoringEngine {
        invalidate = onInvalidated
        return engine
    }

    private val control = object : ILifecycleControl.Stub() {
        @Suppress("DEPRECATION")
        override fun command(operation: Int, callback: ILifecycleSnapshot?) {
            check(Binder.getCallingUid() == Process.myUid())
            when (operation) {
                SNAPSHOT -> Unit
                BLOCK_NEXT -> engine.blockNext()
                RELEASE -> engine.release()
                INVALIDATE -> invalidate()
                TRIM_CRITICAL -> onTrimMemory(ComponentCallbacks2.TRIM_MEMORY_RUNNING_CRITICAL)
                TRIM_BACKGROUND -> onTrimMemory(ComponentCallbacks2.TRIM_MEMORY_BACKGROUND)
                LOW_MEMORY -> onLowMemory()
                AWAIT_SCORING_UNBOUND -> if (!scoringUnbound.await(3, TimeUnit.SECONDS)) engine.recordTimeout()
                AWAIT_SCORING_BOUND -> if (!scoringBound.await(3, TimeUnit.SECONDS)) engine.recordTimeout()
                KILL_PROCESS -> { Process.killProcess(Process.myPid()); return }
                else -> return
            }
            if (callback != null) engine.snapshot(callback)
        }
    }

    override fun onBind(intent: Intent?): IBinder {
        if (intent?.action == CONTROL_ACTION) return control
        scoringUnbound = CountDownLatch(1)
        return super.onBind(intent).also { scoringBound.countDown() }
    }

    override fun onRebind(intent: Intent?) {
        if (intent?.action == CONTROL_ACTION) return
        scoringUnbound = CountDownLatch(1)
        super.onRebind(intent)
        scoringBound.countDown()
    }

    // Android tracks onUnbind separately for the two explicit Intent actions.
    // Releasing the test-only control binding must not invalidate a live scoring binding.
    override fun onUnbind(intent: Intent?): Boolean {
        if (intent?.action == CONTROL_ACTION) return false
        scoringBound = CountDownLatch(1)
        return super.onUnbind(intent).also { scoringUnbound.countDown() }
    }

    private class ControlledEngine : ScoringEngine {
        private val lock = Any()
        private var next: CountDownLatch? = null
        private var blocked: CountDownLatch? = null
        private var cancellation: AtomicBoolean? = null
        private var starts = 0
        private var previousId = 0L
        private var lastId = 0L
        private var active = 0
        private var peakActive = 0
        private var cancels = 0
        private var cancelledCompletions = 0
        private var completions = 0
        private var unloads = 0
        private var unloadedCompletions = 0
        private var orderViolations = 0
        private var timeouts = 0

        fun recordTimeout() = synchronized(lock) { timeouts++ }

        fun blockNext() = synchronized(lock) {
            check(next == null && blocked == null)
            next = CountDownLatch(1)
        }
        fun release() = synchronized(lock) { blocked?.countDown(); next?.countDown() }

        override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
            val latch = synchronized(lock) {
                starts++; previousId = lastId; lastId = request.token.requestId
                active++; peakActive = maxOf(peakActive, active); cancellation = cancelled
                next.also { next = null; blocked = it }
            }
            try {
                // Explicit release keeps pending replacement deterministic even after cancellation.
                // This fixture is deliberately bounded and records any timeout as test failure.
                if (latch != null && !latch.await(10, TimeUnit.SECONDS)) {
                    synchronized(lock) { timeouts++ }
                }
                return ScoringReply(request.token, 0, 0,
                    request.token.candidateIds.map { NumericScore(it, -1.0, 1) })
            } finally {
                synchronized(lock) {
                    if (cancelled.get()) cancelledCompletions++
                    completions++; active--; blocked = null; cancellation = null
                }
            }
        }
        override fun cancel() = synchronized(lock) {
            cancels++
            // Worker must set its request atomic before calling the runtime cancellation hook.
            if (cancellation?.get() == false) orderViolations++
        }
        override fun unload() { synchronized(lock) { unloads++; unloadedCompletions = completions } }
        override fun close() { release(); unload() }

        fun snapshot(callback: ILifecycleSnapshot) = synchronized(lock) {
            try {
                callback.onSnapshot(Process.myPid(), Process.myUid(), starts, previousId, lastId,
                    active, peakActive, cancels, cancelledCompletions, completions, unloads,
                    unloadedCompletions, orderViolations, timeouts)
            } catch (_: RemoteException) { /* A dead test owner needs no retained snapshot. */ }
        }
    }

    companion object {
        const val CONTROL_ACTION = "io.github.mesteriis.rune.keyboard.DEBUG_SCORING_CONTROL"
        const val SNAPSHOT = 0
        const val BLOCK_NEXT = 1
        const val RELEASE = 2
        const val INVALIDATE = 3
        const val TRIM_CRITICAL = 4
        const val KILL_PROCESS = 5
        const val TRIM_BACKGROUND = 6
        const val LOW_MEMORY = 7
        const val AWAIT_SCORING_UNBOUND = 8
        const val AWAIT_SCORING_BOUND = 9
    }
}
