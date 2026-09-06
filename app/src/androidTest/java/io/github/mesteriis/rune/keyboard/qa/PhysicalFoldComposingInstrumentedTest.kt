package io.github.mesteriis.rune.keyboard.qa

import android.os.Bundle
import android.os.SystemClock
import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import android.widget.TextView
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Opt in with -e runePhysicalFold true, starting on the awake cover display. Physically unfold
 * after READY_TO_UNFOLD. This observes a real size transition; it never sets device state,
 * rotates the display, recreates the Activity, refocuses, or seeds/restores editor text itself.
 * One EN/letters/manual-shift transition only, not the full fold matrix or model validation.
 */
@RunWith(AndroidJUnit4::class)
class PhysicalFoldComposingInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val driver = ImeTestDriver()

    @Test
    fun physicalUnfoldPreservesEditorAndVisualStateWithoutReplayingOwnedComposition() {
        // Deliberately do not inherit ImeTestBase: ordinary CI must skip before settings/setup,
        // and physical runs must not capture arbitrary screen/window contents on failure.
        assumeTrue("Requires an operator and a physical Fold on its cover display",
            InstrumentationRegistry.getArguments().getString("runePhysicalFold") == "true")
        try {
            driver.setUp()
            driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false,
                doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
            driver.launchComposingQa()
            driver.tapKey("a")
            driver.tapKey("b")
            driver.awaitFieldText(FIELD, "ab")
            driver.tapKeyByDescription(instrumentation.targetContext.getString(R.string.key_shift))
            driver.assertKeyVisible("C")
            awaitStats { it["start"] == 0 && it["end"] == 2 &&
                it["selectionStart"] == 2 && it["selectionEnd"] == 2 }
            val before = stats()
            assertEquals(2, before.getValue("compose"))
            assertTrue(before.getValue("connections") > 0)
            assertNoPayloadReads(before)
            val visualBefore = visibleKeys()
            val serviceBefore = imeService()
            val dimensionsBefore = dimensions()
            assertTrue("Configuration dimensions must be available", dimensionsBefore.first > 0 &&
                dimensionsBefore.second > 0)

            instrumentation.sendStatus(0, Bundle().apply {
                putString("stream", "\nREADY_TO_UNFOLD\n")
            })
            val deadline = SystemClock.uptimeMillis() + 120_000L
            var expanded = false
            do {
                val current = dimensions()
                // Area increase and a larger short edge reject an ordinary orientation swap.
                // Operator/device provenance establishes that this is physical unfolding.
                expanded = minOf(current.first, current.second) >
                    minOf(dimensionsBefore.first, dimensionsBefore.second) &&
                    current.first.toLong() * current.second >
                    dimensionsBefore.first.toLong() * dimensionsBefore.second * 13 / 10
                if (expanded) break
                SystemClock.sleep(100)
            } while (SystemClock.uptimeMillis() < deadline)
            if (!expanded) {
                instrumentation.sendStatus(0, Bundle().apply {
                    putString("stream", "\nFOLD_UNFOLD_NOT_OBSERVED\n")
                })
                assumeTrue("No cover-to-inner configuration expansion within 120 seconds. " +
                    "Continue once fold transition is ready.", false)
            }
            assertTrue("Rune keyboard must return without refocusing the editor", driver.device.wait(
                Until.hasObject(By.desc(instrumentation.targetContext.getString(R.string.key_delete))),
                ImeTestDriver.WAIT_MILLIS))
            driver.device.waitForIdle()
            instrumentation.waitForIdleSync()
            driver.awaitFieldText(FIELD, "ab")
            awaitStats { it["start"] == -1 && it["end"] == -1 &&
                it["selectionStart"] == 2 && it["selectionEnd"] == 2 }
            instrumentation.sendStatus(0, Bundle().apply {
                // Instance identity only: no EditorInfo, package, editor text or object dump.
                putString("stream", "\nSAME_IME_SERVICE=${serviceBefore === imeService()}\n")
            })
            assertEquals("Language, layer and shift presentation must survive unfold",
                visualBefore, visibleKeys())

            // Activity recreation can reset wrapper counters; only compare command deltas
            // within the post-transition editor, never pretend they are process-wide totals.
            val after = stats()
            assertTrue(after.getValue("connections") > 0)
            assertNoPayloadReads(after)
            driver.tapKey("C")
            driver.awaitFieldText(FIELD, "abC")
            awaitStats { it["selectionStart"] == 3 && it["selectionEnd"] == 3 &&
                ((it["start"] == 2 && it["end"] == 3) ||
                    (it["start"] == -1 && it["end"] == -1)) }
            val typed = stats()
            assertTrue("The next real key must deliver a fresh editor command",
                typed.getValue("compose") + typed.getValue("commit") >
                    after.getValue("compose") + after.getValue("commit"))
            assertEquals(after.getValue("connections"), typed.getValue("connections"))
            driver.tapDelete()
            driver.awaitFieldText(FIELD, "ab")
            awaitStats { it["selectionStart"] == 2 && it["selectionEnd"] == 2 }
            assertNoPayloadReads(stats())
        } finally {
            driver.tearDown()
        }
    }

    private fun dimensions(): Pair<Int, Int> {
        val configuration = instrumentation.targetContext.resources.configuration
        return configuration.screenWidthDp to configuration.screenHeightDp
    }

    private fun visibleKeys(): List<Triple<String, String, Boolean>> {
        val snapshot = keyboardSnapshot()
        var result: List<Triple<String, String, Boolean>> = emptyList()
        instrumentation.runOnMainSync {
            result = snapshot.keys.map { key ->
                Triple((key as TextView).text.toString(), key.contentDescription?.toString().orEmpty(),
                    key.isSelected)
            }
        }
        return result
    }

    private fun imeService(): InputMethodService {
        val snapshot = keyboardSnapshot()
        var service: InputMethodService? = null
        instrumentation.runOnMainSync {
            var context = snapshot.keyboard.context
            while (context is ContextWrapper && context !is InputMethodService) {
                val base = context.baseContext
                check(base !== context) { "Keyboard context wrapper cycle" }
                context = base
            }
            service = context as? InputMethodService
        }
        return checkNotNull(service) { "Rune keyboard must belong to its IME service" }
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))) {
        "Owned QA editor stats must remain visible"
    }.text.orEmpty().split(' ').associate {
        val (key, value) = it.split('=')
        key to value.toInt()
    }

    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!predicate(stats()) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(50)
        assertTrue("Owned editor span/selection did not settle", predicate(stats()))
    }

    private fun assertNoPayloadReads(observed: Map<String, Int>) {
        for (counter in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor payload read: $counter", 0, observed.getValue(counter))
        }
    }

    private companion object {
        const val FIELD = "qa_composing_text"
    }
}
