package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
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

    @Test
    fun alreadyFocusedEditorRestoresKeyboardAfterExplicitHide() {
        val selector = By.res(ImeTestDriver.PACKAGE_NAME, "qa_plain_text")
        assertTrue(driver.device.findObject(selector).isFocused)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        driver.device.pressBack()
        assertTrue(driver.device.wait(Until.gone(By.desc(context.getString(R.string.key_delete))),
            ImeTestDriver.WAIT_MILLIS))
        assertTrue(driver.device.findObject(selector).isFocused)
        driver.focusField("qa_plain_text")
        val key = driver.characterKey("a", "A")
        val expected = key.text
        key.click()
        driver.awaitFieldText("qa_plain_text", expected)
    }
}
