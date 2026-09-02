package io.github.mesteriis.rune.keyboard.intelligence.readiness

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.ThreadFactory
import java.util.concurrent.Executor
import java.util.concurrent.atomic.AtomicInteger

class ActiveModelReadinessTest {
    @Test fun inactiveSourceDoesNotCreateWorkerOrProbe() {
        Harness { ModelReadinessHint.READY }.use { h ->
            repeat(10) { h.source.setActive(false) }
            assertNull(h.thread); assertEquals(0, h.calls.get())
            assertEquals(ModelReadinessHint.UNKNOWN, h.source.hint)
        }
    }

    @Test fun repeatedActiveDemandCoalescesAndReadyIsNotPolled() {
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        Harness { entered.countDown(); release.awaitBounded(); ModelReadinessHint.READY }.use { h ->
            h.source.setActive(true); entered.awaitBounded()
            repeat(100) { h.source.setActive(true) }
            assertEquals(1, h.calls.get())
            release.countDown(); h.deliver()
            assertEquals(ModelReadinessHint.READY, h.source.hint)
            repeat(100) { h.source.setActive(true) }
            assertEquals(1, h.calls.get())
            h.source.setActive(false)
            assertEquals(ModelReadinessHint.UNKNOWN, h.source.hint)
            h.source.setActive(true); h.deliver()
            assertEquals(2, h.calls.get())
        }
    }

    @Test fun completionAfterSessionEndCannotRestoreReady() {
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        Harness { cancelled -> entered.countDown(); release.awaitBounded()
            assertTrue(cancelled()); ModelReadinessHint.READY }.use { h ->
            h.source.setActive(true); entered.awaitBounded(); h.source.setActive(false)
            release.countDown(); h.deliver()
            assertEquals(ModelReadinessHint.UNKNOWN, h.source.hint)
            assertEquals(1, h.calls.get())
        }
    }

    @Test fun obsoleteOwnerCallbackCannotOverwriteNextSession() {
        val count = AtomicInteger()
        Harness { if (count.incrementAndGet() == 1) ModelReadinessHint.READY else ModelReadinessHint.MISSING }.use { h ->
            h.source.setActive(true)
            val obsolete = h.take()
            h.source.setActive(false); h.source.setActive(true)
            val current = h.take()
            current.run(); obsolete.run()
            assertEquals(ModelReadinessHint.MISSING, h.source.hint)
        }
    }

    @Test fun unknownOnlyRetriesOnExplicitDemandAndBrokenNeedsNewActiveEdge() {
        for (hint in listOf(ModelReadinessHint.UNKNOWN, ModelReadinessHint.BROKEN, ModelReadinessHint.MISSING)) {
            Harness { hint }.use { h ->
                h.source.setActive(true); h.deliver()
                assertEquals(1, h.calls.get()); assertTrue(h.queue.isEmpty())
                h.source.setActive(true)
                if (hint == ModelReadinessHint.UNKNOWN) { h.deliver(); assertEquals(2, h.calls.get()) }
                else assertEquals(1, h.calls.get())
            }
        }
    }

    @Test fun throwingProbeBecomesBrokenAndCloseDiscardsQueuedResult() {
        Harness { throw IllegalStateException("synthetic") }.use { h ->
            h.source.setActive(true); h.deliver()
            assertEquals(ModelReadinessHint.BROKEN, h.source.hint)
            h.source.setActive(false); h.source.setActive(true)
            val pending = h.take(); h.source.close(); pending.run()
            assertEquals(ModelReadinessHint.UNKNOWN, h.source.hint)
            h.source.setActive(true); assertEquals(2, h.calls.get())
        }
    }

    @Test fun closeDoesNotWaitForBlockedProbeAndCancellationIsVisible() {
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        Harness { cancelled -> entered.countDown(); release.awaitBounded()
            assertTrue(cancelled()); ModelReadinessHint.READY }.use { h ->
            h.source.setActive(true); entered.awaitBounded()
            h.source.close(); release.countDown(); h.deliver()
            assertEquals(ModelReadinessHint.UNKNOWN, h.source.hint)
        }
    }

    private class Harness(probe: (() -> Boolean) -> ModelReadinessHint) : AutoCloseable {
        val calls = AtomicInteger()
        val queue = LinkedBlockingQueue<Runnable>()
        var thread: Thread? = null
        val source = ActiveModelReadiness({ cancelled -> calls.incrementAndGet(); probe(cancelled) },
            Executor { queue.add(it) }, ThreadFactory { task -> Thread(task).also { thread = it } })
        fun take() = checkNotNull(queue.poll(3, TimeUnit.SECONDS)) { "readiness callback absent" }
        fun deliver() { take().run() }
        override fun close() { source.close(); thread?.join(3000); assertFalse(thread?.isAlive == true) }
    }
    companion object {
        private fun CountDownLatch.awaitBounded() { assertTrue(await(3, TimeUnit.SECONDS)) }
    }
}
