package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.Assert.*
import org.junit.Test

/** Fixed public words; the real IME, packed ranker, worker and remote editor own this flow. */
class NeighborRecoveryLiveInstrumentedTest : ImeTestBase() {
    @Test fun twoNeighborErrorsCorrectAndUndoKeepsTheNextWord() = exercise("палецшего", true)
    @Test fun threeNeighborErrorsCorrectWithHiddenStripAndBackspaceRestoresSource() = exercise("машефшегш", false)

    private fun exercise(typed: String, strip: Boolean) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
            .putBoolean(SettingsCodec.KEY_VISIBLE_UNDO, true)
            .putBoolean(SettingsCodec.KEY_PERSONAL_LEARNING, false)
            .putBoolean(SettingsCodec.KEY_TOUCH_PERSONALIZATION, false)
            .putBoolean(SettingsCodec.KEY_COLLECT_EXAMPLES, false).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, strip,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
        fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
        for (character in "он не дает ни $typed") {
            if (character == ' ') space() else driver.tapKey(character.toString())
        }
        // A ready correction is measured separately from the 15 ms rapid-touch delivery fixture.
        SystemClock.sleep(350)
        space()
        driver.awaitFieldText("qa_composing_text", "он не дает ни малейшего ")
        if (strip) {
            "след".forEach { driver.tapKey(it.toString()) }
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "он не дает ни малейшего сле")
            val undo = driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_undo, typed))), 5000)
            assertNotNull(undo); undo!!.click()
            driver.awaitFieldText("qa_composing_text", "он не дает ни $typed сле")
        } else {
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "он не дает ни $typed")
        }
        val stats = driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))
            .text.split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor readback", 0, stats.getValue(name))
        assertEquals(stats.getValue("selectionStart"), stats.getValue("selectionEnd"))
    }
}
