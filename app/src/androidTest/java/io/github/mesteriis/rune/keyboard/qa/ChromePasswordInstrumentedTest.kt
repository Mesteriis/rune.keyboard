package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.view.KeyEvent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Only the fixed loopback page on an explicitly owned Chrome emulator. */
class ChromePasswordInstrumentedTest {
    @Test fun passwordSuppressesPreviewAndDeletesOneCharacter() {
        val driver = ImeTestDriver()
        val args = InstrumentationRegistry.getArguments()
        assumeTrue("An explicitly owned emulator is required",
            args.getString("runeOwnedEmulator") == "q8-chrome-password" &&
                Build.HARDWARE in setOf("ranchu", "goldfish") && driver.shell("getprop ro.kernel.qemu") == "1")
        check(args.getString("runeFailureArtifacts") == "false")
        val port = checkNotNull(args.getString("runeLoopbackPort")).toInt()
        check(port in 1024..65535)
        val browser = "com.android.chrome"
        val address = By.res(browser, "url_bar").textContains("127.0.0.1:$port/rune-q8-password")
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val keyboard = By.pkg(context.packageName).desc(context.getString(R.string.key_delete))
        try {
            driver.setUp(privateQa = true)
            driver.setKeyPreviewForTest(true)
            driver.shell("am start -W -a android.intent.action.VIEW -d http://127.0.0.1:$port/rune-q8-password --ez create_new_tab true -p $browser")
            if (driver.device.wait(Until.hasObject(By.pkg(browser).text("Chrome notifications make things easier")), 5000)) {
                checkNotNull(driver.device.findObject(By.pkg(browser).text("No thanks"))).click()
            }
            assertTrue("Owned Chrome page missing", driver.device.wait(Until.hasObject(address), 10000))
            for ((phase, field) in listOf("rune-normal", "rune-password").withIndex()) {
                checkNotNull(driver.device.wait(Until.findObject(By.pkg(browser).res(field)), 5000)).click()
                assertTrue("Rune keyboard missing", driver.device.wait(Until.hasObject(keyboard), 5000))
                val ordinary = phase == 0
                observePreview(driver, phase, enabled = true,
                    policy = if (ordinary) InputPolicy.NORMAL else InputPolicy.SENSITIVE,
                    expectedVisible = ordinary, retainDiagnostics = false)
            }
            assertTrue("Owned Chrome page lost foreground", driver.device.hasObject(address))
            "runesecret".forEach { driver.tapKey(it.toString()) }
            driver.tapDelete()
            assertTrue("Synthetic DOM edit was not observed", driver.device.wait(
                Until.hasObject(By.pkg(browser).text("Synthetic edit verified")), 5000))
        } finally {
            try {
                if (driver.device.hasObject(address)) {
                    driver.device.pressKeyCode(KeyEvent.KEYCODE_W, KeyEvent.META_CTRL_ON)
                    assertTrue("Owned Chrome tab did not close", driver.device.wait(Until.gone(address), 5000))
                }
            } finally {
                driver.tearDown()
            }
        }
    }
}
