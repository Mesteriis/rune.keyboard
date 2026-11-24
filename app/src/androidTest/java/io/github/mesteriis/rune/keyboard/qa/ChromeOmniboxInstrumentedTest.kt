package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.view.KeyEvent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/** Uses only its own loopback tab and synthetic .invalid address. */
class ChromeOmniboxInstrumentedTest {
    private val driver = ImeTestDriver()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val browser = "com.android.chrome"
    private val target = "runeqa.invalid"
    private var port = 0
    private var prepared = false
    private var pageOwned = false

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        assumeTrue("Explicit physical Fold test required", Build.MODEL.startsWith("SM-F") &&
            args.getString("allowPhysicalDevice") == "true")
        check(args.getString("runeFailureArtifacts") == "false")
        port = checkNotNull(args.getString("runeLoopbackPort")).toInt()
        check(port in 1024..65535)
        prepared = true
        driver.setUp(privateQa = true)
        driver.device.executeShellCommand("am start -W -a android.intent.action.VIEW -d http://127.0.0.1:$port/rune-q8 --ez create_new_tab true -p $browser")
        assertTrue("Owned local tab missing", driver.device.wait(Until.hasObject(
            By.res(browser, "url_bar").textContains("127.0.0.1:$port")), 10000))
        pageOwned = true
    }

    @After fun restore() {
        try {
            if (pageOwned) {
                assertEquals(browser, driver.device.currentPackageName)
                val bar = checkNotNull(driver.device.findObject(By.res(browser, "url_bar")))
                val text = bar.text.orEmpty()
                check(text.contains("127.0.0.1:$port") ||
                    (text.isNotEmpty() && (target + "x").startsWith(text)) || text.contains(target)) {
                    "Owned Chrome tab identity unavailable"
                }
                driver.device.pressKeyCode(KeyEvent.KEYCODE_W, KeyEvent.META_CTRL_ON)
                assertTrue("Owned tab did not close", driver.device.wait(Until.gone(
                    By.res(browser, "url_bar").textContains(target)), 5000))
            }
        } finally { if (prepared) driver.tearDown() }
    }

    @Test fun syntheticAddressBackspaceAndGoReachChrome() {
        val bar = checkNotNull(driver.device.findObject(By.res(browser, "url_bar")))
        bar.click()
        val editing = checkNotNull(driver.device.wait(Until.findObject(By.res(browser, "url_bar")), 5000))
        editing.text = ""
        assertTrue("Rune keyboard missing", driver.device.wait(Until.hasObject(
            By.pkg(context.packageName).desc(context.getString(R.string.key_delete))), 5000))
        for (character in target + "x") driver.tapKey(character.toString())
        assertEquals(target + "x", checkNotNull(driver.device.findObject(By.res(browser, "url_bar"))).text)
        driver.tapDelete()
        assertEquals(target, checkNotNull(driver.device.findObject(By.res(browser, "url_bar"))).text)
        driver.tapEnter(R.string.key_go)
        assertTrue("Chrome did not navigate to the synthetic address", driver.device.wait(Until.hasObject(
            By.res(browser, "url_bar").textContains(target)), 10000))
        assertTrue("Go key remained visible", driver.device.wait(Until.gone(
            By.pkg(context.packageName).desc(context.getString(R.string.key_go))), 10000))
    }
}
