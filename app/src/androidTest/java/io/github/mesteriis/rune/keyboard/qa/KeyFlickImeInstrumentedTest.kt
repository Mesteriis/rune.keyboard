package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Rect
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.*
import org.junit.Assert.*
import org.junit.Test

class KeyFlickImeInstrumentedTest : ImeTestBase() {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val preferences get() = KeyboardPreferences(instrumentation.targetContext)

    @Test fun upwardDriftInsideKeyCommitsThroughTheRealEditor() {
        preferences.writeKeyFlicks(true)
        preferences.writeDynamicTouch(false)
        preferences.writeDynamicTouchApply(false)
        preferences.writePersonalLearning(false)
        preferences.writeTouchPersonalization(false)
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, false, mechanical = false, doubleSpace = false)
        instrumentation.waitForIdleSync()
        preferences.readSettings().let { configured ->
            assertTrue(configured.keyFlicks)
            assertEquals(AutocorrectionMode.OFF, configured.autocorrectionMode)
            assertFalse(configured.dynamicTouch)
            assertFalse(configured.dynamicTouchApply)
            assertFalse(configured.personalLearning)
            assertFalse(configured.touchPersonalization)
        }
        driver.launchComposingQa()
        val bounds = Rect(driver.characterKey("q", "Q").visibleBounds)
        val held = driver.touchDown(bounds)
        var released = false
        try {
            val moved = driver.moveTouch(
                held,
                bounds.exactCenterX(),
                bounds.exactCenterY() - maxOf(10f, bounds.height() * .2f),
            )
            driver.releaseTouch(moved)
            released = true
        } finally {
            if (!released) driver.cancelTouch(held)
        }
        driver.awaitFieldText("qa_composing_text", "q")
    }

    @Test fun allThemesAndLanguagesCommitSecondaryCharactersWithoutTheBaseLetter() {
        preferences.writeKeyFlicks(true)
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, false, mechanical = false, doubleSpace = false)
        for (theme in KeyboardTheme.entries) {
            preferences.writeKeyboardTheme(theme)
            instrumentation.waitForIdleSync()
            driver.launchComposingQa()
            flick("q")
            driver.awaitFieldText("qa_composing_text", "1")
            flick("a")
            driver.awaitFieldText("qa_composing_text", "1@")
            flick(".")
            driver.awaitFieldText("qa_composing_text", "1@?")
            driver.tapKey("w")
            driver.awaitFieldText("qa_composing_text", "1@?w")
        }
        for ((language, key, symbol) in listOf(
            Triple(KeyboardLanguage.RUSSIAN, "в", "₽"),
            Triple(KeyboardLanguage.SPANISH, "ñ", "¿"),
        )) {
            preferences.writeEnabledLanguages(listOf(language))
            preferences.writeStartingLanguage(StartingLanguage.Fixed(language))
            instrumentation.waitForIdleSync()
            driver.launchComposingQa(language = language)
            flick(key)
            driver.awaitFieldText("qa_composing_text", symbol)
        }
    }

    @Test fun disablingThroughSettingsRemovesTheGestureAndPersists() {
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, false, mechanical = false, doubleSpace = false)
        preferences.writeKeyFlicks(true)
        instrumentation.waitForIdleSync()
        driver.launchSettings()
        driver.settingsRow(R.string.settings_key_flicks).click()
        instrumentation.waitForIdleSync()
        assertFalse(preferences.readSettings().keyFlicks)
        driver.launchComposingQa()
        driver.tapKey("x")
        driver.awaitFieldText("qa_composing_text", "x")
        flick("q") // A full downward escape on a plain key cancels instead of entering 1.
        driver.awaitFieldText("qa_composing_text", "x")
        driver.tapKey("q")
        driver.awaitFieldText("qa_composing_text", "xq")
    }

    @Test fun holdingLettersStillSelectsAccentsAndYo() {
        preferences.writeKeyFlicks(true)
        driver.configureSmartTyping(AutocorrectionMode.OFF, false, mechanical = false, doubleSpace = false)
        for ((language, letter, alternate) in listOf(
            Triple(KeyboardLanguage.RUSSIAN, "е", "ё"),
            Triple(KeyboardLanguage.SPANISH, "a", "á"),
        )) {
            preferences.writeEnabledLanguages(listOf(language))
            preferences.writeStartingLanguage(StartingLanguage.Fixed(language))
            instrumentation.waitForIdleSync()
            driver.launchComposingQa(language = language)
            val bounds = driver.characterKey(letter, letter.uppercase()).visibleBounds
            assertTrue(driver.device.swipe(bounds.centerX(), bounds.centerY(), bounds.centerX(), bounds.centerY(), 160))
            instrumentation.waitForIdleSync()
            driver.awaitFieldText("qa_composing_text", alternate)
        }
    }

    private fun flick(label: String) {
        driver.device.waitForIdle()
        val nodes = driver.device.findObjects(By.text(label)) + driver.device.findObjects(By.text(label.uppercase()))
        val key = checkNotNull(nodes.maxByOrNull { it.visibleBounds.centerY() }) { "Missing flick key $label" }
        val bounds = Rect(key.visibleBounds)
        assertTrue(driver.device.swipe(bounds.centerX(), bounds.centerY(), bounds.centerX(),
            bounds.centerY() + (bounds.height() * .8f).toInt(), 10))
        instrumentation.waitForIdleSync()
    }
}
