package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.Build
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import androidx.test.uiautomator.StaleObjectException
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.StartingLanguage
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assume.assumeTrue
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test

/** Uses the isolated QA editor; physical Fold requires explicit opt-in. */
class ExpandedCandidatesInstrumentedTest {
    private val driver = ImeTestDriver()
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private var stores: Map<String, Map<String, String>>? = null
    private var privateInput = false
    @get:Rule val failureArtifacts = ImeFailureArtifacts(driver) {
        android.os.Build.HARDWARE in setOf("ranchu", "goldfish")
    }

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        val emulator = Build.HARDWARE in setOf("ranchu", "goldfish")
        val fold = Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true" &&
            args.getString("runeFailureArtifacts") == "false"
        assumeTrue("Owned emulator or explicitly authorized Fold required", emulator || fold)
        privateInput = fold || emulator && args.getString("runeExpandedPrivateFixture") == "true"
        stores = personalStoreSnapshot(context).let { snapshot ->
            if (privateInput) snapshot else snapshot.filterKeys { it != "typing-diagnostics" }
        }
        driver.setUp(privateQa = privateInput)
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        assertTrue(edit.commit())
        driver.configureSmartTyping(AutocorrectionMode.SUGGESTIONS, true, mechanical = false, doubleSpace = false)
        if (!privateInput) driver.launchComposingQa()
    }

    @After fun preservePersonalStores() {
        stores?.let { before ->
            assertEquals("Synthetic QA changed personal stores", before,
                personalStoreSnapshot(context).let { snapshot ->
                    if (privateInput) snapshot else snapshot.filterKeys { it != "typing-diagnostics" }
                })
        }
    }

    private fun clickExpandWhenStable() {
        val deadline = SystemClock.uptimeMillis() + 30_000
        val selector = By.desc(context.getString(R.string.candidate_expand))
        do {
            val expand = driver.device.findObject(selector)
            if (expand != null) {
                try {
                    expand.click()
                    return
                } catch (_: StaleObjectException) {
                    // Node disappeared before the click could be dispatched; reacquire it.
                }
            }
            SystemClock.sleep(25)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("Expanded candidate control did not become stable")
    }

    @Test fun hiddenCandidateCanBeExplicitlySelectedInRealIme() {
        "addess".forEach { driver.tapKey(it.toString()) }
        clickExpandWhenStable()
        val hidden = driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "access"))), 5_000)
        assertNotNull(hidden)
        hidden.click()
        driver.awaitFieldText("qa_composing_text", "access")
    }

    @Test fun russianMetroIsSelectableFromExpandedSuggestions() {
        assumeTrue("The metro candidate ordering is qualified in an ordinary editor", !privateInput)
        KeyboardPreferences(context).apply {
            writeEnabledLanguages(listOf(KeyboardLanguage.RUSSIAN))
            writeStartingLanguage(StartingLanguage.Fixed(KeyboardLanguage.RUSSIAN))
            writeManualCandidateExpansion(true)
        }
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        driver.launchComposingQa(mode = if (privateInput) "private" else "accept", language = KeyboardLanguage.RUSSIAN)
        "мето".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText("qa_composing_text", "мето")
        clickExpandWhenStable()
        val metro = driver.device.wait(
            Until.findObject(By.desc(context.getString(R.string.candidate_correction, "метро"))), 5_000)
        assertNotNull(metro)
        metro.click()
        driver.awaitFieldText("qa_composing_text", "метро")
    }

    @Test fun typingOutsideExpandedRowClosesItWithoutSelectingOldCandidate() {
        "addess".forEach { driver.tapKey(it.toString()) }
        clickExpandWhenStable()
        val oldSuggestion = By.desc(context.getString(R.string.candidate_correction, "access"))
        assertNotNull(driver.device.wait(Until.findObject(oldSuggestion), 5_000))
        driver.tapKey("m")
        driver.awaitFieldText("qa_composing_text", "addessm")
        assertTrue(driver.device.wait(Until.gone(oldSuggestion), 5_000))
    }

    @Test fun backClosesExpandedRowAndKeepsTypingSession() {
        "addess".forEach { driver.tapKey(it.toString()) }
        clickExpandWhenStable()
        val hidden = By.desc(context.getString(R.string.candidate_correction, "access"))
        assertNotNull(driver.device.wait(Until.findObject(hidden), 5_000))
        assertTrue(driver.device.pressBack())
        assertTrue(driver.device.wait(Until.gone(hidden), 5_000))
        driver.awaitFieldText("qa_composing_text", "addess")
        clickExpandWhenStable()
        assertNotNull(driver.device.wait(Until.findObject(hidden), 5_000))
    }
}
