package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Test

class ModelPreparationWorkerTest {
    @Test fun bindingPreparesOnceAndOnlyFirstScoreSharesItsChargedAdmission() = Fixture().use { f ->
        f.worker.onBind(); f.engine.entered.awaitDone()
        f.clock.cpu = 600 // More than the 500 ms admission margin; never refund this load cost.
        f.finishPreparation()
        f.worker.onBind()
        f.submit(1).awaitDone()
        assertEquals(ScoringCode.OK, f.replies.take().code)
        assertEquals(111_000L, f.owner.account().creditUnits)
        f.submit(2).awaitDone()
        assertEquals(ScoringCode.UNAVAILABLE, f.replies.take().code)
        assertEquals(1, f.engine.preparations.get()); assertEquals(1, f.engine.scores.get())
    }

    @Test fun cancelledAndReplacedWordsReleaseTheirPayloadWhileOnePreparationContinues() = Fixture().use { f ->
        val first = f.submit(1); f.engine.entered.awaitDone()
        f.worker.cancel(1, 1); first.awaitDone()
        val second = f.submit(2); val third = f.submit(3); second.awaitDone()
        assertFalse(f.engine.flag!!.get()); assertEquals(0, f.engine.cancels.get())
        assertEquals(0, f.engine.scores.get())
        f.engine.release.countDown(); third.awaitDone()
        assertEquals(3L, f.replies.take().token.requestId)
        assertTrue(f.replies.isEmpty()); assertEquals(1, f.engine.preparations.get())
        assertEquals(3, f.finished.get())
    }

    @Test fun unbindAndCloseCancelPreparationWithoutWaitingForItsReturn() {
        for (close in listOf(false, true)) Fixture().use { f ->
            f.worker.onBind(); f.engine.entered.awaitDone()
            val pending = f.submit(1)
            if (close) f.worker.close() else f.worker.onUnbind()
            pending.awaitDone()
            assertTrue(f.engine.flag!!.get()); assertEquals(1L, f.engine.release.count)
            assertEquals(1, f.engine.cancels.get()); assertEquals(0, f.engine.orderViolations.get())
            f.engine.release.countDown()
            if (close) f.scheduler.closed.awaitDone() else f.engine.unloaded.awaitDone()
            assertEquals(0, f.engine.scores.get()); assertTrue(f.replies.isEmpty())
        }
    }

    @Test fun pressureClockFaultCpuDebtAndWallLimitAlsoStopPayloadFreePreparation() {
        for (reason in 0..3) Fixture().use { f ->
            f.worker.onBind(); f.engine.entered.awaitDone()
            when (reason) {
                0 -> f.worker.suspendForMemoryPressure()
                1 -> { f.clock.fail = true; f.scheduler.tick() }
                2 -> { f.clock.cpu = 8001; f.scheduler.tick() }
                else -> { f.clock.elapsed = 3000; f.scheduler.tick() }
            }
            assertTrue(f.engine.flag!!.get()); assertEquals(1, f.engine.cancels.get())
            assertEquals(0, f.engine.orderViolations.get())
            f.engine.release.countDown()
        }
    }

    @Test fun lateCancelledPreparationCannotRejectAWordSubmittedAfterRebind() = Fixture().use { f ->
        f.worker.onBind(); f.engine.entered.awaitDone()
        val old = f.submit(1)
        f.worker.onUnbind(); old.awaitDone()
        f.worker.onBind()
        val fresh = f.submit(2)
        // The old load returns only after a word from the next binding is queued.
        f.engine.release.countDown(); fresh.awaitDone()
        val reply = f.replies.poll(3, TimeUnit.SECONDS)
        assertNotNull(reply)
        assertEquals(2L, reply!!.token.requestId)
        assertEquals(ScoringCode.OK, reply.code)
        assertEquals(2, f.engine.preparations.get())
        assertEquals(1, f.engine.scores.get())
        assertTrue(f.replies.isEmpty())
    }

    @Test fun firstScoreDoesNotRestartTheThreeSecondPreparationDeadline() = Fixture().use { f ->
        f.worker.onBind(); f.engine.entered.awaitDone()
        f.clock.elapsed = 2000; f.clock.cpu = 600
        f.finishPreparation(); f.engine.blockScore = true
        val done = f.submit(1); f.engine.scoreEntered.awaitDone()
        f.clock.elapsed = 2999; f.scheduler.tick(); assertFalse(f.engine.flag!!.get())
        f.clock.elapsed = 3000; f.scheduler.tick(); assertTrue(f.engine.flag!!.get())
        f.engine.scoreRelease.countDown(); done.awaitDone()
        assertTrue(f.replies.isEmpty()); assertEquals(1, f.engine.cancels.get())
    }

    @Test fun expiredPreparationAdmissionCannotBypassTheNormalCreditThreshold() = Fixture().use { f ->
        f.worker.onBind(); f.engine.entered.awaitDone(); f.clock.cpu = 2000
        f.finishPreparation(); f.clock.elapsed = 3000
        f.submit(1).awaitDone()
        assertEquals(ScoringCode.UNAVAILABLE, f.replies.take().code)
        assertEquals(0, f.engine.scores.get())
    }

    @Test fun preparedWeightsStillUnloadAfterIdleWithoutAWordRequest() = Fixture(idleMillis = 1000).use { f ->
        f.worker.onBind(); f.engine.entered.awaitDone(); f.finishPreparation()
        f.clock.elapsed = 1000; f.clock.cpu = 2000
        // Let the existing idle wait expire, without submitting any word or resetting its age.
        f.engine.unloaded.awaitDone()
        assertEquals(1, f.engine.preparations.get()); assertEquals(0, f.engine.scores.get())
    }

    @Test fun declinedPreparationNeverGrantsAResidualCreditAdmission() = Fixture().use { f ->
        f.engine.failureCode = ScoringCode.UNAVAILABLE
        f.worker.onBind(); f.engine.entered.awaitDone(); f.clock.cpu = 600
        f.finishPreparation(); f.submit(1).awaitDone()
        assertEquals(ScoringCode.UNAVAILABLE, f.replies.take().code)
        assertEquals(0, f.engine.scores.get())
    }

    @Test fun failedPreparationPreservesTheErrorAndDoesNotRetryTheQueuedWord() = Fixture().use { f ->
        f.engine.failureCode = ScoringCode.NO_MODEL
        val done = f.submit(1); f.engine.entered.awaitDone()
        f.engine.release.countDown(); done.awaitDone(); f.engine.unloaded.awaitDone()
        assertEquals(ScoringCode.NO_MODEL, f.replies.take().code)
        assertEquals(1, f.engine.preparations.get()); assertEquals(0, f.engine.scores.get())
        assertEquals(1, f.finished.get()); assertTrue(f.replies.isEmpty())
        f.engine.failureCode = null
        f.submit(2).awaitDone()
        assertEquals(ScoringCode.OK, f.replies.take().code)
        assertEquals(2, f.engine.preparations.get()); assertEquals(1, f.engine.scores.get())
    }

    private class Scheduler : ModelDutyScheduler {
        @Volatile var task: Runnable? = null
        val retired = LinkedBlockingQueue<Unit>()
        val closed = CountDownLatch(1)
        override fun start(task: Runnable) { check(this.task == null); this.task = task }
        override fun stop() { task = null; retired.add(Unit) }
        override fun close() { stop(); closed.countDown() }
        fun tick() { task?.run() }
    }
    private class Engine : ScoringEngine {
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        val scoreEntered = CountDownLatch(1); val scoreRelease = CountDownLatch(1)
        val unloaded = CountDownLatch(1)
        val preparations = AtomicInteger(); val scores = AtomicInteger(); val cancels = AtomicInteger()
        val orderViolations = AtomicInteger()
        @Volatile var flag: AtomicBoolean? = null
        @Volatile var failureCode: Int? = null
        @Volatile var blockScore = false
        override fun prepare(cancelled: AtomicBoolean): ModelPreparation {
            flag = cancelled; preparations.incrementAndGet(); entered.countDown(); release.awaitDone()
            return if (cancelled.get()) ModelPreparation.Failure(ScoringCode.CANCELLED)
                else failureCode?.let(ModelPreparation::Failure) ?: ModelPreparation.Ready
        }
        override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
            flag = cancelled; scores.incrementAndGet(); scoreEntered.countDown()
            if (blockScore) scoreRelease.awaitDone()
            return ScoringReply(request.token, ScoringCode.OK, 0, listOf(NumericScore(0, -1.0, 1)))
        }
        override fun cancel() { if (flag?.get() != true) orderViolations.incrementAndGet(); cancels.incrementAndGet() }
        override fun unload() { unloaded.countDown() }
        override fun close() = unload()
    }
    private class Fixture(idleMillis: Long = 60_000) : AutoCloseable {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val engine = Engine(); val scheduler = Scheduler()
        val worker = LatestScoringWorker(engine, idleMillis, owner, scheduler)
        val replies = LinkedBlockingQueue<ScoringReply>(); val finished = AtomicInteger()
        fun submit(id: Long) = CountDownLatch(1).also { done ->
            worker.submit(ScoringInput(ScoringToken(1, 1, id, listOf(0)), "public", listOf(" fixture")),
                replies::add, { finished.incrementAndGet(); done.countDown() })
        }
        fun finishPreparation() {
            engine.release.countDown()
            assertNotNull(scheduler.retired.poll(3, TimeUnit.SECONDS))
            worker.cancel(1, Long.MAX_VALUE) // Wait for the numeric retirement tail under the monitor.
        }
        override fun close() {
            worker.close(); engine.release.countDown(); engine.scoreRelease.countDown(); scheduler.closed.awaitDone()
        }
    }
    companion object {
        private fun CountDownLatch.awaitDone() { assertTrue("bounded preparation fixture timeout", await(3, TimeUnit.SECONDS)) }
    }
}
