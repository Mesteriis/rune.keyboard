package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ImeLifecycleInstrumentedTest : ImeTestBase() {
    @Test
    fun backspaceRepeatStopsAfterCancel() {
        driver.tapQaControl("qa_seed_canary")
        val touch = driver.touchDown(driver.deleteKey())
        SystemClock.sleep(900)
        driver.cancelTouch(touch)
        val afterCancel = driver.fieldText("qa_plain_text")
        SystemClock.sleep(900)
        driver.awaitFieldText("qa_plain_text", afterCancel)
    }

    @Test
    fun backspaceRepeatStopsWhenImeViewDetaches() {
        driver.tapQaControl("qa_seed_canary")
        driver.touchDown(driver.deleteKey())
        SystemClock.sleep(700)
        driver.shell("am start -W -n ${ImeTestDriver.PACKAGE_NAME}/.settings.SettingsActivity")
        SystemClock.sleep(900)
        driver.device.pressBack()
        driver.focusField("qa_plain_text")
        val afterDetach = driver.fieldText("qa_plain_text")
        SystemClock.sleep(900)
        driver.awaitFieldText("qa_plain_text", afterDetach)
    }

    @Test
    fun focusLossCancelsAnArmedCharacterGesture() {
        driver.tapQaControl("qa_seed_cursor")
        driver.touchDown(driver.characterKey("a", "A"))
        driver.shell("am start -W -n ${ImeTestDriver.PACKAGE_NAME}/.settings.SettingsActivity")
        driver.device.pressBack()
        driver.focusField("qa_plain_text")
        driver.awaitFieldText("qa_plain_text", "leftright")
    }

    @Test
    fun settingsChangeRecreatesTheActiveImeView() {
        driver.tapQaControl("qa_seed_cursor")
        driver.setNumberRowThroughSettings(enabled = true)
        driver.assertKeyVisible("1")
        driver.tapKey("a", "A")
        driver.awaitFieldText("qa_plain_text", "leftrighta")
    }
}
