package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.SdkSuppress
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
@SdkSuppress(minSdkVersion = 26, maxSdkVersion = 26)
class SpellingPopupRecoveryInstrumentedTest : ImeTestBase() {
    @Test
    fun androidSpellingPopupCanCloseWithoutChangingEditorText() {
        driver.configureEnglishStartingLanguage()
        assertFalse(driver.dismissAndroidSpellingSuggestions())
        driver.shell("am start -W -f 0x10008000 -n ${ImeTestDriver.QA_ACTIVITY} --ez qa_misspelling_fixture true")
        driver.tapQaControl("qa_seed_cursor")
        driver.device.pressBack()
        val field = checkNotNull(driver.device.wait(Until.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_plain_text")), 5_000L))
        field.click()
        assertTrue("Android did not open spelling suggestions", driver.device.wait(Until.hasObject(By.res("android", "suggestionContainer")), 10_000L))
        assertTrue(driver.dismissAndroidSpellingSuggestions())
        assertEquals(1, driver.spellingPopupDismissals)
        assertFalse(driver.dismissAndroidSpellingSuggestions())
        driver.tapKey("a", "A")
        driver.revealFieldAndAwaitText("qa_plain_text", "leftrighta")
    }
}
