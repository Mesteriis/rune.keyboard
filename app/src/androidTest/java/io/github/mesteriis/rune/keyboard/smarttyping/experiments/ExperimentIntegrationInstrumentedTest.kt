package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.AndroidTypingPersonalization
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class ExperimentIntegrationInstrumentedTest {
    @Test fun packagedRankingAndTapModelsAreIndependent() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val model = ExperimentModels()
        context.assets.open("smarttyping/experiments/ru-ranking-context.bin").use { model.loadContext(it.readBytes()) }
        assertTrue(model.contextReady)
        assertFalse(model.tapReady)
        val ranking = model.contextScore("мы идём", "домой", KeyboardLanguage.RUSSIAN)
        context.assets.open("smarttyping/experiments/ru-context.bin").use { model.loadTapContext(it.readBytes()) }
        assertTrue(model.tapReady)
        val letters = model.nextLetters("мы идём", "д", KeyboardLanguage.RUSSIAN)
        model.loadContext(byteArrayOf())
        assertFalse(model.contextReady)
        assertTrue(model.tapReady)
        assertEquals(letters, model.nextLetters("мы идём", "д", KeyboardLanguage.RUSSIAN))
        context.assets.open("smarttyping/experiments/ru-ranking-context.bin").use { model.loadContext(it.readBytes()) }
        model.loadTapContext(byteArrayOf())
        assertTrue(model.contextReady)
        assertFalse(model.tapReady)
        assertEquals(ranking, model.contextScore("мы идём", "домой", KeyboardLanguage.RUSSIAN), 0.0)
    }

    @Test fun packagedAssetsLoadAndIndependentSwitchesReachActualScorers() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val resources = PersonalTypingResources.get(context)
        val ready = CountDownLatch(1)
        AndroidExperimentResources.whenReady { ready.countDown() }.use {
            assertTrue(ready.await(15, TimeUnit.SECONDS))
        }
        val models = resources.experiments
        assertTrue(models.learnedReady); assertTrue(models.contextReady); assertTrue(models.tapReady)
        resources.learning.configure(false, false, false)
        val candidate = GeneratedCandidate("привет", "привет", "привет", KeyboardLanguage.RUSSIAN,
            false, 4, 100, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.analyze("привт"))
        val adapter = AndroidTypingPersonalization(resources)
        fun score() = adapter.contextualPreference("он сказал ", "привт", candidate, KeyboardLanguage.RUSSIAN)
        assertEquals(0.0, score(), 0.0)
        adapter.learnedRankingEnabled = true
        val learned = score(); assertEquals(models.rankScore("он сказал ", "привт", candidate), learned, 1e-9)
        adapter.learnedRankingEnabled = false; adapter.compactContextEnabled = true
        val compact = score(); assertEquals(models.contextScore("он сказал ", "привет", KeyboardLanguage.RUSSIAN), compact, 1e-9)
        adapter.learnedRankingEnabled = true
        assertEquals(learned + compact, score(), 1e-9)
        adapter.learnedRankingEnabled = false; adapter.compactContextEnabled = false
        assertEquals(0.0, score(), 0.0)
        assertTrue(models.nextLetters("он сказал ", "приве", KeyboardLanguage.RUSSIAN).size == 33)
        assertTrue(models.nextLetters("", "hello", KeyboardLanguage.ENGLISH).isEmpty())

        // Synthetic warmed inference only; save numeric measurements, never editor text.
        repeat(20) { models.rankScore("он сказал ", "привт", candidate); models.contextScore("он сказал ", "привет", KeyboardLanguage.RUSSIAN) }
        fun measure(block: () -> Unit): String {
            val times = LongArray(200) { val start = System.nanoTime(); block(); System.nanoTime() - start }.sorted()
            return "{\"p50Ms\":${times[100] / 1e6},\"p95Ms\":${times[190] / 1e6},\"maxMs\":${times.last() / 1e6}}"
        }
        val rank = measure { models.rankScore("он сказал ", "привт", candidate) }
        val neural = measure { models.contextScore("он сказал ", "привет", KeyboardLanguage.RUSSIAN) }
        val letters = measure { models.nextLetters("он сказал ", "приве", KeyboardLanguage.RUSSIAN) }
        val combined = measure {
            repeat(3) {
                models.rankScore("он сказал ", "привт", candidate)
                models.contextScore("он сказал ", "привет", KeyboardLanguage.RUSSIAN)
            }
        }
        val maximum = measure {
            repeat(3) {
                models.rankScore("он сказал ".repeat(16), "а".repeat(128), candidate)
                models.contextScore("он сказал ".repeat(16), "а".repeat(32), KeyboardLanguage.RUSSIAN)
            }
        }
        File(context.cacheDir, "experiment-latency.json").writeText(
            "{\"samples\":200,\"rankOneCandidate\":$rank,\"contextOneSixLetterCandidate\":$neural,\"nextLetters\":$letters,\"combinedThreeSixLetterCandidates\":$combined,\"combinedThreeBoundedLongCandidates\":$maximum}")
    }
}
