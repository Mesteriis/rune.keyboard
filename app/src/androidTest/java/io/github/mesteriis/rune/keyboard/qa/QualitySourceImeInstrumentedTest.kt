package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.Build
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.smarttyping.quality.*
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Actual IME/editor source accounting; mutating fixtures are restricted to the owned emulator. */
class QualitySourceImeInstrumentedTest {
    @Test fun actualCorrectionAndUndoCountOnlyAcknowledgedEligibleActions() {
        check(Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
        check(InstrumentationRegistry.getArguments().getString("runeOwnedEmulator") == "q4-counters")
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val driver = ImeTestDriver()
        var store: QualityStore? = null
        try {
            driver.setUp()
            val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
            for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
                SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
                SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES))
                edit.putBoolean(key, false)
            check(edit.putBoolean(SettingsCodec.KEY_QUALITY_METRICS, true).commit())
            driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false,
                doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
            val metrics = QualityStore.get(context).also { store = it }
            reset(metrics)
            driver.launchComposingQa()
            for (key in "teh") driver.tapKey(key.toString())
            driver.awaitFieldText("qa_composing_text", "teh")
            assertTrue(driver.device.wait(Until.hasObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
            assertEquals(0L, metrics.snapshot().automaticSources.sum())
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            driver.awaitFieldText("qa_composing_text", "the ")
            await { metrics.snapshot()[AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.APPLIED] == 1L }
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "teh")
            await { metrics.snapshot()[AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.EXPLICIT_UNDO] == 1L }
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "te")
            assertEquals(2L, metrics.snapshot().automaticSources.sum())
            assertEquals(1L, metrics.snapshot()[QualityEvent.AUTOMATIC_APPLIED])
            assertEquals(1L, metrics.snapshot()[QualityEvent.EXPLICIT_UNDO])

            // Reset while the editor still owns its correction: Undo must work, but its
            // application belongs to the old collection period and cannot supply a new label.
            reset(metrics)
            driver.launchComposingQa()
            for (key in "teh") driver.tapKey(key.toString())
            driver.awaitFieldText("qa_composing_text", "teh")
            assertTrue(driver.device.wait(Until.hasObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            driver.awaitFieldText("qa_composing_text", "the ")
            await { metrics.snapshot()[AutomaticQualitySource.COMMON_CONFUSION, AutomaticQualityOutcome.APPLIED] == 1L }
            reset(metrics)
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "teh")
            instrumentation.waitForIdleSync()
            assertEquals(0L, metrics.snapshot().automaticSources.sum())
            assertEquals(1L, metrics.snapshot()[QualityEvent.EXPLICIT_UNDO])

            for (mode in listOf("reject", "private")) {
                reset(metrics)
                driver.launchComposingQa(mode)
                for (key in "teh") driver.tapKey(key.toString())
                driver.tapKeyByDescription(context.getString(R.string.key_space))
                instrumentation.waitForIdleSync()
                assertEquals(mode, 0L, metrics.snapshot().automaticSources.sum())
                assertEquals(mode, 0L, metrics.snapshot()[QualityEvent.AUTOMATIC_APPLIED])
            }
        } finally {
            try { store?.let(::reset) } finally { driver.tearDown() }
        }
    }

    private fun reset(store: QualityStore) {
        val done = CountDownLatch(1)
        var saved = false
        store.reset { saved = it; done.countDown() }
        assertTrue(done.await(10, TimeUnit.SECONDS) && saved)
        assertEquals(QualitySnapshot(), store.snapshot())
    }

    private fun await(condition: () -> Boolean) {
        val deadline = SystemClock.elapsedRealtime() + 5_000
        while (!condition() && SystemClock.elapsedRealtime() < deadline) Thread.sleep(10)
        assertTrue(condition())
    }
}
