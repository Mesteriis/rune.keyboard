package io.github.mesteriis.rune.keyboard.smarttyping.tools

import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.*
import io.github.mesteriis.rune.keyboard.settings.quality.QualityDashboardActivity
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.*
import io.github.mesteriis.rune.keyboard.smarttyping.quality.*
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Synthetic data on the selected test emulator; no private profile is imported. */
class TypingToolsInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext

    @Test fun tenControlsPersistIndependentlyThroughRecreation() {
        val prefs = KeyboardPreferences(context)
        val before = prefs.readSettings()
        val titles = listOf(R.string.settings_quality_metrics, R.string.settings_shadow_comparison,
            R.string.settings_word_boundaries, R.string.settings_abbreviations,
            R.string.settings_phrase_review, R.string.settings_visible_undo, R.string.settings_protected_words,
            R.string.settings_app_profiles, R.string.settings_collect_examples, R.string.settings_typo_patterns)
        fun flags(s: KeyboardSettings) = listOf(s.qualityMetrics, s.shadowComparison,
            s.wordBoundarySuggestions, s.abbreviations, s.phraseReview, s.visibleUndo,
            s.protectedWords, s.appProfiles, s.collectExamples, s.typoPatterns)
        val writes = listOf(prefs::writeQualityMetrics, prefs::writeShadowComparison,
            prefs::writeWordBoundarySuggestions, prefs::writeAbbreviations, prefs::writePhraseReview, prefs::writeVisibleUndo,
            prefs::writeProtectedWords, prefs::writeAppProfiles, prefs::writeCollectExamples, prefs::writeTypoPatterns)
        writes.forEach { it(false) }
        try {
            ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
                for (index in titles.indices) {
                    scenario.onActivity { activity ->
                        val title = descendants(activity.window.decorView).filterIsInstance<TextView>()
                            .single { it.id == R.id.row_title && it.text.toString() == activity.getString(titles[index]) }
                        val row = title.parent.parent as View
                        assertFalse(row.findViewById<CheckBox>(R.id.row_checkbox).isChecked)
                        assertTrue(row.performClick())
                    }
                    assertEquals(titles.indices.map { it <= index }, flags(prefs.readSettings()))
                }
                scenario.recreate()
                scenario.onActivity { activity ->
                    titles.forEach { resource ->
                        val title = descendants(activity.window.decorView).filterIsInstance<TextView>()
                            .single { it.id == R.id.row_title && it.text.toString() == activity.getString(resource) }
                        assertTrue((title.parent.parent as View).findViewById<CheckBox>(R.id.row_checkbox).isChecked)
                    }
                }
            }
        } finally { writes.zip(flags(before)).forEach { (write, value) -> write(value) } }
    }

    @Test fun abbreviationSaveIsDurableAndShownInManager() {
        val store = AbbreviationStore.get(context)
        awaitResult<AbbreviationResult> { store.reset(it) }.also { assertEquals(AbbreviationResult.SAVED, it) }
        try {
            assertEquals(AbbreviationResult.SAVED, awaitResult<AbbreviationResult> {
                store.save(KeyboardLanguage.RUSSIAN, "щас", "сейчас отвечу", onComplete = it)
            })
            assertEquals("сейчас отвечу", store.model.expansion("ЩАС", KeyboardLanguage.RUSSIAN))
            assertNull(store.model.expansion("щас", KeyboardLanguage.ENGLISH))
            val file = File(context.noBackupFilesDir, "abbreviations/entries.bin")
            assertEquals(1, AbbreviationCodec.decode(file.readBytes()).size)
            ActivityScenario.launch(AbbreviationSettingsActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    assertEquals(1, activity.findViewById<ViewGroup>(R.id.abbreviations_entries).childCount)
                    assertTrue(activity.findViewById<Button>(R.id.abbreviations_add).isEnabled)
                    val labels = descendants(activity.findViewById(R.id.abbreviations_entries)).filterIsInstance<TextView>()
                    assertTrue(labels.any { it.text.contains("сейчас отвечу") })
                }
            }
        } finally {
            assertEquals(AbbreviationResult.SAVED, awaitResult<AbbreviationResult> { store.reset(it) })
        }
    }

    @Test fun qualityDashboardShowsNumericEventsAndResetClearsDisk() {
        val store = QualityStore.get(context)
        assertTrue(awaitResult<Boolean> { store.reset(it) })
        store.configure(true, true, true)
        store.record(QualityEvent.ABBREVIATION_PICKED)
        store.compare(987654, "synthetic", "primary", "experimental")
        store.explicitChoice(987654, "experimental")
        assertEquals(1L, store.snapshot()[QualityEvent.ABBREVIATION_PICKED])
        assertEquals(1L, store.snapshot()[ShadowResult.EXPLICIT_EXPERIMENTAL])
        try {
            ActivityScenario.launch(QualityDashboardActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    assertTrue(activity.findViewById<TextView>(R.id.quality_actions).text.contains(
                        activity.getString(R.string.quality_count_format,
                            activity.getString(R.string.quality_abbreviation_picked), 1L)))
                    assertTrue(activity.findViewById<Button>(R.id.quality_reset).isEnabled)
                }
            }
        } finally {
            store.configure(false, false, false)
            assertTrue(awaitResult<Boolean> { store.reset(it) })
        }
        val bytes = File(context.noBackupFilesDir, "typing-quality-v1.txt").readBytes()
        assertFalse(String(bytes).contains("synthetic"))
        assertEquals(QualitySnapshot(), QualityCodec.decode(bytes))
    }

    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()

    private fun <T> awaitResult(start: ((T) -> Unit) -> Unit): T {
        val done = CountDownLatch(1)
        var result: T? = null
        start { result = it; done.countDown() }
        assertTrue(done.await(10, TimeUnit.SECONDS))
        return checkNotNull(result)
    }
}
