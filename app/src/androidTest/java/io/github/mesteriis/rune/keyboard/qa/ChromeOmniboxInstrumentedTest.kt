package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
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
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TestName

/** Uses only its own loopback tab and synthetic addresses. */
class ChromeOmniboxInstrumentedTest {
    private val driver = ImeTestDriver()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val browser = "com.android.chrome"
    private val target = "runeqa.invalid"
    private var port = 0
    private var prepared = false
    private var pageOwned = false
    private var rotationOwned = false
    @get:Rule val testName = TestName()

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        val loopback = testName.methodName == "landscapeGoLoadsOwnedPageAndDismissesKeyboard"
        val physicalFold = Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true"
        val ownedEmulator = args.getString("runeOwnedEmulator") == "q8-omnibox" &&
            Build.HARDWARE in setOf("ranchu", "goldfish") && driver.shell("getprop ro.kernel.qemu") == "1"
        assumeTrue("Explicit Fold or owned landscape emulator required", if (loopback) ownedEmulator else physicalFold)
        check(args.getString("runeFailureArtifacts") == "false")
        port = checkNotNull(args.getString("runeLoopbackPort")).toInt()
        check(port in 1024..65535)
        if (loopback) {
            rotationOwned = true
            driver.device.setOrientationLeft()
        }
        prepared = true
        driver.setUp(privateQa = true)
        driver.device.executeShellCommand("am start -W -a android.intent.action.VIEW -d http://127.0.0.1:$port/rune-q8 --ez create_new_tab true -p $browser")
        if (ownedEmulator && driver.device.wait(Until.hasObject(
                By.pkg(browser).text("Chrome notifications make things easier")), 5000)) {
            checkNotNull(driver.device.findObject(By.pkg(browser).text("No thanks"))).click()
        }
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
                assertTrue("Owned loopback tab did not close", driver.device.wait(Until.gone(
                    By.res(browser, "url_bar").textContains("127.0.0.1:$port")), 5000))
            }
        } finally {
            try { if (prepared) driver.tearDown() }
            finally { if (rotationOwned) driver.device.unfreezeRotation() }
        }
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

    @Test fun landscapeGoLoadsOwnedPageAndDismissesKeyboard() {
        assertTrue("Chrome was not in landscape", driver.device.displayWidth > driver.device.displayHeight)
        val url = By.res(browser, "url_bar")
        val delete = By.pkg(context.packageName).desc(context.getString(R.string.key_delete))
        checkNotNull(driver.device.findObject(url)).click()
        assertTrue("Rune keyboard missing", driver.device.wait(Until.hasObject(delete), 5000))

        val address = "http://127.0.0.1:$port/rune-q8-no-suggestion"
        checkNotNull(driver.device.findObject(url)).text = address
        driver.device.pressKeyCode(KeyEvent.KEYCODE_MOVE_END)
        driver.tapKey("s", "S")
        driver.tapKey("x", "X")
        assertEquals(address + "sx", checkNotNull(driver.device.findObject(url)).text)
        driver.tapDelete()
        assertEquals(address + "s", checkNotNull(driver.device.findObject(url)).text)

        var owner: Context = keyboardSnapshot().keyboard.rootView.context
        while (owner !is InputMethodService && owner is ContextWrapper) owner = owner.baseContext
        val ime = owner as InputMethodService
        instrumentation.runOnMainSync { assertTrue("Input view was not shown before Go", ime.isInputViewShown) }
        driver.tapEnter(R.string.key_go)
        assertTrue("Destination address missing", driver.device.wait(Until.hasObject(
            By.res(browser, "url_bar").textContains("127.0.0.1:$port/rune-q8-no-suggestions")), 10000))
        assertTrue("Rune keyboard remained visible", driver.device.wait(Until.gone(delete), 10000))
        instrumentation.runOnMainSync { assertTrue("Input view remained shown", !ime.isInputViewShown) }
        assertTrue("Chrome left landscape", driver.device.displayWidth > driver.device.displayHeight)
    }
}
