package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.os.Bundle
import android.os.Debug
import android.os.Looper
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

/** Fixed public development requests. Actual Android CPU/wall observations, never an energy gate. */
class TopSevenInstrumentedTest {
    @Test fun packedTopSevenAndExhaustiveComparison() {
        assertNotSame(Looper.getMainLooper(), Looper.myLooper())
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val (requests, handles) = fixtures()
        val packed = PackedCandidateLexicon(handles)
        val exhaustive = object : CandidateLexicon by PackedCandidateLexicon(handles) {
            override fun selectTop(key: String, route: LanguageRoute, pattern: CasePattern,
                control: CandidateSearchControl, maximumAlternatives: Int): TopCandidateSelection? = null
        }
        val generators = listOf(CandidateGenerator(exhaustive), CandidateGenerator(packed))
        val expected = HashMap<Int, List<CandidateGeneration>>()
        fun observe(request: Request, strategy: Int, round: Int, record: Boolean): CandidateGeneration {
            val cpuStart = Debug.threadCpuTimeNanos()
            val wallStart = SystemClock.elapsedRealtimeNanos()
            val result = generators[strategy].generate(request.token, request.language)
            val wall = SystemClock.elapsedRealtimeNanos() - wallStart
            val cpu = Debug.threadCpuTimeNanos() - cpuStart
            assertTrue("NUMERIC_DURATION", cpu >= 0 && wall >= 0)
            assertTrue("ORIGINAL_PRESERVED", result.original == request.token)
            assertTrue("SHARED_BOUNDS", result.inspectedStates <= 8192 && result.verifiedTerminals <= 64)
            assertTrue("BOUNDED_SET", result.alternatives.size <= 7)
            assertFalse("NO_READER_FAILURE", result.completion in listOf(CandidateCompletion.READER_FAILURE, CandidateCompletion.UNAVAILABLE))
            if (record) instrumentation.sendStatus(0, Bundle().apply {
                putString("top_seven_measurement", "v1 id=${request.id} strategy=$strategy round=$round " +
                    "wall_ns=$wall cpu_ns=$cpu states=${result.inspectedStates} verified=${result.verifiedTerminals} " +
                    "completion=${result.completion.ordinal} alternatives=${result.alternatives.size}")
            })
            return result
        }
        // Two unmeasured passes, alternating strategy order; initialize scratch and exercise JIT.
        repeat(2) { round ->
            for (request in requests) {
                val order = if ((request.id + round) % 2 == 0) listOf(0, 1) else listOf(1, 0)
                val results = arrayOfNulls<CandidateGeneration>(2)
                for (strategy in order) results[strategy] = observe(request, strategy, round, false)
                val baseline = results[0]!!; val top = results[1]!!
                if (baseline.isComplete) {
                    assertTrue("BASELINE_COMPLETE_PRESERVED", top.isComplete)
                    assertEquals("FULL_SET_IDENTITY", baseline.alternatives, top.alternatives)
                }
                expected[request.id] = listOf(baseline, top)
            }
        }
        repeat(5) { round ->
            for (request in requests) {
                val order = if ((request.id + round) % 2 == 0) listOf(0, 1) else listOf(1, 0)
                for (strategy in order) {
                    val result = observe(request, strategy, round, true)
                    assertEquals("REPEATABLE_RESULT", expected.getValue(request.id)[strategy], result)
                }
            }
        }
        // Real packed query cancellation and next-request recovery; never retain cancelled payload.
        var calls = 0
        val request = requests.first()
        val cancelled = generators[1].generate(request.token, request.language, CandidateCancellation { ++calls >= 30 })
        assertEquals(CandidateCompletion.CANCELLED, cancelled.completion)
        assertNull(cancelled.original); assertTrue(cancelled.alternatives.isEmpty())
        assertEquals(expected.getValue(request.id)[1], generators[1].generate(request.token, request.language))
    }

    /** Identical public inputs and search caps; width is fixed before each generator runs. */
    @Test fun requestedWidthsPreserveCertifiedPrefixes() {
        assertNotSame(Looper.getMainLooper(), Looper.myLooper())
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val (requests, handles) = fixtures()
        val widths = listOf(1, 3, 7)
        val generators = widths.associateWith { CandidateGenerator(PackedCandidateLexicon(handles), it) }
        val expected = HashMap<Pair<Int, Int>, CandidateGeneration>()
        repeat(7) { round ->
            for (request in requests) {
                val order = if ((round + request.id) % 2 == 0) widths else widths.reversed()
                val results = HashMap<Int, CandidateGeneration>()
                for (maximum in order) {
                    val cpuStart = Debug.threadCpuTimeNanos()
                    val wallStart = SystemClock.elapsedRealtimeNanos()
                    val result = generators.getValue(maximum).generate(request.token, request.language)
                    val wall = SystemClock.elapsedRealtimeNanos() - wallStart
                    val cpu = Debug.threadCpuTimeNanos() - cpuStart
                    assertTrue(cpu >= 0 && wall >= 0)
                    assertEquals(request.token, result.original)
                    assertTrue(result.inspectedStates <= 8192 && result.verifiedTerminals <= 64)
                    assertTrue(result.alternatives.size <= maximum)
                    assertFalse(result.completion in listOf(CandidateCompletion.READER_FAILURE, CandidateCompletion.UNAVAILABLE))
                    if (!result.isComplete) assertTrue(result.prohibitsAutoReplace)
                    val key = request.id to maximum
                    if (round == 0) expected[key] = result else assertEquals(expected[key], result)
                    results[maximum] = result
                    if (round >= 2) instrumentation.sendStatus(0, Bundle().apply {
                        putString("candidate_width_measurement", "v1 id=${request.id} maximum=$maximum round=${round - 2} " +
                            "wall_ns=$wall cpu_ns=$cpu states=${result.inspectedStates} verified=${result.verifiedTerminals} " +
                            "completion=${result.completion.ordinal} alternatives=${result.alternatives.size}")
                    })
                }
                for (larger in widths) for (smaller in widths.filter { it < larger }) {
                    val full = results.getValue(larger)
                    val prefix = results.getValue(smaller)
                    if (full.isComplete) {
                        assertTrue(prefix.isComplete)
                        assertEquals(full.alternatives.take(smaller), prefix.alternatives)
                    }
                    assertTrue(prefix.inspectedStates <= full.inspectedStates)
                    assertTrue(prefix.verifiedTerminals <= full.verifiedTerminals)
                }
            }
        }
    }

    private fun fixtures(): Pair<List<Request>, List<PackedLexiconData>> {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val bytes = instrumentation.context.assets.open("top-seven/requests.tsv").use { it.readBytes() }
        assertEquals(FIXTURE_SHA, PackedLexiconManifest.hex(MessageDigest.getInstance("SHA-256").digest(bytes)))
        val requests = bytes.toString(Charsets.US_ASCII).lineSequence().filter { it.isNotEmpty() }.map { line ->
            val fields = line.split('\t')
            Request(fields[0].toInt(), KeyboardLanguage.entries.single { it.locale.language == fields[1] },
                String(fields[2].split(',').map { it.toInt(16).toChar() }.toCharArray()))
        }.toList()
        assertEquals(60, requests.size)
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH).map {
            val loaded = AndroidPackedLexiconLoader.load(instrumentation.targetContext.assets, it)
            assertTrue("VALIDATED_PACKED_HANDLE", loaded is PackedLexiconLoad.Ready)
            (loaded as PackedLexiconLoad.Ready).lexicon
        }
        return requests to handles
    }

    private class Request(val id: Int, val language: KeyboardLanguage, val token: String)
    companion object {
        private const val FIXTURE_SHA = "364369c7b716e617536725ff1f6622f722addaeca592962dfc1743c931c11e7c"
    }
}
