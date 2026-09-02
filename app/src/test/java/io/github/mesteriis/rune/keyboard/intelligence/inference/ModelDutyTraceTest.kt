package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/** Virtual-clock execution of the production worker. Protocol and costs are frozen in duty-traces/. */
@RunWith(Parameterized::class)
class ModelDutyTraceTest(private val language: String, private val count: Int,
    private val warmWall: Long, private val warmCpu: Long) {
    @Test fun fixedTypingPressureAndRecoveryTrace() {
        Trace(language, count).use { t ->
            t.submit(1); t.entered(1)
            t.advance(100, 400)
            t.submit(2); val receipt3 = t.clock.sample().elapsedMillis; t.submit(3)
            t.done(2)
            t.advance(25, 100); t.finish(1)
            t.entered(3); t.advance(warmWall, warmCpu); t.finish(3)
            val usable = if (t.clock.sample().elapsedMillis - receipt3 <= 1000) 1 else 0
            t.submit(4); t.done(4)
            assertEquals(ScoringCode.UNAVAILABLE, t.records[4L]!!.reply!!.code)

            t.idle(90_000)
            t.submit(5); t.entered(5); t.submit(6)
            t.advance(3000, 0); t.finish(5); t.done(6)
            assertEquals(ScoringCode.UNAVAILABLE, t.records[6L]!!.reply!!.code)
            assertFalse(t.records[6L]!!.started)

            t.idle(90_000)
            t.submit(7, ScoringCode.LOAD_FAILED); t.entered(7)
            t.advance(360, 355); t.finish(7)
            assertEquals(ScoringCode.LOAD_FAILED, t.records[7L]!!.reply!!.code)
            val afterFailure = t.owner.account().creditUnits
            assertTrue(afterFailure < ModelDutyProfile.CAPACITY_UNITS)
            t.worker.suspendForMemoryPressure(); t.cleanup()
            t.submit(8); t.done(8)
            t.worker.invalidate(); t.cleanup()
            t.submit(9); t.done(9)
            assertEquals(ScoringCode.UNAVAILABLE, t.records[8L]!!.reply!!.code)
            assertEquals(ScoringCode.UNAVAILABLE, t.records[9L]!!.reply!!.code)
            t.worker.onUnbind(); t.cleanup(); t.worker.onBind()
            assertEquals(afterFailure, t.owner.account().creditUnits)
            t.submit(10); t.entered(10); t.advance(warmWall, warmCpu); t.finish(10)

            t.idle(90_000)
            t.submit(11); t.entered(11); t.advance(2000, 8400)
            assertTrue(t.records[11L]!!.flag!!.get())
            t.advance(25, 100); t.finish(11)
            val finalCredit = t.owner.account().creditUnits
            assertTrue(finalCredit < 0)

            val records = t.records.values
            assertEquals(11, records.size)
            records.forEach { assertEquals(1, it.finished.get()) }
            val admitted = records.count { it.started }
            val cancelled = records.count { it.started && it.flag!!.get() }
            val completed = records.count { it.reply?.code == ScoringCode.OK }
            val denied = records.count { it.reply?.code == ScoringCode.UNAVAILABLE }
            val failed = records.count { it.reply?.code == ScoringCode.LOAD_FAILED }
            val replaced = records.count { !it.started && it.reply == null }
            assertEquals(6, admitted); assertEquals(3, cancelled); assertEquals(2, completed)
            assertEquals(4, denied); assertEquals(1, failed); assertEquals(1, replaced)
            assertTrue(records.filter { it.flag?.get() == true }.all { it.reply == null })
            val end = t.clock.sample()
            assertEquals(9355 + 2 * warmCpu, end.processCpuMillis)
            assertEquals(275510 + 2 * warmWall, end.elapsedMillis)
            // Numeric stdout is captured in JUnit XML; never print request/candidate content.
            println("DUTY_TRACE_V1 {\"language\":\"$language\",\"candidates\":$count," +
                "\"submitted\":11,\"admitted\":$admitted,\"denied\":$denied,\"expired\":1," +
                "\"cancelled\":$cancelled,\"completed\":$completed,\"failed\":$failed," +
                "\"replacedPending\":$replaced,\"usableBefore1000msBoundary\":$usable," +
                "\"boundaryProbes\":1,\"simulatedCpuMillis\":${end.processCpuMillis}," +
                "\"simulatedWallMillis\":${end.elapsedMillis},\"finalCreditUnits\":$finalCredit," +
                "\"simulatedExhaustionTailCpuMillis\":100,\"simulatedExhaustionTailWallMillis\":25}")
        }
    }

    private class Clock {
        private var wall = 0L
        private var cpu = 0L
        @Synchronized fun advance(elapsed: Long, spent: Long) { wall += elapsed; cpu += spent }
        @Synchronized fun sample() = ModelDutySample(wall, cpu)
    }
    private class Record(val input: ScoringInput, val code: Int) {
        val release = CountDownLatch(1)
        val done = CountDownLatch(1)
        val finished = AtomicInteger()
        @Volatile var started = false
        @Volatile var flag: AtomicBoolean? = null
        @Volatile var reply: ScoringReply? = null
    }
    private class Checks : ModelDutyScheduler {
        @Volatile var task: Runnable? = null
        val stopped = LinkedBlockingQueue<Boolean>()
        val closed = CountDownLatch(1)
        override fun start(task: Runnable) { check(this.task == null); this.task = task }
        override fun stop() { task = null; stopped.add(true) }
        override fun close() { task = null; closed.countDown() }
    }
    private class Trace(language: String, count: Int) : AutoCloseable {
        val clock = Clock()
        val owner = ModelDutyOwner(clock::sample)
        val records = ConcurrentHashMap<Long, Record>()
        private val checks = Checks()
        private val starts = LinkedBlockingQueue<Long>()
        private val unloads = LinkedBlockingQueue<Boolean>()
        private val candidates = when (language) {
            "EN" -> listOf("cat", "bat", "cut", "cot", "car", "can", "cap", "cab")
            "RU" -> listOf("кот", "кит", "рот", "ком", "код", "ток", "тут", "кат")
            else -> listOf("casa", "caso", "cama", "cara", "pasa", "cosa", "caza", "masa")
        }.take(count)
        private val prefix = when (language) { "EN" -> "The word is "; "RU" -> "Это слово "; else -> "La palabra es " }
        val worker = LatestScoringWorker(object : ScoringEngine {
            override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
                val record = records.getValue(request.token.requestId)
                assertSame(record.input, request)
                assertEquals(candidates, request.continuations)
                assertEquals(candidates.indices.toList(), request.token.candidateIds)
                record.started = true; record.flag = cancelled; starts.add(request.token.requestId)
                record.release.awaitBounded()
                return ScoringReply(request.token, record.code, 0, if (record.code == ScoringCode.OK)
                    request.token.candidateIds.map { NumericScore(it, -1.0, 1) } else emptyList())
            }
            override fun cancel() = Unit
            override fun unload() { unloads.add(true) }
            override fun close() = unload()
        }, 60_000, owner, checks)

        init { worker.onBind() }
        fun submit(id: Long, code: Int = ScoringCode.OK) {
            val input = ScoringInput(ScoringToken(1, id, id, candidates.indices.toList()), prefix, candidates)
            val record = Record(input, code)
            assertNull(records.put(id, record))
            worker.submit(input, { reply -> record.reply = reply }, {
                record.finished.incrementAndGet(); record.done.countDown()
            })
        }
        fun entered(id: Long) { assertEquals(id, starts.poll(3, TimeUnit.SECONDS)) }
        fun done(id: Long) {
            records.getValue(id).done.awaitBounded()
            // Drain worker finalization under its monitor before advancing virtual time.
            worker.cancel(1, Long.MAX_VALUE)
        }
        fun finish(id: Long) {
            records.getValue(id).release.countDown(); done(id)
            assertEquals(true, checks.stopped.poll(3, TimeUnit.SECONDS))
        }
        fun advance(wall: Long, cpu: Long) { clock.advance(wall, cpu); checks.task?.run() }
        fun idle(wall: Long) {
            assertNull(checks.task)
            clock.advance(wall, 0)
            assertEquals(ModelDutyProfile.CAPACITY_UNITS, owner.account().creditUnits)
            assertNull(checks.task)
        }
        fun cleanup() {
            assertEquals(true, unloads.poll(3, TimeUnit.SECONDS))
            assertEquals(true, checks.stopped.poll(3, TimeUnit.SECONDS))
            worker.cancel(1, Long.MAX_VALUE)
        }
        override fun close() {
            records.values.forEach { it.release.countDown() }
            worker.close(); checks.closed.awaitBounded()
            val lease = owner.acquireLease()
            assertTrue("worker must release its lease after mandatory close", lease != 0L)
            owner.release(lease)
        }
    }
    companion object {
        @JvmStatic @Parameterized.Parameters(name = "{0}-{1}")
        fun cases(): List<Array<Any>> = listOf(
            arrayOf("EN", 2, 257L, 862L), arrayOf("EN", 4, 469L, 1666L), arrayOf("EN", 8, 1004L, 3634L),
            arrayOf("RU", 2, 600L, 2138L), arrayOf("RU", 4, 1076L, 3937L), arrayOf("RU", 8, 2063L, 7656L),
            arrayOf("ES", 2, 369L, 1272L), arrayOf("ES", 4, 767L, 2702L), arrayOf("ES", 8, 1432L, 5263L),
        )
        private fun CountDownLatch.awaitBounded() { assertTrue("trace synchronization timeout", await(3, TimeUnit.SECONDS)) }
    }
}
