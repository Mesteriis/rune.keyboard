package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.os.Bundle
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.ceil

class NeighborRecoveryInstrumentedTest {
    @Test fun stagedWorkerKeepsFirstReplyLatency() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val loaded = AndroidPackedLexiconLoader.load(instrumentation.targetContext.assets, FrozenPackedLexicons.RUSSIAN)
        assertTrue(loaded is PackedLexiconLoad.Ready)
        val generator = CandidateGenerator(PackedCandidateLexicon(listOf((loaded as PackedLexiconLoad.Ready).lexicon)))
        val queue = java.util.concurrent.LinkedBlockingQueue<Runnable>()
        val baseline = mutableListOf<Double>()
        val staged = mutableListOf<Double>()
        var start = 0L
        var firstMs = 0.0
        var finished = false
        val worker = LocalCandidateWorker(generator, java.util.concurrent.Executor { queue.add(it) }, { reply ->
            if (reply.stage == CandidateStage.BASELINE) firstMs = (System.nanoTime() - start) / 1e6
            if (reply.isFinal) finished = true
        })
        try {
            repeat(240) { index ->
                val extended = index % 2 == 0
                finished = false
                start = System.nanoTime()
                assertTrue(worker.submit(LocalCandidateRequest(1, index.toLong(), index.toLong() + 1,
                    listOf("рооверка", "ролверка", "опботает", "клавиатуар", "пожалйста", "привет")[(index / 2) % 6],
                    KeyboardLanguage.RUSSIAN, true, neighborRecoveryEnabled = extended)))
                while (!finished) checkNotNull(queue.poll(2, java.util.concurrent.TimeUnit.SECONDS)).run()
                if (index >= 40) (if (extended) staged else baseline).add(firstMs)
            }
        } finally { worker.close() }
        fun p95(values: List<Double>) = values.sorted()[ceil(values.size * .95).toInt() - 1]
        val delta = p95(staged) - p95(baseline)
        instrumentation.sendStatus(0, Bundle().apply {
            putString("neighbor_first_reply_latency", "samples=100 baselineP95Ms=${p95(baseline)} stagedP95Ms=${p95(staged)} deltaMs=$delta")
        })
        assertTrue("First local reply regression exceeds 5 ms: $delta", delta <= 5.0)
    }

    @Test fun packagedRecoveryKeepsBaselineAndReportsLatency() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val loaded = AndroidPackedLexiconLoader.load(instrumentation.targetContext.assets, FrozenPackedLexicons.RUSSIAN)
        assertTrue(loaded is PackedLexiconLoad.Ready)
        val generator = CandidateGenerator(PackedCandidateLexicon(listOf((loaded as PackedLexiconLoad.Ready).lexicon)))
        val tokens = listOf("рооверка", "ролверка", "опботает", "клавиатуар", "пожалйста", "привет")
        val baselineTimes = mutableListOf<Double>()
        val recoveryTimes = mutableListOf<Double>()
        var complete = 0
        repeat(120) { iteration ->
            val token = tokens[iteration % tokens.size]
            val started = System.nanoTime()
            val baseline = generator.generate(token, KeyboardLanguage.RUSSIAN)
            val localEnd = System.nanoTime()
            val recovered = generator.generateRecovery(token, KeyboardLanguage.RUSSIAN, baseline)
            val ended = System.nanoTime()
            assertEquals(baseline.alternatives, recovered.alternatives)
            assertEquals(baseline.localSearch, recovered.localSearch)
            assertTrue(recovered.neighborRecovery.inspectedStates <= 32_768)
            assertTrue(recovered.neighborRecovery.verifiedTerminals <= 64)
            if (recovered.neighborRecovery.isComplete) {
                complete++
                if (token in listOf("рооверка", "ролверка"))
                    assertTrue(recovered.neighborRecovery.alternatives.any { it.text == "проверка" })
            }
            if (iteration >= 20) {
                baselineTimes += (localEnd - started) / 1e6
                recoveryTimes += (ended - localEnd) / 1e6
            }
        }
        assertTrue(complete > 0)
        fun p95(values: List<Double>) = values.sorted()[ceil(values.size * .95).toInt() - 1]
        instrumentation.sendStatus(0, Bundle().apply {
            putString("neighbor_recovery_latency", "samples=100 complete=$complete baselineP95Ms=${p95(baselineTimes)} recoveryP95Ms=${p95(recoveryTimes)} recoveryMaxMs=${recoveryTimes.max()}")
        })
    }
}
