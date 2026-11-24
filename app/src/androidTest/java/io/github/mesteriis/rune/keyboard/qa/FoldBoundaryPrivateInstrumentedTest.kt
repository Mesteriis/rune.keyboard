package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.Build
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsAndroidPreferences
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsPreferences
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

internal fun requireOrdinaryDiagnosticsSafety(preferences: DiagnosticsPreferences, allowRotation: Boolean) {
    check(!(preferences.metadata || preferences.text) || allowRotation) {
        "Ordinary QA with diagnostics requires a verified owner backup and explicit rotation opt-in"
    }
}

/** Public phrases in an isolated QA editor, with explicit physical-device opt-in. */
class FoldBoundaryPrivateInstrumentedTest {
    private val driver = ImeTestDriver()
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private var prepared = false
    private var ordinary = false
    private var stores: Map<String, Map<String, String>>? = null

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        val emulator = Build.HARDWARE in setOf("ranchu", "goldfish") &&
            args.getString("runeBoundaryPrivateFixture") == "true"
        val fold = Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true" &&
            args.getString("runeFailureArtifacts") == "false"
        assumeTrue("Explicit private fixture opt-in required", emulator || fold)
        ordinary = args.getString("runeBoundaryOrdinaryFixture") == "true"
        if (ordinary) {
            val diagnostics = DiagnosticsPreferences.decode(DiagnosticsAndroidPreferences(context).read())
            requireOrdinaryDiagnosticsSafety(diagnostics, args.getString("runeAllowDiagnosticRotation") == "true")
        }
        stores = personalStoreSnapshot(context).let { snapshot ->
            if (ordinary) snapshot.filterKeys { it != "typing-diagnostics" } else snapshot
        }
        prepared = true
        driver.setUp(privateQa = true)
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        assertTrue(edit.commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false, doubleSpace = false)
        driver.launchComposingQa(mode = if (ordinary) "accept" else "private", language = KeyboardLanguage.RUSSIAN)
    }

    @After fun restore() {
        try {
            if (prepared) driver.tearDown()
        } finally {
            stores?.let { before ->
                val after = personalStoreSnapshot(context).let { snapshot ->
                    if (ordinary) snapshot.filterKeys { it != "typing-diagnostics" } else snapshot
                }
                assertEquals("Synthetic QA changed personal stores", before, after)
            }
        }
    }

    @Test fun ambiguousAbbreviationBeforePeriod() = abbreviation(false)
    @Test fun ambiguousAbbreviationBeforeColon() = abbreviation(true)
    @Test fun correctionAndExactUndoBeforePeriod() = correction(false)
    @Test fun correctionAndExactUndoBeforeColon() = correction(true)

    @Test fun reviewPhrasePreservesAbbreviationAndUndoesCorrection() {
        for (character in "живу") driver.tapKey(character.toString(), character.uppercase())
        space()
        driver.tapKey("в", "В"); space()
        for (character in "спб") driver.tapKey(character.toString(), character.uppercase())
        driver.tapKey("."); driver.awaitFieldText("qa_composing_text", "живу в спб.")
        space()
        for (character in "смотруть") driver.tapKey(character.toString(), character.uppercase())
        driver.awaitFieldText("qa_composing_text", "живу в спб. смотруть")
        candidate("смотреть")
        driver.tapKey("."); driver.awaitFieldText("qa_composing_text", "живу в спб. смотреть.")
        driver.tapDelete(); driver.awaitFieldText("qa_composing_text", "живу в спб. смотруть")
        noReadback()
    }

    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))

    private fun abbreviation(colon: Boolean) {
        driver.tapKey("И", "и"); driver.tapKey("н"); driver.tapKey("н")
        driver.awaitFieldText("qa_composing_text", "инн")
        candidate("Инн")
        boundary(colon)
        driver.awaitFieldText("qa_composing_text", if (colon) "инн:" else "инн.")
        driver.tapDelete(); driver.awaitFieldText("qa_composing_text", "инн")
        noReadback()
    }

    private fun correction(colon: Boolean) {
        "смотруть".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText("qa_composing_text", "смотруть")
        candidate("смотреть")
        boundary(colon)
        driver.awaitFieldText("qa_composing_text", if (colon) "смотреть:" else "смотреть.")
        driver.tapDelete(); driver.awaitFieldText("qa_composing_text", "смотруть")
        noReadback()
    }

    private fun boundary(colon: Boolean) {
        if (colon) driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        driver.tapKey(if (colon) ":" else ".")
    }

    private fun candidate(text: String) {
        checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, text))),
            ImeTestDriver.WAIT_MILLIS)) { "Expected public candidate unavailable" }
    }

    private fun noReadback() {
        val stats = checkNotNull(driver.device.wait(Until.findObject(By.res(context.packageName, "qa_composing_stats")), 3000))
            .text.split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor payload read: $key", 0, stats.getValue(key))
    }
}
