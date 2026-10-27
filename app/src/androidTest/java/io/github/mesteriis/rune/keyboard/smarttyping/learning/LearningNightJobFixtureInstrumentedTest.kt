package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager
import android.os.SystemClock
import android.util.AtomicFile
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidCanonicalCaseLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidPackedLexiconLoader
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedCandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedLexiconLoad
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.time.ZonedDateTime
import java.util.concurrent.locks.LockSupport

/** Explicit disposable-emulator fixture. Never seed a physical or ordinary test installation. */
@RunWith(AndroidJUnit4::class)
class LearningNightJobFixtureInstrumentedTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val arguments get() = InstrumentationRegistry.getArguments()
    private val report get() = File(context.cacheDir, "review-u13-state.json")

    @Before fun requireIsolatedEmulator() {
        assumeTrue("Explicit isolated-emulator fixture only", arguments.getString("reviewU13") == "true")
        assumeTrue("Physical devices are excluded", Build.HARDWARE in setOf("ranchu", "goldfish"))
        check(context.packageName == "io.github.mesteriis.rune.keyboard")
    }

    @Test fun seedFixture() {
        val language = KeyboardLanguage.ENGLISH
        val model = LearningModel().apply { configure(true, true, true) }
        WORDS.filterNot { LearningModel.holdout(language, it) }.take(3).forEach {
            assertTrue(model.record(it + "z", it, language, FeedbackSource.ACCEPTED))
        }
        val active = LearningPatternPolicy(mapOf((language to TypoPattern.SUBSTITUTION) to 3))
        val candidate = model.snapshot().candidatePolicy()
        assertEquals(3, candidate.counts[language to TypoPattern.DELETION])
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH)
            .map { (AndroidPackedLexiconLoader.load(context.assets, it) as PackedLexiconLoad.Ready).lexicon }
        val generator = CandidateGenerator(PackedCandidateLexicon(handles), canonicalCaseLexicon = AndroidCanonicalCaseLexicon(context.assets))
        // Functional promotion fixture, not independent quality evidence. Expected
        // words are declared here; only complete real APK pools are accepted.
        val completions = mutableMapOf<String, Int>()
        var retrieved = 0
        val held = WORDS.filter { LearningModel.holdout(language, it) }.mapNotNull { expected ->
            val original = expected + "z"
            val generation = generator.generate(original, language)
            completions[generation.completion.name] = (completions[generation.completion.name] ?: 0) + 1
            if (generation.alternatives.any { LearningModel.normalize(it.text) == expected }) retrieved++
            if (generation.completion != CandidateCompletion.COMPLETE) return@mapNotNull null
            val learned = generation.alternatives.sortedByDescending { LearningModel.preference(candidate, original, it.text, language) }
            if (LearningModel.normalize(learned.firstOrNull()?.text.orEmpty()) != expected) return@mapNotNull null
            val previous = generation.alternatives.sortedByDescending { LearningModel.preference(active, original, it.text, language) }
            expected to (LearningModel.normalize(previous.firstOrNull()?.text.orEmpty()) != expected)
        }.sortedByDescending { it.second }.take(15)
        writeReport(JSONObject().put("probeCompletions", JSONObject(completions.toMap())).put("retrievedTargets", retrieved).put("usableTargets", held.size))
        assertTrue("Need sufficient real held-out fixture targets", held.size >= 10)
        assertTrue("Need a real suggestion-order gain", held.any { it.second })
        held.forEach { (word, _) ->
            assertTrue(model.record(word, word, language, FeedbackSource.CONFIRMED))
            assertTrue(model.record(word + "z", word, language, FeedbackSource.ACCEPTED))
        }
        val snapshot = model.snapshot().copy(activePolicy = active)
        val evaluation = AndroidLearningEvaluation.run(context.assets, snapshot) { false }
        assertTrue("Complete real APK evaluation must approve fixture", evaluation.promotion.promotionApproved)
        assertEquals(0, evaluation.regressions)
        assertEquals(0, evaluation.unavailable)
        val root = File(context.noBackupFilesDir, "learning-lab").apply { check(mkdirs() || isDirectory) }
        val storage = AtomicFile(File(root, "learning.bin"));val stream = storage.startWrite()
        try { stream.write(LearningCodec.encode(snapshot)); stream.fd.sync(); storage.finishWrite(stream) }
        catch (error: Throwable) { storage.failWrite(stream); throw error }
        assertEquals(snapshot, LearningCodec.decode(storage.readFully()))
        KeyboardPreferences(context).apply { writeCollectExamples(true); writeTypoPatterns(true) }
        // Commit waits for the public facade's pending apply writes before the
        // host stops this disposable process to reload the seeded profile.
        assertTrue(context.getSharedPreferences("keyboard_preferences", Context.MODE_PRIVATE).edit().commit())
        writeReport(JSONObject().put("seeded", true).put("heldOut", evaluation.heldOut)
            .put("improvements", evaluation.improvements).put("regressions", evaluation.regressions)
            .put("promotionApproved", evaluation.promotion.promotionApproved))
    }

    @Test fun observeJob() {
        val expected = arguments.getString("reviewU13Expected")
        check(expected in setOf("blocked", "promoted"))
        val store = LearningStore.get(context)
        val loadDeadline = SystemClock.elapsedRealtime() + 10_000
        while (store.readiness == LearningStore.Readiness.LOADING && SystemClock.elapsedRealtime() < loadDeadline) SystemClock.sleep(10)
        assertTrue(store.isReady)
        val before = store.snapshot()
        assertNotEquals(before.activePolicy, before.candidatePolicy())
        assertTrue(LearningJobScheduler.sync(context, false))
        assertTrue(LearningJobScheduler.sync(context, true))
        writeReport(JSONObject().put("observerReady", true).put("expectedPromotion", expected == "promoted"))
        var promoting = false
        val deadline = SystemClock.elapsedRealtime() + if (expected == "blocked") 12_000 else 90_000
        while (SystemClock.elapsedRealtime() < deadline) {
            if (store.readiness == LearningStore.Readiness.PROMOTING) promoting = true
            if (store.isReady && store.snapshot().activePolicy != before.activePolicy) break
            LockSupport.parkNanos(100_000)
        }
        val after = store.snapshot()
        val conditions = conditions()
        val result = conditions.put("observerReady", true).put("finished", true).put("promotingObserved", promoting)
            .put("activeChanged", after.activePolicy != before.activePolicy)
            .put("activeMatchesCandidate", after.activePolicy == before.candidatePolicy())
            .put("rollbackMatchesPrevious", after.rollbackPolicy == before.activePolicy)
            .put("storeReady", store.isReady)
        writeReport(result)
        assertTrue(conditions.getBoolean("night"))
        assertTrue(conditions.getBoolean("screenOff"))
        assertTrue(conditions.getBoolean("charging"))
        assertFalse("Doze must not be forced", conditions.getBoolean("deepIdle"))
        if (expected == "blocked") {
            assertFalse(promoting)
            assertEquals(before.activePolicy, after.activePolicy)
        } else {
            assertTrue("Must observe actual PROMOTING state", promoting)
            assertEquals(before.candidatePolicy(), after.activePolicy)
            assertEquals(before.activePolicy, after.rollbackPolicy)
            assertTrue(store.isReady)
            assertEquals(true, store.lastWriteSucceeded)
        }
    }

    private fun conditions(): JSONObject {
        val power = context.getSystemService(PowerManager::class.java)
        val battery = checkNotNull(context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)))
        val status = battery.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        return JSONObject().put("night", LearningJobPolicy.isNight(ZonedDateTime.now()))
            .put("screenOff", !power.isInteractive).put("deepIdle", power.isDeviceIdleMode)
            .put("charging", status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL)
    }

    private fun writeReport(result: JSONObject) {
        val temp = File(context.cacheDir, "review-u13-state.tmp").apply { writeText(result.toString()) }
        check(temp.renameTo(report))
    }

    private companion object {
        val WORDS = ("about above after again along also always around away back before begin being below better both bring build came carry change children city close come could day different does down each early end even every face family far feel few find first form found four friend from full game gave general get give good great group grow hand hard have hear help here high home house however include inside just keep kind know land large last late later learn least leave left less life light light like line list little live long look made make man many mean might more most move much must name near need never new next night number off old once only open order other our out over own part people place play point problem put right room said same saw school second see seem set several shall should show side since small some something sound still such system take tell than that their them then there these thing think this those three through time together too toward try turn two under until upon use very want war water way well went were what when where which while white whole why will woman word work world would write year young your " +
            "ability absent accept access account action active actual adjust admit advice affect afraid agent agree ahead almost alone amount animal anyone appear arrive artist asleep attend autumn balance beauty become beside beyond bottle bottom branch breath bridge bright broken butter camera candle centre chance choose church circle common corner cotton course create danger degree demand design detail direct doctor double driver effort eighty either engine entire escape except expect expert explain factor fairly famous father figure finish flower follow forest forget former forty fresh future garden gentle ground happen hardly health heavy human hundred imagine indeed inform injury instead invite island itself lawyer leader letter listen lovely market matter member memory method middle minute modern moment mother myself narrow nation nature nearly neither normal notice object obtain office orange parent partly people period person phrase picture plenty pocket police prefer pretty prison proper quick quiet rather reach ready reason recent record reduce refuse remain remove repeat report result return review rhythm safety season secret serious settle shadow signal simple sister slowly social speech spring square stable station steady strange street strong study sudden summer supply surely symbol system target though throat ticket travel trouble twelve twenty unless useful valley various village visit voice volume weight welcome window winter within wonder worker yellow").split(' ').distinct()
    }
}
