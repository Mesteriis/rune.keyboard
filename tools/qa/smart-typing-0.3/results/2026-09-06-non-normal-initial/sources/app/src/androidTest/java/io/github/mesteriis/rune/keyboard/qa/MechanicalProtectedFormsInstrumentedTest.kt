package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Actual Rune key/popup gestures retain owned context across URL, email and time punctuation. */
@RunWith(AndroidJUnit4::class)
class MechanicalProtectedFormsInstrumentedTest : ImeTestBase() {
    @Test
    fun urlEmailAndTimeKeepPunctuationAndOrdinaryDeleteAcrossBinder() {
        // Switching layers inside a token discards ownership and would make exclusions vacuous.
        driver.setNumberRowThroughSettings(enabled = true)
        for (token in listOf("https://example.com/path", "name@example", "12:30")) {
            driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
            driver.launchComposingQa()
            "hello".forEach { driver.tapKey(it.toString()) }
            driver.tapKey(","); driver.tapKey("w")
            driver.awaitFieldText(FIELD, "hello, w") // Enabled mechanical positive control.
            driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext
                .getString(io.github.mesteriis.rune.keyboard.R.string.key_space))
            val prefix = "hello, w "
            driver.awaitFieldText(FIELD, prefix)
            val initial = stats()
            val keys = keyboardSnapshot()
            var typed = prefix
            for (character in token) {
                when (character) {
                    ':' -> alternate(",", ":", typed)
                    '/', '@' -> alternate(".", character.toString(), typed)
                    else -> driver.tapKey(character.toString())
                }
                typed += character
                driver.awaitFieldText(FIELD, typed)
            }
            driver.tapKey(","); driver.awaitFieldText(FIELD, "$typed,")
            val beforeLetter = stats()
            driver.tapKey("w"); driver.awaitFieldText(FIELD, "$typed,w")
            val afterLetter = stats()
            assertEquals(beforeLetter.getValue("compose") + 1, afterLetter.getValue("compose"))
            assertEquals(beforeLetter.getValue("commit"), afterLetter.getValue("commit"))
            driver.tapDelete(); driver.awaitFieldText(FIELD, "$typed,")
            driver.tapDelete(); driver.awaitFieldText(FIELD, typed)
            assertEquals(initial.getValue("connections"), stats().getValue("connections"))
            assertSameKeys(keys, keyboardSnapshot())
            for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
                assertEquals("Unexpected editor payload read", 0, stats().getValue(name))
            }
        }
    }

    private fun alternate(key: String, symbol: String, unchanged: String) {
        var touch = driver.touchDown(driver.keyByText(key))
        var released = false
        try {
            val cell = checkNotNull(driver.device.wait(Until.findObject(By.desc(symbol)),
                ImeTestDriver.WAIT_MILLIS)) { "Required actual alternate cell is unavailable" }
            driver.awaitFieldText(FIELD, unchanged) // No early fallback commit while the key is held.
            val bounds = cell.visibleBounds
            check(!bounds.isEmpty) { "Alternate has no visible bounds" }
            touch = driver.moveTouch(touch, bounds.exactCenterX(), bounds.exactCenterY())
            driver.releaseTouch(touch)
            released = true
        } finally {
            if (!released) driver.cancelTouch(touch)
        }
        driver.device.waitForIdle()
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('='); name to value.toInt()
    }

    private companion object { const val FIELD = "qa_composing_text" }
}
