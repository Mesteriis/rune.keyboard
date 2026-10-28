package io.github.mesteriis.rune.keyboard.smarttyping.tools

import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.Switch
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

    @Test fun fourteenControlsPersistIndependentlyThroughRecreation() {
        val prefs = KeyboardPreferences(context)
        val before = prefs.readSettings()
        val titles = listOf(R.string.settings_quality_metrics, R.string.settings_shadow_comparison,
            R.string.settings_word_boundaries, R.string.settings_abbreviations,
            R.string.settings_phrase_review, R.string.settings_visible_undo, R.string.settings_protected_words,
            R.string.settings_app_profiles, R.string.settings_collect_examples, R.string.settings_typo_patterns,
            R.string.settings_learned_ranking, R.string.settings_compact_context, R.string.settings_dynamic_touch, R.string.settings_dynamic_touch_apply)
        fun flags(s: KeyboardSettings) = listOf(s.qualityMetrics, s.shadowComparison,
            s.wordBoundarySuggestions, s.abbreviations, s.phraseReview, s.visibleUndo,
            s.protectedWords, s.appProfiles, s.collectExamples, s.typoPatterns,
            s.learnedRanking, s.compactContext, s.dynamicTouch, s.dynamicTouchApply)
        val writes = listOf(prefs::writeQualityMetrics, prefs::writeShadowComparison,
            prefs::writeWordBoundarySuggestions, prefs::writeAbbreviations, prefs::writePhraseReview, prefs::writeVisibleUndo,
            prefs::writeProtectedWords, prefs::writeAppProfiles, prefs::writeCollectExamples, prefs::writeTypoPatterns,
            prefs::writeLearnedRanking, prefs::writeCompactContext, prefs::writeDynamicTouch, prefs::writeDynamicTouchApply)
        writes.forEach { it(false) }
        try {
            for (index in titles.indices) {
                val page = checkNotNull(AdditionalFeatures.forTitle(titles[index])).page
                ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, page)).use { scenario ->
                    scenario.onActivity { activity ->
                        val title = descendants(activity.window.decorView).filterIsInstance<TextView>()
                            .single { it.id == R.id.row_title && it.text.toString() == activity.getString(titles[index]) }
                        val row = title.parent.parent as View
                        assertFalse(row.findViewById<Switch>(R.id.row_checkbox).isChecked)
                        assertTrue(row.performClick())
                    }
                    assertEquals(titles.indices.map { it <= index }, flags(prefs.readSettings()))
                    scenario.recreate()
                    scenario.onActivity { activity ->
                        val title = descendants(activity.window.decorView).filterIsInstance<TextView>()
                            .single { it.id == R.id.row_title && it.text.toString() == activity.getString(titles[index]) }
                        assertTrue((title.parent.parent as View).findViewById<Switch>(R.id.row_checkbox).isChecked)
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
        requireOwnedQualityEmulator()
        val store = QualityStore.get(context)
        assertTrue(awaitResult<Boolean> { store.reset(it) })
        store.configure(true, true, true)
        store.record(QualityEvent.ABBREVIATION_PICKED)
        store.compare(987654, "synthetic", "primary", "experimental")
        store.explicitChoice(987654, "experimental")
        repeat(100) { store.recordAutomatic(AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.APPLIED) }
        repeat(5) { store.recordAutomatic(AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.EXPLICIT_UNDO) }
        store.recordAutomatic(AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.KEPT_ORIGINAL)
        store.recordAutomatic(AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.WINDOW_EXPIRED)
        repeat(99) { store.recordAutomatic(AutomaticQualitySource.JOINT_SHORT, AutomaticQualityOutcome.APPLIED) }
        for (duration in listOf(0L, 49, 50, 99, 100, 249, 250, 499, 500, Long.MAX_VALUE)) store.modelResponseMillis(duration)
        assertEquals(1L, store.snapshot()[QualityEvent.ABBREVIATION_PICKED])
        assertEquals(1L, store.snapshot()[ShadowResult.EXPLICIT_EXPERIMENTAL])
        try {
            ActivityScenario.launch(QualityDashboardActivity::class.java).use { scenario ->
                fun checkDisplay(activity: QualityDashboardActivity) {
                    val actions = activity.findViewById<TextView>(R.id.quality_actions).text
                    assertTrue(actions.contains(activity.getString(R.string.quality_count_format,
                        activity.getString(R.string.quality_abbreviation_picked), 1L)))
                    assertTrue(actions.contains(activity.getString(R.string.quality_count_format,
                        activity.getString(R.string.quality_manual_retype), 0L)))
                    val sourceLabels = activity.resources.getStringArray(R.array.quality_source_labels)
                    assertEquals(14, sourceLabels.size)
                    val sources = activity.findViewById<TextView>(R.id.quality_sources).text
                    assertTrue(sources.contains(activity.getString(R.string.quality_source_counts,
                        sourceLabels[0], 100L, 5L, 1L, 1L,
                        activity.getString(R.string.quality_source_undo_fraction, 5.0))))
                    assertTrue(sources.contains(activity.getString(R.string.quality_source_counts,
                        sourceLabels[4], 99L, 0L, 0L, 0L,
                        activity.getString(R.string.quality_source_insufficient, 99L, 100L))))
                    val modelLabels = activity.resources.getStringArray(R.array.quality_model_latency_labels)
                    assertEquals(5, modelLabels.size)
                    val model = activity.findViewById<TextView>(R.id.quality_model_latency).text
                    for (label in modelLabels) assertTrue(model.contains(
                        activity.getString(R.string.quality_count_format, label, 2L)))
                    assertTrue(activity.findViewById<Button>(R.id.quality_reset).isEnabled)
                }
                scenario.onActivity(::checkDisplay)
                scenario.recreate()
                scenario.onActivity(::checkDisplay)
                scenario.onActivity { it.findViewById<Button>(R.id.quality_reset).performClick() }
                val deadline = android.os.SystemClock.elapsedRealtime() + 10_000
                while ((!store.isReady || store.snapshot() != QualitySnapshot()) &&
                    android.os.SystemClock.elapsedRealtime() < deadline) Thread.sleep(10)
                assertTrue(store.isReady)
                assertEquals(true, store.lastWriteSucceeded)
                assertEquals(QualitySnapshot(), store.snapshot())
                // Refresh observes durable reset even if its UI callback is still queued.
                scenario.onActivity { activity ->
                    activity.findViewById<Button>(R.id.quality_refresh).performClick()
                    val labels = activity.resources.getStringArray(R.array.quality_source_labels)
                    val text = activity.findViewById<TextView>(R.id.quality_sources).text
                    for (label in labels) assertTrue(text.contains(activity.getString(R.string.quality_source_counts,
                        label, 0L, 0L, 0L, 0L, activity.getString(R.string.quality_source_insufficient, 0L, 100L))))
                }
            }
        } finally {
            store.configure(false, false, false)
            assertTrue(awaitResult<Boolean> { store.reset(it) })
        }
        val bytes = File(context.noBackupFilesDir, "typing-quality-v1.txt").readBytes()
        assertFalse(String(bytes).contains("synthetic"))
        assertTrue(String(bytes).startsWith("RUNE_QUALITY_3\n"))
        assertEquals(QualitySnapshot(), QualityCodec.decode(bytes))
    }

    @Test fun realAtomicQualityStorageMigratesV2AndReadsTheFullV3Payload() {
        requireOwnedQualityEmulator()
        val path = File.createTempFile("rune-quality-v3-", ".txt", context.cacheDir)
        try {
            val constructor = Class.forName("io.github.mesteriis.rune.keyboard.smarttyping.quality.AtomicQualityStorage")
                .getDeclaredConstructor(File::class.java).apply { isAccessible = true }
            val storage = constructor.newInstance(path) as QualityStorage
            path.writeText("RUNE_QUALITY_2\n" + (1..20).joinToString("\n") + "\n", Charsets.US_ASCII)
            val migrated = storage.read()!!
            assertEquals((1L..8L).toList(), migrated.events)
            assertEquals((9L..14L).toList(), migrated.candidateResponseBuckets)
            assertEquals((15L..20L).toList(), migrated.shadow)
            assertEquals(List(56) { 0L }, migrated.automaticSources)
            assertEquals(List(5) { 0L }, migrated.modelResponseBuckets)
            val maximum = QualitySnapshot(List(8) { QualityModel.MAX_COUNT }, List(6) { QualityModel.MAX_COUNT },
                List(6) { QualityModel.MAX_COUNT }, List(56) { QualityModel.MAX_COUNT }, List(5) { QualityModel.MAX_COUNT })
            assertTrue(storage.write(maximum))
            assertTrue(path.length() > 1024 && path.length() <= QualityCodec.MAX_BYTES)
            assertEquals(maximum, storage.read())
            assertTrue(storage.write(QualitySnapshot()))
            assertEquals(QualitySnapshot(), storage.read())
        } finally {
            for (suffix in listOf("", ".bak", ".new")) {
                val file = File(path.path + suffix)
                assertTrue(!file.exists() || file.delete())
            }
        }
    }

    @Test fun qualitySourceResourceTablesRetainTheirEnglishAndRussianDimensions() {
        for (locale in listOf("en", "ru")) {
            val configuration = android.content.res.Configuration(context.resources.configuration)
            configuration.setLocale(java.util.Locale(locale))
            val localized = context.createConfigurationContext(configuration)
            val sourceLabels = localized.resources.getStringArray(R.array.quality_source_labels)
            assertEquals(14, sourceLabels.size)
            assertEquals(if (locale == "ru") "Частые опечатки" else "Common confusions", sourceLabels[0])
            assertEquals(5, localized.resources.getStringArray(R.array.quality_model_latency_labels).size)
            val insufficient = localized.getString(R.string.quality_source_insufficient, 99L, 100L)
            assertTrue(insufficient.contains("99 / 100"))
            val observed = localized.getString(R.string.quality_source_undo_fraction, 5.0)
            assertTrue(observed.contains(if (locale == "ru") "5,0%" else "5.0%"))
        }
    }

    private fun requireOwnedQualityEmulator() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
        check(InstrumentationRegistry.getArguments().getString("runeOwnedEmulator") == "q4-counters")
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
