package io.github.mesteriis.rune.keyboard.intelligence.client

import android.content.ComponentName
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.RemoteException
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringCallback
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService
import io.github.mesteriis.rune.keyboard.intelligence.ipc.NumericScore
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreReplyParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreRequestParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.*
import org.junit.Test

/** Actual client, real main Handler for results, controlled retry time and Context registration. */
class ModelDemandClientInstrumentedTest {
    @Test fun sameAttachPreservesReplyAndRequestSequence() = fixture { f ->
        onMain {
            f.attach(); f.connect(); f.client.score(input(5))
            repeat(3) { f.attach() }
            assertEquals(1, f.context.attempts.size)
            assertTrue(f.endpoint.cancelled.isEmpty())
            f.endpoint.reply(0)
        }
        onMain {
            assertEquals(listOf(5L), f.replies)
            f.client.score(input(5)); f.client.score(input(4)); f.client.score(input(6))
            assertEquals(listOf(5L, 6L), f.endpoint.tokens.map { it.requestId })
            assertEquals(listOf(true), f.availability)
        }
    }

    @Test fun offOnPreservesWatermarkAndRetiredCallbackCannotDeliver() = fixture { f ->
        onMain {
            f.attach(); f.connect(); f.client.score(input(5))
            val old = f.context.attempts.single()
            f.client.attachSession(1, false); f.attach(); f.connect()
            f.client.score(input(5)); f.client.score(input(6))
            f.endpoint.reply(0)
            old.onServiceDisconnected(f.name); old.onBindingDied(f.name)
            if (Build.VERSION.SDK_INT >= 28) old.onNullBinding(f.name)
            old.onServiceConnected(f.name, Endpoint())
        }
        onMain {
            assertTrue(f.replies.isEmpty()); assertTrue(f.client.available)
            assertEquals(listOf(5L, 6L), f.endpoint.tokens.map { it.requestId })
            assertEquals(listOf(5L), f.endpoint.cancelled)
            f.endpoint.reply(1)
        }
        onMain { assertEquals(listOf(6L), f.replies) }
    }

    @Test fun falseBindsExhaustExactlyTwoRetriesWhileDemandRemainsTrue() = failedBinds(false)
    @Test fun securityFailuresExhaustExactlyTwoRetriesWhileDemandRemainsTrue() = failedBinds(true)

    private fun failedBinds(security: Boolean) = fixture { f -> onMain {
        f.context.bound = false; f.context.security = security
        f.attach(); assertEquals(listOf(1000L), f.scheduler.delays)
        repeat(3) { f.attach() }
        f.scheduler.fireNext(); assertEquals(listOf(1000L, 2000L), f.scheduler.delays)
        f.scheduler.fireNext()
        repeat(3) { f.attach() }
        assertEquals(3, f.context.attempts.size)
        assertEquals(3, f.context.unbinds)
        assertTrue(f.context.registrations.isEmpty()); assertTrue(f.scheduler.pending.isEmpty())
        assertTrue(f.availability.isEmpty()); assertFalse(f.client.available)
        f.scheduler.history.forEach { it.run() } // obsolete tasks must not mint attempts
        assertEquals(3, f.context.attempts.size)
    } }

    @Test fun successfulReconnectsDoNotReplenishCreditOrReplayRequests() = fixture { f -> onMain {
        f.attach(); f.connect(); f.client.score(input(1))
        f.disconnect(); f.scheduler.fireNext(); f.connect()
        assertEquals(1, f.endpoint.tokens.size)
        f.attach(); f.client.score(input(2, revision = 2)); f.disconnect()
        f.scheduler.fireNext(); f.connect(); f.disconnect()
        assertEquals(3, f.context.attempts.size)
        assertEquals(listOf(1000L, 2000L), f.scheduler.delays)
        assertTrue(f.scheduler.pending.isEmpty())
        assertEquals(listOf(true, false, true, false, true, false), f.availability)
        f.client.attachSession(1, false); f.attach() // a genuine demand edge grants a new epoch
        assertEquals(4, f.context.attempts.size)
    } }

    @Test fun disableAndTerminalCloseRemoveTimersAndRejectCapturedTasks() {
        for (close in listOf(false, true)) fixture { f -> onMain {
            f.context.bound = false; f.attach()
            val stale = f.scheduler.pending.single()
            if (close) { f.client.close(); f.client.close(); f.attach() }
            else f.client.attachSession(1, false)
            assertTrue(f.scheduler.pending.isEmpty())
            stale.run()
            assertEquals(1, f.context.attempts.size)
            assertEquals(1, f.context.unbinds)
            assertFalse(f.client.available)
        } }
    }

    @Test fun oldTimerCannotEraseNewPendingRetryAndOldConnectionCannotDisconnectIt() = fixture { f -> onMain {
        f.context.bound = false; f.attach()
        val stale = f.scheduler.pending.single()
        val old = f.context.attempts.single()
        f.client.attachSession(2, true)
        val current = f.scheduler.pending.single()
        stale.run(); old.onServiceDisconnected(f.name); old.onBindingDied(f.name)
        old.onServiceConnected(f.name, f.endpoint)
        assertSame(current, f.scheduler.pending.single())
        f.scheduler.fireNext()
        assertEquals(3, f.context.attempts.size)
        assertEquals(listOf(1000L, 1000L, 2000L), f.scheduler.delays)
    } }

    @Test fun normalizedNoDemandNeverBindsAndConsumerDomainsAreIndependent() = fixture { f -> onMain {
        for (ready in ModelReadinessHint.entries) {
            f.client.attachSession(ModelDemand.derive(1, true, true, true, ready))
            f.client.attachSession(ModelDemand.derive(1, true, true, true, ready,
                ModelConsumerDemand.UNIMPLEMENTED, ModelConsumerDemand.UNIMPLEMENTED))
        }
        f.client.attachSession(ModelDemand.derive(0, true, true, true, ModelReadinessHint.READY,
            ModelConsumerDemand.ENABLED_IMPLEMENTED))
        assertTrue(f.context.attempts.isEmpty())
        f.client.attachSession(ModelDemand.derive(1, true, true, true, ModelReadinessHint.READY,
            contextual = ModelConsumerDemand.ENABLED_IMPLEMENTED))
        assertEquals(1, f.context.attempts.size)
        assertFalse(f.client.available) // demand/Ready is not a connected transport
    } }

    @Test fun newSessionCancelsOldRequestAndGenerationRejectsRecycledTokenCallback() = fixture { f ->
        onMain {
            f.attach(); f.connect(); f.client.score(input(1))
            f.client.attachSession(2, true); f.connect()
            assertEquals(listOf(1L), f.endpoint.cancelled)
            assertEquals(1, f.endpoint.tokens.size) // no reconnect replay
            f.client.attachSession(1, true); f.connect(); f.client.score(input(1))
            assertEquals(f.endpoint.tokens[0], f.endpoint.tokens[1]) // adversarial identity recycling
            f.endpoint.reply(0)
        }
        onMain {
            assertTrue(f.replies.isEmpty())
            f.endpoint.reply(1)
        }
        onMain { assertEquals(listOf(1L), f.replies) }
    }

    @Test fun nullBindingAndDeathDisconnectOnceAndConnectedNotificationsAreTransitions() = fixture { f -> onMain {
        f.attach(); f.connect(); f.connect()
        assertEquals(listOf(true), f.availability)
        val old = f.context.attempts.last()
        // API 26/27 lack the interface method; invoke the actual override through reflection there.
        if (Build.VERSION.SDK_INT >= 28) old.onNullBinding(f.name)
        else old.javaClass.getDeclaredMethod("onNullBinding", ComponentName::class.java).apply {
            isAccessible = true
        }.invoke(old, f.name)
        old.onServiceDisconnected(f.name); old.onBindingDied(f.name)
        assertEquals(listOf(true, false), f.availability)
        assertEquals(1, f.context.unbinds)
        f.scheduler.fireNext(); f.connect()
        f.context.attempts.last().onBindingDied(f.name)
        assertEquals(2, f.context.unbinds)
        assertEquals(listOf(1000L, 2000L), f.scheduler.delays)
    } }

    @Test fun remoteFailureClearsActiveTokenAndDoesNotReplayOnReconnect() = fixture { f -> onMain {
        f.attach(); f.connect(); f.endpoint.remoteFailure = true
        f.client.score(input(1)); assertFalse(f.client.available)
        f.scheduler.fireNext(); f.endpoint.remoteFailure = false; f.connect()
        f.client.score(input(1)); assertTrue(f.endpoint.tokens.isEmpty())
        f.client.score(input(2)); assertEquals(listOf(2L), f.endpoint.tokens.map { it.requestId })
    } }

    private class Scheduler : ModelRetryScheduler {
        val pending = mutableListOf<Runnable>()
        val history = mutableListOf<Runnable>()
        val delays = mutableListOf<Long>()
        override fun postDelayed(task: Runnable, delayMillis: Long) {
            pending += task; history += task; delays += delayMillis
        }
        override fun remove(task: Runnable) { pending.remove(task) }
        fun fireNext() { pending.removeAt(0).run() }
    }
    private class BindingContext(base: Context) : ContextWrapper(base) {
        val attempts = mutableListOf<ServiceConnection>()
        val registrations = linkedSetOf<ServiceConnection>()
        var unbinds = 0
        var bound = true
        var security = false
        override fun getApplicationContext(): Context = this
        override fun bindService(intent: Intent, connection: ServiceConnection, flags: Int): Boolean {
            assertEquals("io.github.mesteriis.rune.keyboard.intelligence.inference.ModelInferenceService",
                intent.component?.className)
            assertEquals(Context.BIND_AUTO_CREATE, flags)
            check(registrations.add(connection)); attempts += connection
            if (security) throw SecurityException()
            return bound
        }
        override fun unbindService(connection: ServiceConnection) {
            check(registrations.remove(connection)) { "duplicate or unknown registration" }; unbinds++
        }
    }
    private class Endpoint : IModelScoringService.Stub() {
        val tokens = mutableListOf<ScoringToken>()
        val callbacks = mutableListOf<IModelScoringCallback>()
        val cancelled = mutableListOf<Long>()
        var remoteFailure = false
        override fun score(request: ScoreRequestParcel?, callback: IModelScoringCallback?) {
            if (remoteFailure) throw RemoteException()
            tokens += checkNotNull(request).value.token; callbacks += checkNotNull(callback)
        }
        override fun cancel(sessionId: Long, requestId: Long) { cancelled += requestId }
        fun reply(index: Int) = callbacks[index].onResult(ScoreReplyParcel(ScoringReply(tokens[index], 0, 1,
            listOf(NumericScore(7, -1.0, 1)))))
    }
    private class Fixture : AutoCloseable {
        val context = BindingContext(ApplicationProvider.getApplicationContext())
        val scheduler = Scheduler()
        val endpoint = Endpoint()
        val name = ComponentName(context.packageName, "fixture")
        val replies = mutableListOf<Long>()
        val availability = mutableListOf<Boolean>()
        val client = BoundModelScoringClient(context, object : ModelScoringListener {
            override fun currentCompositionRevision() = 1L
            override fun onReply(reply: ScoringReply) { replies += reply.token.requestId }
            override fun onAvailabilityChanged(available: Boolean) { availability += available }
        }, scheduler)
        fun attach() = client.attachSession(1, true)
        fun connect() = context.attempts.last().onServiceConnected(name, endpoint)
        fun disconnect() = context.attempts.last().onServiceDisconnected(name)
        override fun close() {
            client.close()
            assertTrue(scheduler.pending.isEmpty()); assertTrue(context.registrations.isEmpty())
            assertEquals(context.attempts.size, context.unbinds)
        }
    }
    private fun fixture(block: (Fixture) -> Unit) {
        val fixture = onMain { Fixture() }
        try { block(fixture) } finally { onMain { fixture.close() } }
    }
    private fun input(id: Long, revision: Long = 1) = ScoringInput(ScoringToken(1, revision, id, listOf(7)),
        "public fixture", listOf(" option"))
    private fun <T> onMain(block: () -> T): T {
        val result = AtomicReference<Result<T>>()
        InstrumentationRegistry.getInstrumentation().runOnMainSync { result.set(runCatching(block)) }
        return result.get().getOrThrow()
    }
}
