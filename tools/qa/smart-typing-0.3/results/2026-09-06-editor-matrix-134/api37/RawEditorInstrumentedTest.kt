package io.github.mesteriis.rune.keyboard.qa

import android.view.View
import android.view.ViewGroup
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.ui.CandidateStripView
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Public text in the debug :qa_editor; observes actual Binder key delivery, never a fake scorer. */
@RunWith(AndroidJUnit4::class)
class RawEditorInstrumentedTest : ImeTestBase() {
    @Test fun typeNullUsesRawKeysWithoutCompositionCorrectionsStripOrReadback() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = true, doubleSpace = true)
        driver.launchComposingQa("raw")
        for (letter in "helllo") driver.tapKey(letter.toString())
        space(); driver.tapKey("."); space()
        driver.awaitFieldText(FIELD, "helllo . ")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "helllo .")
        driver.device.waitForIdle()

        val counts = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME,
            "qa_composing_stats"))).text.orEmpty().split(' ').associate {
            val (name, count) = it.split('='); name to count.toInt()
        }
        assertTrue("No raw key downs reached the remote editor", counts.getValue("keyDown") >= 10)
        assertEquals(counts.getValue("keyDown"), counts.getValue("keyUp"))
        assertEquals(1, counts.getValue("deleteKeyDown"))
        for (counter in listOf("compose", "region", "commit", "before", "after", "selected",
            "extracted", "caps", "surrounding", "snapshot")) {
            assertEquals("TYPE_NULL unexpectedly used $counter", 0, counts.getValue(counter))
        }
        val keyboard = keyboardSnapshot().keyboard
        var result: Result<Unit>? = null
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            result = runCatching {
                fun visibleStrip(view: View): Boolean = when (view) {
                    is CandidateStripView -> view.isShown
                    is ViewGroup -> (0 until view.childCount).any { visibleStrip(view.getChildAt(it)) }
                    else -> false
                }
                assertFalse("TYPE_NULL exposed the candidate strip", visibleStrip(keyboard))
            }
        }
        checkNotNull(result).getOrThrow()
    }

    private fun space() = driver.tapKeyByDescription(
        InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space))

    private companion object { const val FIELD = "qa_composing_text" }
}
