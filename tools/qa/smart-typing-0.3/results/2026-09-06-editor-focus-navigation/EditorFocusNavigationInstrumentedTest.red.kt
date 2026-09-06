package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EditorFocusNavigationInstrumentedTest : ImeTestBase() {
    @Test
    fun offscreenCustomEditorReceivesOneFocusTapAndItsAction() {
        assertNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_custom_action")))
        driver.focusField("qa_custom_action")
        driver.tapEnter(R.string.qa_custom_action)
        driver.awaitStatus("Action received: 0")
    }
}
