package io.github.mesteriis.rune.keyboard.intelligence.client

import android.content.ComponentName
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringCallback
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreRequestParcel
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Real main Looper/Handler with controlled Context binding failures; not a remote Binder test. */
class BoundModelScoringClientInstrumentedTest {
    @Test fun repeatedFalseBindsReleaseEveryConnectionAndStopRetryWhenIneligible() = failures(false)
    @Test fun repeatedSecurityExceptionsReleaseEveryConnectionAndStopRetryWhenIneligible() = failures(true)

    private fun failures(throwsSecurityException: Boolean) {
        val base = ApplicationProvider.getApplicationContext<Context>()
        val context = FailingContext(base, throwsSecurityException)
        val listener = object : ModelScoringListener {
            override fun currentCompositionRevision() = 0L
            override fun onReply(reply: ScoringReply) = throw AssertionError("unexpected result")
            override fun onAvailabilityChanged(available: Boolean) { assertFalse(available) }
        }
        val client = onMain { BoundModelScoringClient(context, listener).also { it.attachSession(1, true) } }
        try {
            assertTrue("three attempts did not release their connections", context.cleaned.await(5, TimeUnit.SECONDS))
            onMain {
                client.attachSession(1, false)
                context.ended = true
                assertEquals(3, context.binds)
                assertEquals(context.binds, context.unbinds)
                assertTrue(context.registrations.isEmpty())
                assertFalse(client.available)
                val name = ComponentName(base.packageName, "fixture")
                val lateEndpoint = object : IModelScoringService.Stub() {
                    override fun score(request: ScoreRequestParcel?, callback: IModelScoringCallback?) = Unit
                    override fun cancel(sessionId: Long, requestId: Long) = Unit
                }
                context.attempts.forEach { previous ->
                    previous.onServiceConnected(name, lateEndpoint)
                    previous.onBindingDied(name)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) previous.onNullBinding(name)
                }
            }
            assertFalse("retry survived eligibility end", context.unexpectedBind.await(1500, TimeUnit.MILLISECONDS))
            onMain {
                assertEquals(3, context.binds)
                assertTrue(context.registrations.isEmpty())
                assertFalse(client.available)
            }
        } finally { onMain { client.close() } }
    }

    private class FailingContext(base: Context, private val throwsSecurityException: Boolean) : ContextWrapper(base) {
        val cleaned = CountDownLatch(3)
        val unexpectedBind = CountDownLatch(1)
        val registrations = linkedSetOf<ServiceConnection>()
        val attempts = mutableListOf<ServiceConnection>()
        var binds = 0
        var unbinds = 0
        var ended = false
        override fun getApplicationContext(): Context = this
        override fun bindService(intent: Intent, connection: ServiceConnection, flags: Int): Boolean {
            if (ended) unexpectedBind.countDown()
            check(registrations.add(connection))
            attempts += connection
            binds++
            if (throwsSecurityException) throw SecurityException("synthetic binding failure")
            return false
        }
        override fun unbindService(connection: ServiceConnection) {
            check(registrations.remove(connection)) { "wrong or duplicate connection cleanup" }
            unbinds++
            cleaned.countDown()
        }
    }

    private fun <T> onMain(block: () -> T): T {
        val result = AtomicReference<Result<T>>()
        InstrumentationRegistry.getInstrumentation().runOnMainSync { result.set(runCatching(block)) }
        return result.get().getOrThrow()
    }
}
