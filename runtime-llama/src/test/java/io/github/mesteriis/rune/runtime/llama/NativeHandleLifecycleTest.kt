package io.github.mesteriis.rune.runtime.llama

import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class NativeHandleLifecycleTest {
    @Test
    fun admittedNativeCallCompletesBeforeDestroy() {
        val events = Collections.synchronizedList(mutableListOf<String>())
        val callStarted = CountDownLatch(1)
        val releaseCall = CountDownLatch(1)
        val destroyed = AtomicBoolean(false)
        val lifecycle = lifecycle(
            cancel = { events += "cancel" },
            unload = { events += "unload" },
            destroy = { events += "destroy"; destroyed.set(true) },
        )
        val caller = Thread {
            lifecycle.beginOperation {
                callStarted.countDown()
                releaseCall.await(5, TimeUnit.SECONDS)
                events += "call-finished"
            }
        }
        val closer = Thread(lifecycle::close)

        caller.start()
        assertTrue(callStarted.await(5, TimeUnit.SECONDS))
        closer.start()
        assertFalse(destroyed.get())
        releaseCall.countDown()
        caller.join()
        closer.join()

        assertTrue(events.indexOf("call-finished") < events.indexOf("unload"))
        assertTrue(events.indexOf("unload") < events.indexOf("destroy"))
    }

    @Test
    fun closeWaitsForInFlightCancelBeforeDestroy() {
        val events = Collections.synchronizedList(mutableListOf<String>())
        val firstCancelEntered = CountDownLatch(1)
        val releaseFirstCancel = CountDownLatch(1)
        val cancelCalls = AtomicInteger()
        val destroyed = AtomicBoolean(false)
        val lifecycle = lifecycle(
            cancel = {
                val call = cancelCalls.incrementAndGet()
                events += "cancel-$call-enter"
                if (call == 1) {
                    firstCancelEntered.countDown()
                    releaseFirstCancel.await(5, TimeUnit.SECONDS)
                }
                events += "cancel-$call-exit"
            },
            unload = { events += "unload" },
            destroy = { events += "destroy"; destroyed.set(true) },
        )
        val canceller = Thread(lifecycle::cancel)
        val closer = Thread(lifecycle::close)

        canceller.start()
        assertTrue(firstCancelEntered.await(5, TimeUnit.SECONDS))
        closer.start()
        assertFalse(destroyed.get())
        releaseFirstCancel.countDown()
        canceller.join()
        closer.join()

        assertTrue(events.indexOf("cancel-1-exit") < events.indexOf("unload"))
        assertTrue(events.indexOf("unload") < events.indexOf("destroy"))
    }

    @Test
    fun cancelAfterAdmissionBeforeExecutorStartSkipsNativeOperation() {
        val executor = ThreadPoolExecutor(
            1,
            1,
            0,
            TimeUnit.MILLISECONDS,
            LinkedBlockingQueue(),
        )
        val blockerStarted = CountDownLatch(1)
        val releaseBlocker = CountDownLatch(1)
        executor.execute {
            blockerStarted.countDown()
            releaseBlocker.await(5, TimeUnit.SECONDS)
        }
        assertTrue(blockerStarted.await(5, TimeUnit.SECONDS))
        val resets = AtomicInteger()
        val nativeCalls = AtomicInteger()
        val outcome = AtomicReference<NativeCallResult<Int>>()
        val lifecycle = lifecycle(
            executor = executor,
            resetCancellation = { resets.incrementAndGet() },
        )
        val caller = Thread {
            outcome.set(lifecycle.beginOperation { nativeCalls.incrementAndGet() })
        }

        caller.start()
        assertTrue(awaitCondition { executor.queue.isNotEmpty() })
        lifecycle.cancel()
        releaseBlocker.countDown()
        caller.join(5_000)

        assertFalse(caller.isAlive)
        assertSame(NativeCallResult.Cancelled, outcome.get())
        assertEquals(0, resets.get())
        assertEquals(0, nativeCalls.get())
        lifecycle.close()
    }

    @Test
    fun cancelBetweenLoadAndSelfTestRemainsStickyUntilNextLoad() {
        val resets = AtomicInteger()
        val selfTests = AtomicInteger()
        val retryLoads = AtomicInteger()
        val lifecycle = lifecycle(resetCancellation = { resets.incrementAndGet() })

        assertEquals(
            NativeCallResult.Completed("loaded"),
            lifecycle.beginOperation { "loaded" },
        )
        lifecycle.cancel()

        val cancelledSelfTest = lifecycle.continueOperation { selfTests.incrementAndGet() }
        val retryLoad = lifecycle.beginOperation { retryLoads.incrementAndGet() }

        assertSame(NativeCallResult.Cancelled, cancelledSelfTest)
        assertEquals(NativeCallResult.Completed(1), retryLoad)
        assertEquals(0, selfTests.get())
        assertEquals(1, retryLoads.get())
        assertEquals(2, resets.get())
        lifecycle.close()
    }

    @Test
    fun callsAfterCloseNeverReachNativeHandle() {
        val calls = AtomicInteger()
        val cancels = AtomicInteger()
        val lifecycle = lifecycle(cancel = { cancels.incrementAndGet() })

        lifecycle.close()
        val cancelsAtClose = cancels.get()
        val result = lifecycle.beginOperation { calls.incrementAndGet() }
        lifecycle.cancel()

        assertSame(NativeCallResult.Unavailable, result)
        assertEquals(0, calls.get())
        assertEquals(cancelsAtClose, cancels.get())
    }

    private fun lifecycle(
        executor: java.util.concurrent.ExecutorService = Executors.newSingleThreadExecutor(),
        resetCancellation: (Long) -> Unit = {},
        cancel: (Long) -> Unit = {},
        unload: (Long) -> Unit = {},
        destroy: (Long) -> Unit = {},
    ) = NativeHandleLifecycle(
        executor = executor,
        initialHandle = 42,
        resetCancellationNative = resetCancellation,
        cancelNative = cancel,
        unloadNative = unload,
        destroyNative = destroy,
    )

    private fun awaitCondition(condition: () -> Boolean): Boolean {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
        while (System.nanoTime() < deadline) {
            if (condition()) return true
            Thread.yield()
        }
        return condition()
    }
}
