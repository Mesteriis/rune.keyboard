package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.os.Bundle
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CommonConfusions
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ExperimentModels
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import kotlin.math.ceil

class ManualRetrievalInstrumentedTest {
    @Test fun userReportedRussianMisspellingsExposeCurrentLocalCoverage() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val loaded = AndroidPackedLexiconLoader.load(context.assets, FrozenPackedLexicons.RUSSIAN)
        assertTrue(loaded is PackedLexiconLoad.Ready)
        val generator = CandidateGenerator(
            PackedCandidateLexicon(listOf((loaded as PackedLexiconLoad.Ready).lexicon)),
            canonicalCaseLexicon = AndroidCanonicalCaseLexicon(context.assets),
        )
        val morphology = AndroidMorphologyLexiconLoader.load(context.assets)
        val probes: List<Pair<String, String?>> = listOf(
            "заберай" to "забирай",
            "смотруть" to "смотреть",
            "ощющениям" to "ощущениям",
            "ность" to null,
        )
        probes.forEachIndexed { index, (token, expected) ->
            val generation = generator.generate(token, KeyboardLanguage.RUSSIAN)
            val commonId = CommonConfusions.preferredId(generation, KeyboardLanguage.RUSSIAN)
            val local = LocalCorrectionPolicy.decide(generation, KeyboardLanguage.RUSSIAN)
            val selectedKey = generation.alternatives.getOrNull(commonId - 1)?.canonicalKey
                ?: local?.canonicalKey
            assertEquals(expected, selectedKey)
            val morphologyFacts = (listOf(token) + generation.localSearch.alternatives.map { it.terminalKey })
                .distinct().joinToString("|") { word ->
                    val membership = morphology.lookup(KeyboardLanguage.RUSSIAN, word)
                    "$word:${membership.available}:${membership.present}:${membership.lemmaId ?: 0}"
                }
            instrumentation.sendStatus(0, Bundle().apply {
                putString("reported_misspelling_probe",
                        "v1 id=$index completion=${generation.completion.name} " +
                        "alternatives=${generation.alternatives.joinToString("|") { it.text }} " +
                        "source=${if (commonId > 0) "COMMON" else "GENERAL"} " +
                        "local=${selectedKey ?: "NONE"} morphology=$morphologyFacts")
            })
        }
    }

    @Test fun packagedRetrievalKeepsBaselineAndMeasuresBoundedExtraWork() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN,
            FrozenPackedLexicons.SPANISH).map {
            val result = AndroidPackedLexiconLoader.load(context.assets, it)
            assertTrue(result is PackedLexiconLoad.Ready)
            (result as PackedLexiconLoad.Ready).lexicon
        }
        val generator = CandidateGenerator(PackedCandidateLexicon(handles), CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES)
        val models = ExperimentModels()
        context.assets.open("smarttyping/experiments/ru-ranker.bin").use { models.loadRanker(it.readBytes()) }
        context.assets.open("smarttyping/experiments/ru-ranker-auto-v1.bin").use {
            models.loadLegacyAutomaticRanker(it.readBytes())
        }
        context.assets.open("smarttyping/experiments/ru-ranking-context.bin").use { models.loadContext(it.readBytes()) }
        assertTrue(models.learnedReady && models.legacyAutomaticReady && models.contextReady)
        val language = KeyboardLanguage.RUSSIAN
        // Synthetic fixtures cover valid, short, long, and dense typo neighborhoods.
        val tokens = listOf("привет", "привте", "клавиатуар", "пожалйста", "интресно", "сегодння",
            "сообщене", "предложенеи", "корректировк", "а".repeat(32))
        val baselineTimes = ArrayList<Double>()
        val extraTimes = ArrayList<Double>()
        val totalTimes = ArrayList<Double>()
        val scoredTimes = ArrayList<Double>()
        var maxStates = 0
        var maxTerminals = 0
        var expandedQueries = 0
        var maxPool = 0
        repeat(220) { iteration ->
            val token = tokens[iteration % tokens.size]
            val started = System.nanoTime()
            val baseline = generator.generate(token, language)
            val baselineEnd = System.nanoTime()
            val localBefore = LocalCorrectionPolicy.decide(baseline, language)
            val manualStart = System.nanoTime()
            val pool = generator.generateManualPool(token, language, baseline, true)
            val poolEnd = System.nanoTime()
            val candidates = pool?.alternatives ?: baseline.alternatives
            assertEquals(localBefore, LocalCorrectionPolicy.decide(baseline, language))
            assertNull(generator.generateManualPool(token, language, baseline, false))
            assertTrue(candidates.size <= CandidateGenerator.MAX_ALTERNATIVES)
            assertTrue(candidates.map { it.canonicalKey }.containsAll(baseline.alternatives.map { it.canonicalKey }))
            assertEquals(candidates.size, candidates.map { it.canonicalKey }.distinct().size)
            if (baseline.isValidWord || baseline.protectedReason != null) assertNull(pool)
            pool?.let {
                assertTrue(it.inspectedStates in 0..CandidateSearchControl.MAX_STATES)
                assertTrue(it.verifiedTerminals in 0..CandidateSearchControl.MAX_VERIFIED)
                maxStates = maxOf(maxStates, it.inspectedStates)
                maxTerminals = maxOf(maxTerminals, it.verifiedTerminals)
            }
            val scoreStart = System.nanoTime()
            candidates.forEach { candidate ->
                assertTrue(models.rankScore("он написал ", token, candidate).isFinite())
                assertTrue(models.contextScore("он написал ", candidate.text, language).isFinite())
            }
            val scoreNanos = System.nanoTime() - scoreStart
            if (iteration >= 20) {
                baselineTimes.add((baselineEnd - started) / 1e6)
                extraTimes.add((poolEnd - manualStart) / 1e6)
                totalTimes.add((baselineEnd - started + poolEnd - manualStart) / 1e6)
                scoredTimes.add((baselineEnd - started + poolEnd - manualStart + scoreNanos) / 1e6)
                if (candidates.size > baseline.alternatives.size) expandedQueries++
                maxPool = maxOf(maxPool, candidates.size)
            }
        }
        assertTrue("Fixtures must exercise expansion", expandedQueries > 0)
        assertTrue(maxPool > CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES)
        fun percentiles(times: List<Double>): String {
            val sorted = times.sorted()
            fun value(p: Double) = sorted[(ceil(p * sorted.size).toInt() - 1).coerceAtLeast(0)]
            return "{\"p50Ms\":${value(.5)},\"p95Ms\":${value(.95)},\"maxMs\":${sorted.last()}}"
        }
        val report = "{\"samples\":200,\"warmupQueries\":20,\"fixtureCount\":${tokens.size}," +
                "\"baseline\":${percentiles(baselineTimes)},\"manualAdditional\":${percentiles(extraTimes)}," +
                "\"totalRetrieval\":${percentiles(totalTimes)},\"retrievalAndCombinedScoring\":${percentiles(scoredTimes)}," +
                "\"expandedQueries\":$expandedQueries,\"maximumPool\":$maxPool," +
                "\"maximumManualStates\":$maxStates,\"maximumManualTerminals\":$maxTerminals}"
        File(context.cacheDir, "retrieval-latency.json").writeText(report)
        InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
            putString("retrieval_latency", report)
        })
    }

    @Test fun qualifiedCompactAutomaticPathRunsWithinMeasuredDeviceBudget() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN,
            FrozenPackedLexicons.SPANISH).map {
            val result = AndroidPackedLexiconLoader.load(context.assets, it)
            assertTrue(result is PackedLexiconLoad.Ready)
            (result as PackedLexiconLoad.Ready).lexicon
        }
        val morphology = AndroidMorphologyLexiconLoader.load(context.assets)
        val rareWords = AndroidRareWordLexiconLoader.load(context.assets)
        val generator = CandidateGenerator(PackedCandidateLexicon(handles),
            CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
            AndroidCanonicalCaseLexicon(context.assets), morphology, rareWords)
        val models = ExperimentModels()
        context.assets.open("smarttyping/experiments/ru-ranker.bin").use { models.loadRanker(it.readBytes()) }
        context.assets.open("smarttyping/experiments/ru-ranker-auto-v1.bin").use {
            models.loadLegacyAutomaticRanker(it.readBytes())
        }
        context.assets.open("smarttyping/experiments/ru-ranking-context.bin").use { models.loadContext(it.readBytes()) }
        assertTrue(models.learnedReady && models.legacyAutomaticReady && models.contextReady)
        val probes = listOf(
            Triple("В интерпретации Уолкиера «сатанизм не говорит давайте", "ыйдем", "выйдем"),
            Triple("снаряжение не носились (оружие носилось в кобуре под плащом; обязательным элементом снаряжения при исполнении служебных обязанностей был", "висток", "свисток"),
            Triple("2000 — в Утене начато производство питьевой воды Vichy Classique,", "сидраа", "сидра"),
            Triple("Автор музыки и слов песни\u00a0— Пол", "маккртни", "маккартни"),
            Triple("В Сенсорном саду находятся растения, которые можно", "отрогать", "потрогать"),
        )
        val generationTimes = ArrayList<Double>()
        val decisionTimes = ArrayList<Double>()
        val totalTimes = ArrayList<Double>()
        repeat(120) { iteration ->
            val (prefix, token, expected) = probes[iteration % probes.size]
            val started = System.nanoTime()
            val generation = generator.generate(token, KeyboardLanguage.RUSSIAN)
            val generated = System.nanoTime()
            assertTrue(generation.compactAlternatives.isNotEmpty())
            assertEquals(expected, models.compactAutomaticCandidate(prefix, generation,
                KeyboardLanguage.RUSSIAN)?.terminalKey)
            val decided = System.nanoTime()
            if (iteration >= 20) {
                generationTimes += (generated - started) / 1e6
                decisionTimes += (decided - generated) / 1e6
                totalTimes += (decided - started) / 1e6
            }
        }
        fun percentiles(times: List<Double>): String {
            val sorted = times.sorted()
            fun value(p: Double) = sorted[(ceil(p * sorted.size).toInt() - 1).coerceAtLeast(0)]
            return "{\"p50Ms\":${value(.5)},\"p95Ms\":${value(.95)},\"maxMs\":${sorted.last()}}"
        }
        val report = "{\"samples\":100,\"warmupQueries\":20,\"fixtureCount\":${probes.size}," +
            "\"generation\":${percentiles(generationTimes)}," +
            "\"compactDecision\":${percentiles(decisionTimes)}," +
            "\"total\":${percentiles(totalTimes)}}"
        instrumentation.sendStatus(0, Bundle().apply {
            putString("compact_automatic_latency", report)
        })
    }
}
