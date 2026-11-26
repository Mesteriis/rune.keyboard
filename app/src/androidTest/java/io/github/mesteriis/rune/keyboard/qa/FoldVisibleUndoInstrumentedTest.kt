package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.Build
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.intelligence.inference.LifecycleModelInferenceService as Remote
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/** Explicit physical Fold test; injected public model replies never use the owner's model. */
class FoldVisibleUndoInstrumentedTest {
    private val driver = ImeTestDriver()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private var prepared = false
    private var stores: Map<String, Map<String, String>>? = null

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        assumeTrue("Explicit physical Fold test required", Build.MODEL.startsWith("SM-F") &&
            args.getString("allowPhysicalDevice") == "true" && args.getString("runeFailureArtifacts") == "false")
        stores = personalStoreSnapshot(context).filterKeys { it != "typing-diagnostics" }
        prepared = true
        driver.setUp(privateQa = true)
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        assertTrue(edit.commit())
        KeyboardPreferences(context).writeVisibleUndo(true)
    }

    @After fun restore() {
        try {
            stores?.let { assertEquals("Synthetic QA changed personal stores", it,
                personalStoreSnapshot(context).filterKeys { key -> key != "typing-diagnostics" }) }
        } finally { if (prepared) driver.tearDown() }
    }

    @Test fun canonicalUndoSurvivesNextLetter() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
        "я москва".forEach { if (it == ' ') space() else driver.tapKey(it.toString()) }
        checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "Москва"))), 30_000))
        space(); driver.awaitFieldText("qa_composing_text", "я Москва ")
        driver.tapKey("д"); driver.awaitFieldText("qa_composing_text", "я Москва д")
        undo("москва"); driver.awaitFieldText("qa_composing_text", "я москва д")
        noReadback()
    }

    @Test fun readyModelUndoSurvivesNextLetter() = modelUndo(false)
    @Test fun lateModelUndoSurvivesNextLetter() = modelUndo(true)

    private fun modelUndo(late: Boolean) {
        LiveFakeModelBinderFixture.install(driver).use { fixture ->
            val token = fixture.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
            if (late) fixture.spaceThenReleaseWithinGrace(token) else {
                fixture.release(); fixture.awaitCompletion(token, Remote.MODE_PUBLIC_CORRECTION)
                fixture.awaitRanking(token, 1); fixture.space()
            }
            fixture.editor("a hello ", 8, 7, 8)
            driver.tapKey("w"); fixture.editor("a hello w", 9, 7, 9)
            undo("helllo"); fixture.editor("a helllo w", 10, 8, 10)
            noReadback()
        }
    }

    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun undo(original: String) {
        checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_undo, original))),
            ImeTestDriver.WAIT_MILLIS)).click()
    }
    private fun noReadback() {
        val stats = checkNotNull(driver.device.wait(Until.findObject(
            By.res(context.packageName, "qa_composing_stats")), 3000)).text.split(' ')
            .associate { val (key, value) = it.split('='); key to value.toInt() }
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor payload read: $key", 0, stats.getValue(key))
    }
}
