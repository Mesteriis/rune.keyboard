package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Test

class ModelDutyWorkerTest {
    @Test fun retiringCloseHoldsLeaseAndChargesDebtBeforeSuccessorCanEnter() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val first = Probe(owner); val second = Probe(owner)
        try {
            first.submit(1).awaitDone(); first.engine.closeRelease = CountDownLatch(1)
            first.worker.close(); first.engine.closeEntered.awaitDone()
            second.submit(2).awaitDone()
            assertEquals(ScoringCode.UNAVAILABLE, second.replies.take().code)
            assertEquals(0, second.engine.starts.get())
            clock.cpu = 10_000
            first.scheduler.tick()
            assertTrue(owner.account().creditUnits < 0)
            assertEquals(0, first.engine.cancels.get()) // cleanup is uncancellable
            first.engine.closeRelease!!.countDown(); first.scheduler.closed.awaitDone()
            second.submit(3).awaitDone()
            assertEquals(ScoringCode.UNAVAILABLE, second.replies.take().code)
            assertEquals(0, second.engine.starts.get()) // no spontaneous retry on lease release
            clock.elapsed = 120_000
            second.submit(4).awaitDone()
            assertEquals(ScoringCode.OK, second.replies.take().code)
            assertEquals(1, second.engine.starts.get())
        } finally { first.close(); second.close() }
    }
    @Test fun warmIdleOwnershipAndExceptionalCloseStillReleaseExactlyOnce() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val first = Probe(owner); val second = Probe(owner)
        try {
            first.submit(1).awaitDone()
            assertNull(first.scheduler.task)
            second.submit(2).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, second.replies.take().code)
            first.engine.failClose = true; first.close()
            second.submit(3).awaitDone(); assertEquals(ScoringCode.OK, second.replies.take().code)
            assertEquals(1, first.engine.closes.get())
        } finally { first.close(); second.close() }
    }
    @Test fun processCpuExhaustionSetsFlagBeforeCancelAndRetiresActiveTimer() = blocked { p, clock ->
        clock.cpu = 8000
        p.scheduler.tick()
        assertTrue(p.engine.flag!!.get()); assertEquals(1, p.engine.cancels.get())
        assertEquals(0, p.engine.orderViolations.get())
        p.engine.release.countDown(); p.done!!.awaitDone()
        assertTrue(p.replies.isEmpty()); assertNull(p.scheduler.task)
        assertEquals(1, p.finished.get())
    }
    @Test fun activeWallDeadlineIsIndependentOfCpuAndHasExactBoundary() = blocked { p, clock ->
        clock.elapsed = 2999; p.scheduler.tick(); assertFalse(p.engine.flag!!.get())
        clock.elapsed = 3000; p.scheduler.tick(); assertTrue(p.engine.flag!!.get())
        p.engine.release.countDown(); p.done!!.awaitDone(); assertTrue(p.replies.isEmpty())
    }
    @Test fun ordinaryCancellationPreservesWarmEngineAndStaleTimerCannotCancelNextRequest() {
        val clock = DutyClock(); Probe(ModelDutyOwner(clock::sample)).use { p ->
            p.engine.block = true; val first = p.submit(1); p.engine.entered.awaitDone()
            val oldTimer = checkNotNull(p.scheduler.task)
            p.worker.cancel(1, 1); p.engine.release.countDown(); first.awaitDone()
            assertEquals(0, p.engine.unloads.get()); assertEquals(0, p.engine.orderViolations.get())
            p.engine.prepareBlock(); val next = p.submit(2); p.engine.entered.awaitDone()
            val cancels = p.engine.cancels.get()
            oldTimer.run()
            assertEquals(cancels, p.engine.cancels.get()); assertFalse(p.engine.flag!!.get())
            p.engine.release.countDown(); next.awaitDone(); assertEquals(2L, p.replies.take().token.requestId)
        }
    }
    @Test fun pendingReplacementDoesNotExtendAgeOfSameRequest() = blocked { p, clock ->
        val oldPending = p.submit(2)
        clock.elapsed = 2500
        val replacement = p.submit(2, revision = 2)
        oldPending.awaitDone()
        clock.elapsed = 3000
        p.engine.release.countDown(); p.done!!.awaitDone(); replacement.awaitDone()
        val denied = p.replies.take()
        assertEquals(2L, denied.token.requestId); assertEquals(ScoringCode.UNAVAILABLE, denied.code)
        assertEquals(1, p.engine.starts.get()); assertEquals(3, p.finished.get())
    }
    @Test fun latestDifferentPendingReplacesPreviousAndGetsItsOwnReceiptTime() = blocked { p, clock ->
        val replaced = p.submit(2)
        clock.elapsed = 2500
        val latest = p.submit(3)
        replaced.awaitDone()
        clock.elapsed = 3001
        p.engine.block = false; p.engine.release.countDown(); p.done!!.awaitDone(); latest.awaitDone()
        assertEquals(3L, p.replies.take().token.requestId)
        assertEquals(2, p.engine.starts.get()); assertEquals(3, p.finished.get())
    }
    @Test fun pressureLatchesBeforeNewSubmissionAndOnlyRealUnbindBindRearms() = blocked { p, _ ->
        p.worker.onBind()
        val pending = p.submit(2)
        p.worker.suspendForMemoryPressure(); pending.awaitDone()
        assertTrue(p.engine.flag!!.get())
        p.submit(3).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
        p.worker.onBind(); p.worker.invalidate()
        p.submit(4).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
        p.engine.block = false; p.engine.release.countDown(); p.done!!.awaitDone()
        p.worker.onUnbind(); p.worker.onBind()
        p.submit(5).awaitDone(); assertEquals(ScoringCode.OK, p.replies.take().code)
        p.worker.suspendForMemoryPressure()
        p.submit(6).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
    }
    @Test fun deniedRequestsNeverEnterEngineOrExtendExistingIdleUnload() {
        val clock = DutyClock(); Probe(ModelDutyOwner(clock::sample), idleMillis = 1000).use { p ->
            p.submit(1).awaitDone(); assertEquals(ScoringCode.OK, p.replies.take().code)
            assertNotNull(p.scheduler.stops.poll(3, TimeUnit.SECONDS)) // score operation retired
            // Finish callback precedes idleAt accounting under the worker monitor. This no-op
            // control roundtrip waits for that tail before advancing the virtual clock.
            p.worker.cancel(1, 1)
            clock.elapsed = 500; clock.cpu = 2000
            p.submit(2).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
            clock.elapsed = 1000
            p.submit(3).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
            p.engine.unloaded.awaitDone()
            assertEquals(1, p.engine.starts.get()); assertEquals(1, p.engine.unloads.get())
            // Engine entry is before the worker's finally; only scheduler.stop proves retirement.
            assertNotNull(p.scheduler.stops.poll(3, TimeUnit.SECONDS))
            assertNull(p.scheduler.task)
        }
    }
    @Test fun unloadEntryPrecedesDutyTimerRetirement() {
        val clock = DutyClock(); Probe(ModelDutyOwner(clock::sample)).use { p ->
            p.submit(1).awaitDone(); assertEquals(ScoringCode.OK, p.replies.take().code)
            assertNotNull(p.scheduler.stops.poll(3, TimeUnit.SECONDS))
            p.engine.unloadRelease = CountDownLatch(1)
            p.worker.invalidate()
            p.engine.unloaded.awaitDone()
            assertNotNull(p.scheduler.task) // Cleanup CPU is still accounted while native unload runs.
            assertTrue(p.scheduler.stops.isEmpty())
            p.engine.unloadRelease!!.countDown()
            assertNotNull(p.scheduler.stops.poll(3, TimeUnit.SECONDS))
            assertNull(p.scheduler.task)
        }
    }
    @Test fun resolverFailureAndCancelledColdWorkChargeWholeProcessCpu() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        Probe(owner).use { p ->
            p.engine.onScore = { clock.cpu += 501; ScoringCode.NO_MODEL }
            p.submit(1).awaitDone(); assertEquals(ScoringCode.NO_MODEL, p.replies.take().code)
            p.submit(2).awaitDone(); assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
            assertEquals(1, p.engine.starts.get()); assertEquals(112_485L, owner.account().creditUnits)
        }
        val coldClock = DutyClock(); val coldOwner = ModelDutyOwner(coldClock::sample)
        Probe(coldOwner).use { p ->
            p.engine.block = true; val done = p.submit(3); p.engine.entered.awaitDone()
            coldClock.cpu = 1000; p.worker.cancel(1, 3)
            p.engine.release.countDown(); done.awaitDone()
            assertEquals(105_000L, coldOwner.account().creditUnits)
            assertTrue(p.replies.isEmpty())
        }
    }
    @Test fun throwingClockCancelsButCleanupStillRunsAndAccountsWithoutRearming() = blocked { p, clock ->
        clock.fail = true; p.scheduler.tick()
        assertTrue(p.engine.flag!!.get())
        p.engine.release.countDown(); p.done!!.awaitDone()
        clock.fail = false; clock.cpu = 9000
        p.close()
        assertEquals(1, p.engine.closes.get())
        assertTrue(p.owner.account().faulted); assertTrue(p.owner.account().creditUnits < 0)
        p.owner.onUnbind(1); p.owner.onBind(1)
        assertFalse(p.owner.admit(p.owner.acquireLease()).admitted)
    }
    @Test fun throwingEngineDeliveryAndFinishedCallbacksDoNotLeakActiveOrPendingWork() {
        val clock = DutyClock(); Probe(ModelDutyOwner(clock::sample)).use { p ->
            p.engine.onScore = { clock.cpu += 1; throw IllegalStateException() }
            val done = CountDownLatch(1); val finishes = AtomicInteger()
            p.worker.submit(input(1), { assertEquals(ScoringCode.INTERNAL, it.code); throw IllegalStateException() }, {
                finishes.incrementAndGet(); done.countDown(); throw IllegalStateException()
            })
            done.awaitDone(); p.engine.onScore = null
            p.submit(2).awaitDone(); assertEquals(ScoringCode.OK, p.replies.take().code)
            assertEquals(1, finishes.get())
        }
    }
    @Test fun finalSampleSuppressesFastOvershootWithoutWaitingForTimer() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        Probe(owner).use { p ->
            p.engine.onScore = { clock.cpu = 8001; ScoringCode.OK }
            p.submit(1).awaitDone()
            assertTrue(p.replies.isEmpty()); assertEquals(-15L, owner.account().creditUnits)
            assertEquals(1, p.engine.cancels.get()); assertEquals(0, p.engine.orderViolations.get())
        }
    }
    @Test fun closeFinishesBothActiveAndPendingExactlyOnceWithoutJoining() = blocked { p, _ ->
        val pending = p.submit(2)
        p.worker.close(); p.worker.close()
        pending.awaitDone()
        assertEquals(1, p.engine.starts.get())
        assertTrue(p.engine.flag!!.get())
        // close returned although the active synthetic engine is still held.
        assertEquals(1L, p.done!!.count)
        p.engine.release.countDown(); p.done!!.awaitDone(); p.scheduler.closed.awaitDone()
        assertEquals(2, p.finished.get()); assertTrue(p.replies.isEmpty())
    }
    @Test fun deniedNewRevisionStillCancelsOldActiveAndDropsOldPending() = blocked { p, clock ->
        val pending = p.submit(2)
        clock.cpu = 501
        p.submit(3).awaitDone(); pending.awaitDone()
        assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
        assertTrue(p.engine.flag!!.get())
        p.engine.release.countDown(); p.done!!.awaitDone()
        assertEquals(1, p.engine.starts.get()); assertEquals(3, p.finished.get())
        assertTrue(p.replies.isEmpty())
    }
    @Test fun pressureIsAlreadyLatchedWhileWaitingForWorkerMonitor() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        Probe(owner).use { p ->
            p.worker.onBind()
            val field = LatestScoringWorker::class.java.getDeclaredField("monitor").apply { isAccessible = true }
            val monitor = checkNotNull(field.get(p.worker))
            val pressureDone = CountDownLatch(1)
            synchronized(monitor) {
                Thread { try { p.worker.suspendForMemoryPressure() } finally { pressureDone.countDown() } }.start()
                val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
                while (!owner.account().suspended && System.nanoTime() < deadline) Thread.yield()
                assertTrue("pressure must latch before acquiring worker monitor", owner.account().suspended)
                p.submit(1).awaitDone() // synchronized monitor is reentrant for this test thread
                assertEquals(ScoringCode.UNAVAILABLE, p.replies.take().code)
                assertEquals(0, p.engine.starts.get())
            }
            pressureDone.awaitDone()
        }
    }
    @Test fun admissionPreservesCompleteInputAndEightCandidates() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val original = ScoringInput(ScoringToken(1, 1, 1, (0..7).toList()), "complete public prefix",
            (0..7).map { " option $it" })
        val scheduler = Scheduler(); val done = CountDownLatch(1)
        val sameInput = AtomicBoolean()
        val received = LinkedBlockingQueue<ScoringReply>()
        val engine = object : ScoringEngine {
            override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
                sameInput.set(original === request)
                return ScoringReply(request.token, ScoringCode.NO_MODEL, 0, emptyList())
            }
            override fun cancel() = Unit
            override fun unload() = Unit
            override fun close() = Unit
        }
        val worker = LatestScoringWorker(engine, 60_000, owner, scheduler)
        try {
            worker.submit(original, received::add, done::countDown); done.awaitDone()
            assertTrue(sameInput.get())
            assertEquals(ScoringCode.NO_MODEL, received.poll(3, TimeUnit.SECONDS)?.code)
        }
        finally { worker.close(); scheduler.closed.awaitDone() }
    }

    private fun blocked(test: (Probe, DutyClock) -> Unit) {
        val clock = DutyClock(); Probe(ModelDutyOwner(clock::sample)).use { p ->
            p.engine.block = true; p.done = p.submit(1); p.engine.entered.awaitDone()
            test(p, clock)
        }
    }
    private class Scheduler : ModelDutyScheduler {
        @Volatile var task: Runnable? = null
        val stops = LinkedBlockingQueue<Unit>()
        val closed = CountDownLatch(1)
        override fun start(task: Runnable) { check(this.task == null); this.task = task }
        override fun stop() { task = null; stops.add(Unit) }
        override fun close() { stop(); closed.countDown() }
        fun tick() { task?.run() }
    }
    private class Engine : ScoringEngine {
        var block = false
        var failClose = false
        var closeRelease: CountDownLatch? = null
        var unloadRelease: CountDownLatch? = null
        var onScore: (() -> Int)? = null
        var entered = CountDownLatch(1)
        var release = CountDownLatch(1)
        val closeEntered = CountDownLatch(1)
        val unloaded = CountDownLatch(1)
        val starts = AtomicInteger(); val closes = AtomicInteger(); val unloads = AtomicInteger()
        val cancels = AtomicInteger(); val orderViolations = AtomicInteger()
        @Volatile var flag: AtomicBoolean? = null
        fun prepareBlock() { block = true; entered = CountDownLatch(1); release = CountDownLatch(1) }
        override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
            starts.incrementAndGet(); flag = cancelled; entered.countDown()
            if (block) release.awaitDone()
            val code = onScore?.invoke() ?: ScoringCode.OK
            return ScoringReply(request.token, code, 0, if (code == ScoringCode.OK)
                request.token.candidateIds.map { NumericScore(it, -1.0, 1) } else emptyList())
        }
        override fun cancel() { if (flag?.get() == false) orderViolations.incrementAndGet(); cancels.incrementAndGet() }
        override fun unload() { unloads.incrementAndGet(); unloaded.countDown(); unloadRelease?.awaitDone() }
        override fun close() {
            closes.incrementAndGet(); closeEntered.countDown(); closeRelease?.awaitDone()
            if (failClose) throw IllegalStateException()
        }
    }
    private class Probe(val owner: ModelDutyOwner, idleMillis: Long = 60_000) : AutoCloseable {
        val scheduler = Scheduler(); val engine = Engine()
        val worker = LatestScoringWorker(engine, idleMillis, owner, scheduler)
        val replies = LinkedBlockingQueue<ScoringReply>()
        val finished = AtomicInteger()
        var done: CountDownLatch? = null
        fun submit(id: Long, revision: Long = 1) = CountDownLatch(1).also { done -> worker.submit(input(id, revision), replies::add, {
            finished.incrementAndGet(); done.countDown()
        }) }
        override fun close() {
            engine.release.countDown(); engine.closeRelease?.countDown(); engine.unloadRelease?.countDown(); worker.close()
            scheduler.closed.awaitDone()
        }
    }
    companion object {
        private fun CountDownLatch.awaitDone() { assertTrue("bounded fixture timeout", await(3, TimeUnit.SECONDS)) }
        private fun input(id: Long, revision: Long = 1) = ScoringInput(ScoringToken(1, revision, id, listOf(1, 2)), "public fixture", listOf(" a", " b"))
    }
}
