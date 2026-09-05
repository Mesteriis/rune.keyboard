package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.ComponentName
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Process
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.intelligence.client.BoundModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringCallback
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreReplyParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreRequestParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import org.junit.Assert.*
import org.junit.Test
import java.util.Collections
import java.util.IdentityHashMap
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.FutureTask
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong

/** Actual ServiceDispatcher/Binder/process tests; the remote engine returns only synthetic scores. */
class ScoringLifecycleInstrumentedTest {
    @Test fun debugFixtureIsPrivateSameUidAndActuallyRemote() = Fixture().use { f ->
        @Suppress("DEPRECATION")
        val info = f.context.packageManager.getServiceInfo(f.component, 0)
        assertFalse(info.exported)
        assertNull(info.permission)
        assertEquals(f.context.packageName + ":model_runtime", info.processName)
        val snapshot = f.command()
        assertEquals(Process.myUid(), snapshot.uid)
        assertNotEquals(Process.myPid(), snapshot.processId)
        assertNull(f.rawBinder.queryLocalInterface(
            "io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService"))
    }

    @Test fun onewayTransportKeepsOneActiveAndOnlyLatestPending() = Fixture().use { f ->
        val base = f.command()
        f.command(LifecycleModelInferenceService.BLOCK_NEXT)
        f.score(101)
        f.await { it.active == 1 && it.lastId == 101L }
        f.score(102)
        f.score(103)
        // These requests target the same oneway Binder, preserving their admission order.
        val blocked = f.await { it.cancels >= base.cancels + 2 }
        assertEquals(base.starts + 1, blocked.starts)
        assertEquals(1, blocked.active)
        f.command(LifecycleModelInferenceService.RELEASE)
        assertEquals(103L, f.replies.poll(3, TimeUnit.SECONDS))
        val done = f.await { it.completions == base.completions + 2 }
        assertEquals(101L, done.previousId)
        assertEquals(103L, done.lastId)
        assertEquals(base.cancelledCompletions + 1, done.cancelledCompletions)
        assertEquals(1, done.peakActive)
        assertTrue(f.replies.isEmpty())
        f.assertHealthy(done)
    }

    @Test fun immediateCancelSuppressesCallbackAndDoesNotWaitForScore() = Fixture().use { f ->
        val base = f.command()
        f.command(LifecycleModelInferenceService.BLOCK_NEXT)
        f.score(201)
        f.await { it.active == 1 && it.lastId == 201L }
        f.service.cancel(1, 201)
        val cancelled = f.await { it.cancels > base.cancels }
        assertEquals(1, cancelled.active) // cancel roundtrip completed while score is still blocked
        f.command(LifecycleModelInferenceService.RELEASE)
        f.await { it.completions > base.completions }
        // A following callback from the same worker/Binder drains any earlier result.
        f.score(202)
        assertEquals(202L, f.replies.poll(3, TimeUnit.SECONDS))
        assertTrue(f.replies.isEmpty())
        f.assertHealthy(f.command())
    }

    @Test fun criticalTrimAndInvalidationDropPendingCancelActiveAndUnload() {
        listOf(LifecycleModelInferenceService.TRIM_CRITICAL,
            LifecycleModelInferenceService.INVALIDATE).forEach { operation ->
            Fixture().use { f ->
                val base = f.command()
                f.command(LifecycleModelInferenceService.BLOCK_NEXT)
                f.score(301)
                f.await { it.active == 1 && it.lastId == 301L }
                f.score(302)
                f.await { it.cancels > base.cancels }
                val before = f.command(operation)
                assertEquals(1, before.active)
                f.command(LifecycleModelInferenceService.RELEASE)
                val after = f.await { it.active == 0 && it.unloads > before.unloads }
                assertEquals(base.starts + 1, after.starts)
                assertEquals(base.cancelledCompletions + 1, after.cancelledCompletions)
                f.score(303)
                if (operation == LifecycleModelInferenceService.TRIM_CRITICAL) {
                    assertEquals(-303L, f.replies.poll(3, TimeUnit.SECONDS))
                    assertEquals(ScoringCode.UNAVAILABLE, f.codes.poll(3, TimeUnit.SECONDS))
                    assertEquals(base.starts + 1, f.command().starts)
                    f.rebindScoring()
                    f.score(304)
                    assertEquals(304L, f.replies.poll(3, TimeUnit.SECONDS))
                } else assertEquals(303L, f.replies.poll(3, TimeUnit.SECONDS))
                assertTrue(f.replies.isEmpty())
                f.assertHealthy(f.command())
            }
        }
    }

    @Test fun criticalBackgroundAndLowMemoryRemainSuspendedUntilActualUnbindBind() {
        for (pressure in listOf(LifecycleModelInferenceService.TRIM_CRITICAL,
            LifecycleModelInferenceService.TRIM_BACKGROUND, LifecycleModelInferenceService.LOW_MEMORY)) {
            Fixture().use { f ->
                val base = f.command()
                f.command(pressure)
                f.score(701)
                assertEquals(-701L, f.replies.poll(3, TimeUnit.SECONDS))
                assertEquals(ScoringCode.UNAVAILABLE, f.codes.poll(3, TimeUnit.SECONDS))
                f.command(LifecycleModelInferenceService.INVALIDATE) // version invalidation cannot clear pressure
                f.score(702)
                assertEquals(-702L, f.replies.poll(3, TimeUnit.SECONDS))
                assertEquals(ScoringCode.UNAVAILABLE, f.codes.poll(3, TimeUnit.SECONDS))
                assertEquals(base.starts, f.command().starts)
                // Control stays bound, so the same Service/worker/owner survives this real lifecycle edge.
                f.rebindScoring()
                f.score(703)
                assertEquals(703L, f.replies.poll(3, TimeUnit.SECONDS))
                assertEquals(ScoringCode.OK, f.codes.poll(3, TimeUnit.SECONDS))
                assertEquals(base.starts + 1, f.command().starts)
                f.assertHealthy(f.command())
            }
        }
    }

    @Test fun idleWorkerUnloadsAfterCompletionWithoutMoreInput() = Fixture().use { f ->
        val base = f.command()
        f.score(401)
        assertEquals(401L, f.replies.poll(3, TimeUnit.SECONDS))
        val completed = f.command()
        val idle = f.await { it.unloadedCompletions == base.completions + 1 }
        assertEquals(completed.starts, idle.starts)
        assertEquals(0, idle.active)
        f.assertHealthy(idle)
    }

    @Test fun realClientRebindsAfterProcessDeathWithoutReplayingPayload() = Fixture().use { f ->
        ClientProbe(f.context).use { p ->
            p.attach(7, true)
            p.awaitAvailable()
            f.command(LifecycleModelInferenceService.BLOCK_NEXT)
            p.score(501)
            f.await { it.active == 1 && it.lastId == 501L }
            val oldProcess = f.command().processId
            p.availability.clear()
            f.kill()
            p.awaitUnavailable()
            p.awaitAvailable()
            f.reconnectControl()
            val restarted = f.command()
            assertNotEquals(oldProcess, restarted.processId)
            assertEquals(0, restarted.starts)
            assertTrue(p.replies.isEmpty())
            p.score(502)
            assertEquals(502L, p.replies.poll(3, TimeUnit.SECONDS))
            assertEquals(1, f.command().starts)
            assertEquals(1, p.context.registrations.size)
        }
    }

    @Test fun ineligibleEndedAndClosedSessionsCancelDeathRetryAndReleaseRegistrations() {
        for (mode in 0..2) Fixture().use { f ->
            ClientProbe(f.context).use { p ->
                p.attach(8, true)
                p.awaitAvailable()
                p.availability.clear()
                f.kill()
                p.awaitUnavailable()
                when (mode) {
                    0 -> p.attach(8, false)
                    1 -> p.attach(null, false)
                    else -> p.close()
                }
                val attempts = onMain { p.context.attempts }
                afterRetryWindow()
                assertEquals(attempts, onMain { p.context.attempts })
                assertEquals(0, onMain { p.context.registrations.size })
                assertEquals(p.context.attempts, p.context.unbinds)
                assertFalse(onMain { p.client.available })
            }
        }
    }

    @Test fun obsoleteConnectionEventsCannotReviveAnEndedClient() = Fixture().use { f ->
        ClientProbe(f.context).use { p ->
            p.attach(9, true)
            p.awaitAvailable()
            val old = onMain { p.context.connections.single() }
            val oldBinder = f.rawBinder
            p.close()
            onMain {
                old.onServiceConnected(f.component, oldBinder)
                old.onServiceDisconnected(f.component)
                old.onBindingDied(f.component)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) old.onNullBinding(f.component)
            }
            afterRetryWindow()
            assertFalse(onMain { p.client.available })
            assertEquals(1, p.context.attempts)
            assertEquals(1, p.context.unbinds)
            assertTrue(p.context.registrations.isEmpty())
        }
    }

    @Test fun aRealReplyEvaluatedAfterMainThreadCancellationIsIgnored() = Fixture().use { f ->
        ClientProbe(f.context).use { p ->
            p.attach(10, true)
            p.awaitAvailable()
            val base = f.command()
            p.revisionReads.clear()
            // Hold main until cancellation; idle unload follows the worker's Binder dispatch,
            // whereas engine completion alone can precede server-side callback suppression.
            onMain {
                p.client.score(input(601, 10))
                f.await { it.unloadedCompletions == base.completions + 1 }
                p.client.cancel()
            }
            // Only 601 is outstanding: require its actual main-thread callback evaluation.
            // A missing callback must fail, and 602 must not replace 601's token first.
            val evaluatedRevision = checkNotNull(p.revisionReads.poll(3, TimeUnit.SECONDS)) {
                "601 callback was not evaluated after cancellation"
            }
            assertEquals(1L, evaluatedRevision)
            onMain { assertTrue(p.replies.isEmpty()) }
            p.score(602)
            assertEquals(602L, p.replies.poll(3, TimeUnit.SECONDS))
            assertTrue(p.replies.isEmpty())
            p.revisionReads.clear()
            p.revision.set(2)
            p.score(603) // request revision 1 is stale against the live editor revision 2
            f.await { it.lastId == 603L && it.active == 0 }
            assertEquals(2L, p.revisionReads.poll(3, TimeUnit.SECONDS))
            onMain { Unit }
            assertTrue(p.replies.isEmpty())
        }
    }

    @Test fun ownerCanCertifyOnePostSpaceTokenWithoutAcceptingOtherOldRevisionReplies() = Fixture().use { f ->
        ClientProbe(f.context).use { p ->
            p.attach(10, true); p.awaitAvailable()
            p.revision.set(2)
            onMain { p.retainedSpaceToken = input(604, 10).token }
            p.score(604)
            assertEquals(604L, p.replies.poll(3, TimeUnit.SECONDS))
            p.revisionReads.clear()
            p.score(605)
            f.await { it.lastId == 605L && it.active == 0 }
            assertEquals(2L, p.revisionReads.poll(3, TimeUnit.SECONDS))
            onMain { Unit }
            assertTrue(p.replies.isEmpty())
        }
    }

    private class Fixture : AutoCloseable {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val component = ComponentName(context, LifecycleModelInferenceService::class.java)
        private var controlBinding = RealBinding(context, Intent().setComponent(component)
            .setAction(LifecycleModelInferenceService.CONTROL_ACTION))
        private var scoringBinding = RealBinding(context, Intent().setComponent(component))
        val rawBinder get() = scoringBinding.binder()
        val service: IModelScoringService get() = IModelScoringService.Stub.asInterface(rawBinder)
        val replies = LinkedBlockingQueue<Long>()
        val codes = LinkedBlockingQueue<Int>()
        private val callback = object : IModelScoringCallback.Stub() {
            override fun onResult(reply: ScoreReplyParcel?) { reply?.value?.let { codes.add(it.code); replies.add(checkedId(it)) } }
        }
        private var killed = false
        init { command(LifecycleModelInferenceService.RELEASE); await { it.active == 0 } }
        fun score(id: Long) = service.score(ScoreRequestParcel(input(id)), callback)
        fun rebindScoring() {
            scoringBinding.close()
            assertHealthy(command(LifecycleModelInferenceService.AWAIT_SCORING_UNBOUND))
            scoringBinding = RealBinding(context, Intent().setComponent(component))
            scoringBinding.binder()
            assertHealthy(command(LifecycleModelInferenceService.AWAIT_SCORING_BOUND))
        }
        fun command(operation: Int = LifecycleModelInferenceService.SNAPSHOT): Snapshot {
            val result = LinkedBlockingQueue<Snapshot>(1)
            ILifecycleControl.Stub.asInterface(controlBinding.binder()).command(operation,
                object : ILifecycleSnapshot.Stub() {
                    override fun onSnapshot(processId: Int, uid: Int, starts: Int, previousId: Long,
                        lastId: Long, active: Int, peakActive: Int, cancels: Int,
                        cancelledCompletions: Int, completions: Int, unloads: Int,
                        unloadedCompletions: Int, orderViolations: Int, timeouts: Int) {
                        result.offer(Snapshot(processId, uid, starts, previousId, lastId, active,
                            peakActive, cancels, cancelledCompletions, completions, unloads,
                            unloadedCompletions, orderViolations, timeouts))
                    }
                })
            return checkNotNull(result.poll(3, TimeUnit.SECONDS)) { "control callback timeout" }
        }
        fun await(predicate: (Snapshot) -> Boolean): Snapshot {
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(4)
            do {
                val result = command()
                assertHealthy(result)
                if (predicate(result)) return result
                // Each iteration is a real Binder roundtrip; no keystroke/timing sleeps.
            } while (System.nanoTime() < deadline)
            error("remote numeric state did not reach expected condition")
        }
        fun assertHealthy(snapshot: Snapshot) {
            assertEquals(0, snapshot.orderViolations)
            assertEquals(0, snapshot.timeouts)
            assertTrue(snapshot.peakActive <= 1)
        }
        fun kill() {
            val death = CountDownLatch(1)
            val binder = controlBinding.binder()
            binder.linkToDeath({ death.countDown() }, 0)
            ILifecycleControl.Stub.asInterface(binder).command(LifecycleModelInferenceService.KILL_PROCESS, null)
            assertTrue("remote Binder must die", death.await(3, TimeUnit.SECONDS))
            killed = true
        }
        fun reconnectControl() {
            controlBinding.close()
            controlBinding = RealBinding(context, Intent().setComponent(component)
                .setAction(LifecycleModelInferenceService.CONTROL_ACTION))
            controlBinding.binder()
            killed = false
        }
        override fun close() {
            try {
                if (!killed) {
                    command(LifecycleModelInferenceService.RELEASE)
                    command(LifecycleModelInferenceService.INVALIDATE)
                    await { it.active == 0 }
                }
            } finally { scoringBinding.close(); controlBinding.close() }
        }
    }

    private class RealBinding(private val context: Context, intent: Intent) : AutoCloseable {
        private val ready = LinkedBlockingQueue<IBinder>(1)
        private var endpoint: IBinder? = null
        private var closed = false
        private var binds = 0
        private var unbinds = 0
        private val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) { ready.offer(binder) }
            override fun onServiceDisconnected(name: ComponentName) = Unit
        }
        init {
            val bound = onMain { binds++; context.bindService(intent, connection, Context.BIND_AUTO_CREATE) }
            if (!bound) close()
            check(bound)
        }
        fun binder(): IBinder = endpoint ?: checkNotNull(ready.poll(4, TimeUnit.SECONDS)) {
            "real service binding timeout"
        }.also { endpoint = it }
        override fun close() {
            if (!closed) {
                closed = true
                onMain { context.unbindService(connection); unbinds++ }
            }
            assertEquals(binds, unbinds)
        }
    }

    private class RedirectingContext(base: Context) : ContextWrapper(base) {
        val registrations = Collections.newSetFromMap(IdentityHashMap<ServiceConnection, Boolean>())
        val connections = mutableListOf<ServiceConnection>()
        var attempts = 0
        var unbinds = 0
        override fun getApplicationContext(): Context = this
        override fun bindService(intent: Intent, connection: ServiceConnection, flags: Int): Boolean {
            check(intent.component?.className == ModelInferenceService::class.java.name)
            attempts++; connections += connection; check(registrations.add(connection))
            return baseContext.bindService(Intent(intent).setComponent(
                ComponentName(baseContext, LifecycleModelInferenceService::class.java)), connection, flags)
        }
        override fun unbindService(connection: ServiceConnection) {
            check(registrations.remove(connection)); unbinds++
            baseContext.unbindService(connection)
        }
    }

    private class ClientProbe(base: Context) : AutoCloseable {
        val context = RedirectingContext(base)
        val replies = LinkedBlockingQueue<Long>()
        val availability = LinkedBlockingQueue<Boolean>()
        val revision = AtomicLong(1)
        val revisionReads = LinkedBlockingQueue<Long>()
        var retainedSpaceToken: ScoringToken? = null // Main owner only; no payload.
        private var session = 1L
        val client = onMain { BoundModelScoringClient(context, object : ModelScoringListener {
            override fun currentCompositionRevision(): Long = revision.get().also { revisionReads.add(it) }
            override fun isCurrentRequest(token: ScoringToken): Boolean =
                token.revision == currentCompositionRevision() || token == retainedSpaceToken
            override fun onReply(reply: ScoringReply) { replies.add(checkedId(reply)) }
            override fun onAvailabilityChanged(available: Boolean) { availability.add(available) }
        }) }
        fun attach(id: Long?, eligible: Boolean) { session = id ?: 1; onMain { client.attachSession(id, eligible) } }
        fun score(id: Long) = onMain { client.score(input(id, session)) }
        fun awaitAvailable() = awaitAvailability(true)
        fun awaitUnavailable() = awaitAvailability(false)
        private fun awaitAvailability(expected: Boolean) {
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
            while (System.nanoTime() < deadline) {
                val next = availability.poll(maxOf(1, deadline - System.nanoTime()), TimeUnit.NANOSECONDS)
                if (next == expected) return
            }
            error("client availability callback timeout")
        }
        override fun close() {
            onMain { client.close() }
            assertTrue(context.registrations.isEmpty())
            assertEquals(context.attempts, context.unbinds)
        }
    }

    private data class Snapshot(val processId: Int, val uid: Int, val starts: Int,
        val previousId: Long, val lastId: Long, val active: Int, val peakActive: Int,
        val cancels: Int, val cancelledCompletions: Int, val completions: Int,
        val unloads: Int, val unloadedCompletions: Int, val orderViolations: Int, val timeouts: Int)

    companion object {
        private fun checkedId(reply: ScoringReply): Long =
            if (reply.code == 0 && reply.scores.size == 1 && reply.scores[0].candidateId == 11 &&
                reply.scores[0].sumLogProbability == -1.0 && reply.scores[0].tokenCount == 1)
                reply.token.requestId else -reply.token.requestId
        private fun input(id: Long, session: Long = 1) =
            ScoringInput(ScoringToken(session, 1, id, listOf(11)), "fixture", listOf(" value"))
        private fun <T> onMain(block: () -> T): T {
            val task = FutureTask(Callable(block))
            InstrumentationRegistry.getInstrumentation().runOnMainSync(task)
            return task.get(6, TimeUnit.SECONDS)
        }
        private fun afterRetryWindow() {
            val done = CountDownLatch(1)
            Handler(Looper.getMainLooper()).postDelayed({ done.countDown() }, 1_250)
            assertTrue(done.await(3, TimeUnit.SECONDS))
        }
    }
}
