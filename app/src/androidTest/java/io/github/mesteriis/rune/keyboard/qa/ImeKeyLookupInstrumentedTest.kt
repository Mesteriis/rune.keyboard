package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.StaleObjectException
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ImeKeyLookupInstrumentedTest : ImeTestBase() {
    @Test
    fun detachedKeyIsResolvedAgainBeforeOneTapIsInjected() {
        driver.launchComposingQa()
        val obsolete = driver.keyByText("a")
        driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext
            .getString(R.string.key_shift))
        assertThrows(StaleObjectException::class.java) { obsolete.visibleBounds }
        var resolutions = 0
        driver.tapResolvedKey {
            if (resolutions++ == 0) obsolete else driver.keyByText("A")
        }
        assertEquals(2, resolutions)
        driver.awaitFieldText("qa_composing_text", "A")
    }
}
