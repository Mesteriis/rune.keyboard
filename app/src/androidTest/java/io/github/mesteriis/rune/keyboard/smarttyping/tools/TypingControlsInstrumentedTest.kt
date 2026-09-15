package io.github.mesteriis.rune.keyboard.smarttyping.tools

import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Button
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.*
import io.github.mesteriis.rune.keyboard.smarttyping.controls.*
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.learning.*
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.*
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Synthetic data only, on the explicitly selected emulator. */
class TypingControlsInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val language = KeyboardLanguage.ENGLISH

    @Test fun protectedWordVetoIsDurableAndIndependentOfGeneralLearning() {
        val resources = PersonalTypingResources.get(context)
        val store = resources.controls
        assertEquals(TypingControlStore.Result.SAVED, awaitResult<TypingControlStore.Result> { store.reset(it) })
        try {
            assertEquals(TypingControlStore.Result.SAVED, awaitResult<TypingControlStore.Result> { store.protect("Teh", language, it) })
            val bytes = File(context.noBackupFilesDir, "typing-controls-v1.bin").readBytes()
            assertTrue(TypingControlCodec.decode(bytes).contains("TEH", language))
            val candidate = GeneratedCandidate("the", "the", "the", language, false, 4, 1, 1,
                EditFeatures(1.0, 0, 0.0), 0, CasePattern.analyze("teh"))
            val generation = CandidateGeneration("teh", listOf(candidate), CandidateCompletion.COMPLETE, false, null, 1, 1)
            val adapter = AndroidTypingPersonalization(resources)
            adapter.protectionEnabled = true
            assertFalse(adapter.allowsAutomatic(generation, candidate, language))
            adapter.protectionEnabled = false
            assertTrue(adapter.allowsAutomatic(generation, candidate, language))
            ActivityScenario.launch(ProtectedWordsActivity::class.java).use { scenario ->
                scenario.onActivity { activity -> assertEquals(1, activity.findViewById<ViewGroup>(R.id.controls_entries).childCount) }
            }
        } finally { awaitResult<TypingControlStore.Result> { store.reset(it) } }
    }

    @Test fun disableAllIsAtomicAndKeepsProtectedWordsAndProfileAssignments() {
        val prefs = KeyboardPreferences(context)
        val store = TypingControlStore.get(context)
        awaitResult<TypingControlStore.Result> { store.reset(it) }
        val writes = listOf(prefs::writePersonalLearning, prefs::writeTouchPersonalization, prefs::writePhraseSuggestions,
            prefs::writeQualityMetrics, prefs::writeShadowComparison, prefs::writeWordBoundarySuggestions,
            prefs::writeAbbreviations, prefs::writePhraseReview, prefs::writeVisibleUndo, prefs::writeProtectedWords,
            prefs::writeAppProfiles, prefs::writeCollectExamples, prefs::writeTypoPatterns,
            prefs::writeLearnedRanking, prefs::writeCompactContext, prefs::writeDynamicTouch, prefs::writeDynamicTouchApply,
            prefs::writeManualCandidateExpansion)
        val before = DiagnosticFeatures.configured(prefs.readSettings())
        val features = listOf(DiagnosticFeature.PERSONAL_LEARNING, DiagnosticFeature.TOUCH_PERSONALIZATION,
            DiagnosticFeature.PHRASE_SUGGESTIONS, DiagnosticFeature.QUALITY_METRICS, DiagnosticFeature.SHADOW_COMPARISON,
            DiagnosticFeature.WORD_BOUNDARIES, DiagnosticFeature.ABBREVIATIONS, DiagnosticFeature.PHRASE_REVIEW,
            DiagnosticFeature.VISIBLE_UNDO, DiagnosticFeature.PROTECTED_WORDS, DiagnosticFeature.APP_PROFILES,
            DiagnosticFeature.COLLECT_EXAMPLES, DiagnosticFeature.TYPO_PATTERNS,
            DiagnosticFeature.LEARNED_RANKING, DiagnosticFeature.COMPACT_CONTEXT,
            DiagnosticFeature.DYNAMIC_TOUCH, DiagnosticFeature.DYNAMIC_TOUCH_APPLY, DiagnosticFeature.MANUAL_CANDIDATE_EXPANSION)
        awaitResult<TypingControlStore.Result> { store.protect("codex", language, it) }
        store.observePackage(context.packageName)
        assertEquals(TypingControlStore.Result.SAVED, awaitResult<TypingControlStore.Result> {
            store.assign(context.packageName, TypingProfile.FORMAL, it)
        })
        try {
            writes.forEach { it(true) }
            ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val title = descendants(activity.window.decorView).filterIsInstance<TextView>()
                        .single { it.id == R.id.row_title && it.text.toString() == activity.getString(R.string.controls_disable_all) }
                    assertTrue((title.parent.parent as View).performClick())
                }
            }
            val after = DiagnosticFeatures.configured(prefs.readSettings())
            features.forEach { assertEquals(0, after and it.bit) }
            assertTrue(store.snapshot.contains("codex", language))
            assertEquals(TypingProfile.FORMAL, store.snapshot.profile(context.packageName))
            assertEquals(TypingProfile.DEFAULT,
                TypingProfileResolver.resolve(prefs.readSettings(), context.packageName, store.snapshot).first)
        } finally {
            writes.zip(features).forEach { (write, feature) -> write(before and feature.bit != 0) }
            awaitResult<TypingControlStore.Result> { store.reset(it) }
        }
    }

    @Test fun manualExpansionTogglePersistsAcrossSettingsRecreation() {
        val prefs = KeyboardPreferences(context)
        val before = prefs.readSettings().manualCandidateExpansion
        prefs.writeManualCandidateExpansion(false)
        try {
            ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
                fun toggle(expected: Boolean) {
                    scenario.onActivity { activity ->
                        val title = descendants(activity.window.decorView).filterIsInstance<TextView>()
                            .single { it.id == R.id.row_title &&
                                it.text.toString() == activity.getString(R.string.settings_manual_candidate_expansion) }
                        val row = title.parent.parent as View
                        assertEquals(expected, row.findViewById<android.widget.CheckBox>(R.id.row_checkbox).isChecked)
                        assertTrue(row.performClick())
                    }
                    assertEquals(!expected, prefs.readSettings().manualCandidateExpansion)
                }
                toggle(false)
                scenario.recreate()
                val configured = DiagnosticFeatures.configured(prefs.readSettings())
                assertTrue(configured and DiagnosticFeature.MANUAL_CANDIDATE_EXPANSION.bit != 0)
                toggle(true)
            }
        } finally { prefs.writeManualCandidateExpansion(before) }
    }

    @Test fun profileManagerShowsAssignedAppAndItsPreset() {
        val store = TypingControlStore.get(context)
        awaitResult<TypingControlStore.Result> { store.reset(it) }
        store.observePackage(context.packageName)
        assertEquals(TypingControlStore.Result.SAVED, awaitResult<TypingControlStore.Result> {
            store.assign(context.packageName, TypingProfile.CONVERSATION, it)
        })
        try {
            ActivityScenario.launch(AppProfilesActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val entries = activity.findViewById<ViewGroup>(R.id.controls_entries)
                    assertEquals(1, entries.childCount)
                    assertTrue(descendants(entries).filterIsInstance<TextView>().any {
                        it.text.contains(activity.getString(R.string.controls_profile_chat))
                    })
                }
            }
        } finally { awaitResult<TypingControlStore.Result> { store.reset(it) } }
    }

    @Test fun learningLabRecreatesAndEvaluatesShippedLexiconOnFrozenHoldout() {
        val store = LearningStore.get(context)
        assertTrue(awaitResult<Boolean> { store.reset(it) })
        store.configure(true, true, true)
        // Known words with deterministic holdout selection; do not assume a particular hash bucket.
        val word = listOf("hello", "world", "test", "good", "house", "work", "people", "water", "time", "day", "night", "friend")
            .first { LearningModel.holdout(language, it) }
        store.confirmed(word, language)
        val result = AndroidLearningEvaluation.run(context.assets, store.snapshot()) { false }
        assertEquals(1, result.heldOut)
        assertEquals(1, result.evaluated)
        assertFalse(result.cancelled)
        try {
            ActivityScenario.launch(LearningLabActivity::class.java).use { scenario ->
                scenario.recreate()
                scenario.onActivity { activity ->
                    assertTrue(activity.findViewById<Button>(R.id.learning_run).isEnabled)
                    assertTrue(activity.findViewById<TextView>(R.id.learning_status).text.isNotEmpty())
                }
            }
        } finally {
            store.configure(false, false, false)
            assertTrue(awaitResult<Boolean> { store.reset(it) })
        }
        assertTrue(LearningCodec.decode(File(context.noBackupFilesDir, "learning-lab/learning.bin").readBytes()).evidence.isEmpty())
    }

    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
    private fun <T> awaitResult(start: ((T) -> Unit) -> Unit): T {
        val done = CountDownLatch(1); var result: T? = null
        start { result = it; done.countDown() }; assertTrue(done.await(10, TimeUnit.SECONDS)); return checkNotNull(result)
    }
}
