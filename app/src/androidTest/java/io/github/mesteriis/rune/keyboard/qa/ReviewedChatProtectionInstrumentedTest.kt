package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.Build
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.After
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test

/** Previously disclosed public chat controls, exercised via the real IME. */
class ReviewedChatProtectionInstrumentedTest {
    private val driver = ImeTestDriver()
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private var stores: Map<String, Map<String, String>>? = null

    @get:Rule val failureArtifacts = ImeFailureArtifacts(driver) {
        Build.HARDWARE in setOf("ranchu", "goldfish")
    }

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        val emulator = Build.HARDWARE in setOf("ranchu", "goldfish")
        val fold = Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true" &&
            args.getString("runeFailureArtifacts") == "false"
        assumeTrue("Owned emulator or explicitly authorized Fold required", emulator || fold)
        stores = personalStoreSnapshot(context).filterKeys { it != "typing-diagnostics" }
        driver.setUp()
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        assertTrue(edit.commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
    }

    @After fun preservePersonalStores() {
        stores?.let { before ->
            org.junit.Assert.assertEquals("Synthetic QA changed personal stores", before,
                personalStoreSnapshot(context).filterKeys { it != "typing-diagnostics" })
        }
    }

    @Test fun compactChatOriginalIsKeptAtSpace() = exercise("том натянул на себя", "бадлон", "баллон")

    @Test fun contextualChatOriginalIsKeptAtSpace() = exercise("выдай мне", "админку", "спинку")

    @Test fun pairingChatOriginalIsKeptAtSpace() = exercise("это неканоничный", "пейринг", "рейтинг")

    @Test fun toxicChatOriginalIsKeptAtSpace() = exercise("ненавижу", "токсиков", "трусиков")

    @Test fun bannedChatOriginalIsKeptAtSpace() = exercise("читера", "забанили", "заманили")

    @Test fun colloquialYoOriginalIsKeptAtSpace() = exercise("а твоя лошадка вот так", "могёт", "могут")

    @Test fun slangChatOriginalIsKeptAtSpace() = exercise("ты", "ебобо", "бобо", requireExactSuggestion = false)

    @Test fun wishesChatOriginalIsKeptAtSpace() = exercise("твои", "хотелки", "хотели")

    @Test fun inviteChatOriginalIsKeptAtSpace() = exercise("апрувни", "инвайт", "инсайт")

    @Test fun protectedOriginalStillAllowsManualSuggestion() {
        for (character in "выдай мне админку") {
            if (character == ' ') driver.tapKeyByDescription(context.getString(R.string.key_space))
            else driver.tapKey(character.toString())
        }
        driver.awaitFieldText("qa_composing_text", "выдай мне админку")
        val suggestion = driver.device.wait(Until.findObject(
            By.desc(context.getString(R.string.candidate_correction, "спинку"))), 30_000)
        assertNotNull(suggestion)
        suggestion!!.click()
        driver.awaitFieldText("qa_composing_text", "выдай мне спинку")
    }

    @Test fun protectedSlangAllowsContextualManualSuggestion() {
        for (character in "ты ебобо") {
            if (character == ' ') driver.tapKeyByDescription(context.getString(R.string.key_space))
            else driver.tapKey(character.toString())
        }
        driver.awaitFieldText("qa_composing_text", "ты ебобо")
        val suggestion = driver.device.wait(Until.findObject(
            By.desc(context.getString(R.string.candidate_correction, "бобо"))), 30_000)
        assertNotNull(suggestion)
        suggestion!!.click()
        driver.awaitFieldText("qa_composing_text", "ты бобо")
        driver.tapKeyByDescription(context.getString(R.string.key_space))
        driver.awaitFieldText("qa_composing_text", "ты бобо ")
    }

    private fun exercise(prefix: String, original: String, suggestion: String, requireExactSuggestion: Boolean = true) {
        fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
        for (character in "$prefix $original") {
            when (character) {
                ' ' -> space()
                'ё' -> {
                    val bounds = driver.characterKey("е", "Е").visibleBounds
                    assertTrue(driver.device.swipe(bounds.centerX(), bounds.centerY(),
                        bounds.centerX(), bounds.centerY(), 160))
                }
                else -> driver.tapKey(character.toString())
            }
        }
        val before = "$prefix $original"
        driver.awaitFieldText("qa_composing_text", before)
        val selector = if (requireExactSuggestion)
            By.desc(context.getString(R.string.candidate_correction, suggestion))
        else By.descStartsWith(context.getString(R.string.candidate_correction, ""))
        assertNotNull("A correction candidate must be available before Space",
            driver.device.wait(Until.findObject(selector), 30_000))
        SystemClock.sleep(350)
        space()
        driver.awaitFieldText("qa_composing_text", "$before ")
    }
}
