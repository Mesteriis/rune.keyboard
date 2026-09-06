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
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
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
                SCORES_EQUAL -> engine.setMode(MODE_EQUAL)
                SCORES_PUBLIC_ORIGINAL -> engine.setMode(MODE_PUBLIC_ORIGINAL)
                SCORES_PUBLIC_CORRECTION -> engine.setMode(MODE_PUBLIC_CORRECTION)
                BLOCK_NEXT_PUBLIC -> engine.blockNextPublic()
                KILL_PROCESS -> { Process.killProcess(Process.myPid()); return }
                else -> return
            }
            if (callback != null) engine.snapshot(callback)
        }
        override fun observePublic(callback: ILifecyclePublicSnapshot?) {
            check(Binder.getCallingUid() == Process.myUid())
            if (callback != null) engine.publicSnapshot(callback)
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
        private var nextPublic: CountDownLatch? = null
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
        private var mode = MODE_EQUAL
        private var publicStarts = 0
        private var publicCompletions = 0
        private var publicActive = 0
        private var publicSession = 0L
        private var publicRevision = 0L
        private var publicRequest = 0L
        private var admittedMode = MODE_EQUAL
        private var completedSession = 0L
        private var completedRevision = 0L
        private var completedRequest = 0L
        private var completedMode = MODE_EQUAL
        private var invalidPublicRequests = 0

        fun recordTimeout() = synchronized(lock) { timeouts++ }

        fun blockNext() = synchronized(lock) {
            check(next == null && nextPublic == null && blocked == null)
            next = CountDownLatch(1)
        }
        fun blockNextPublic() = synchronized(lock) {
            check(mode != MODE_EQUAL && next == null && nextPublic == null && blocked == null)
            nextPublic = CountDownLatch(1)
        }
        fun setMode(value: Int) = synchronized(lock) {
            check(value in MODE_EQUAL..MODE_PUBLIC_CORRECTION)
            mode = value
            // Reset only a not-yet-admitted public latch; an active score keeps its captured mode.
            if (value == MODE_EQUAL) { nextPublic?.countDown(); nextPublic = null }
        }
        fun release() = synchronized(lock) { blocked?.countDown(); next?.countDown(); nextPublic?.countDown() }

        override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
            val admitted = synchronized(lock) {
                starts++; previousId = lastId; lastId = request.token.requestId
                active++; peakActive = maxOf(peakActive, active); cancellation = cancelled
                val isPublicPayload = request.prefix == "a " && request.continuations == listOf("helllo", "hello") &&
                    request.token.candidateIds == listOf(0, 1)
                val publicMode = mode != MODE_EQUAL
                val latch = if (publicMode && isPublicPayload && nextPublic != null) {
                    nextPublic.also { nextPublic = null }
                } else next.also { next = null }
                blocked = latch
                if (publicMode && isPublicPayload) {
                    publicStarts++; publicActive++
                    publicSession = request.token.sessionId; publicRevision = request.token.revision
                    publicRequest = request.token.requestId; admittedMode = mode
                } else if (publicMode) invalidPublicRequests++
                Admission(latch, mode, isPublicPayload)
            }
            try {
                // Explicit release keeps pending replacement deterministic even after cancellation.
                // This fixture is deliberately bounded and records any timeout as test failure.
                if (admitted.latch != null && !admitted.latch.await(10, TimeUnit.SECONDS)) {
                    synchronized(lock) { timeouts++ }
                }
                if (admitted.mode != MODE_EQUAL && !admitted.isPublicPayload) {
                    return ScoringReply(request.token, ScoringCode.INVALID, 0, emptyList())
                }
                val winner = if (admitted.mode == MODE_PUBLIC_CORRECTION) 1 else 0
                return ScoringReply(request.token, ScoringCode.OK, 0,
                    request.token.candidateIds.map {
                        NumericScore(it, if (admitted.mode == MODE_EQUAL || it == winner) -1.0 else -1000.0, 1)
                    })
            } finally {
                synchronized(lock) {
                    if (cancelled.get()) cancelledCompletions++
                    completions++; active--; blocked = null; cancellation = null
                    if (admitted.mode != MODE_EQUAL && admitted.isPublicPayload) {
                        publicCompletions++; publicActive--
                        completedSession = request.token.sessionId; completedRevision = request.token.revision
                        completedRequest = request.token.requestId; completedMode = admitted.mode
                    }
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

        private class Admission(val latch: CountDownLatch?, val mode: Int, val isPublicPayload: Boolean)

        fun publicSnapshot(callback: ILifecyclePublicSnapshot) = synchronized(lock) {
            try {
                callback.onSnapshot(mode, if (nextPublic == null) 0 else 1, publicStarts, publicCompletions,
                    publicActive, publicSession, publicRevision, publicRequest, admittedMode,
                    completedSession, completedRevision, completedRequest, completedMode, invalidPublicRequests)
            } catch (_: RemoteException) { /* Numeric observation owner is gone. */ }
        }

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
        const val SCORES_EQUAL = 10
        const val SCORES_PUBLIC_ORIGINAL = 11
        const val SCORES_PUBLIC_CORRECTION = 12
        const val BLOCK_NEXT_PUBLIC = 13
        const val MODE_EQUAL = 0
        const val MODE_PUBLIC_ORIGINAL = 1
        const val MODE_PUBLIC_CORRECTION = 2
    }
}
