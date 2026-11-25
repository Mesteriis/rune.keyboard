package io.github.mesteriis.rune.keyboard.qa

import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.text.InputType
import android.view.inputmethod.EditorInfo
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

/** The owned emulator must contain GetBack GPS 0.8 with location permission denied. */
class GetBackGpsNumericInstrumentedTest {
    @Test fun signedDecimalBackspaceAndDoneInUnsavedDestination() {
        val driver = ImeTestDriver()
        val registry = InstrumentationRegistry.getInstrumentation()
        val args = InstrumentationRegistry.getArguments()
        assumeTrue("An explicitly owned emulator is required",
            args.getString("runeOwnedEmulator") == "q8-getback-gps" &&
                Build.HARDWARE in setOf("ranchu", "goldfish") && driver.shell("getprop ro.kernel.qemu") == "1")
        check(args.getString("runeFailureArtifacts") == "false")
        val app = "com.github.ruleant.getback_gps"
        fun longitude() = By.res(app, "location_longtitude")
        val keyboard = By.pkg(registry.targetContext.packageName)
            .desc(registry.targetContext.getString(R.string.key_delete))
        try {
            driver.setUp(privateQa = true)
            driver.shell("am start -W -n $app/.MainActivity")
            assertTrue("GetBack GPS did not open", driver.device.wait(Until.hasObject(By.pkg(app)), 5000))
            val entry = By.pkg(app).text("Enter destination manually")
            val manualEntry = driver.device.findObject(By.res(app, "menu_enterlocation"))
                ?: driver.device.findObject(entry)
                ?: run {
                    checkNotNull(driver.device.findObject(By.desc("More options"))).click()
                    checkNotNull(driver.device.wait(Until.findObject(entry), 5000))
                }
            manualEntry.click()
            checkNotNull(driver.device.wait(Until.findObject(longitude()), 5000)).click()
            assertTrue("Rune numeric keyboard missing", driver.device.wait(Until.hasObject(keyboard), 5000))
            var owner = keyboardSnapshot().keyboard.rootView.context
            while (owner !is InputMethodService && owner is ContextWrapper) owner = owner.baseContext
            val info = checkNotNull((owner as InputMethodService).currentInputEditorInfo)
            val numericFlags = InputType.TYPE_NUMBER_FLAG_SIGNED or InputType.TYPE_NUMBER_FLAG_DECIMAL
            assertEquals(app, info.packageName)
            assertEquals(InputType.TYPE_CLASS_NUMBER, info.inputType and InputType.TYPE_MASK_CLASS)
            assertEquals(numericFlags, info.inputType and numericFlags)
            assertEquals(EditorInfo.IME_ACTION_DONE, info.imeOptions and EditorInfo.IME_MASK_ACTION)

            "-12.35".forEach { driver.tapKey(it.toString()) }
            assertTrue("Signed decimal was not received", driver.device.wait(Until.hasObject(longitude().text("-12.35")), 5000))
            driver.tapDelete()
            assertTrue("Backspace changed the wrong value", driver.device.wait(Until.hasObject(longitude().text("-12.3")), 5000))
            driver.tapEnter(R.string.key_done)
            assertTrue("Done did not dismiss Rune", driver.device.wait(Until.gone(keyboard), 5000))
            assertTrue("Done did not preserve the unsaved value", driver.device.hasObject(longitude().text("-12.3")))
        } finally {
            try {
                if (driver.device.hasObject(longitude())) {
                    checkNotNull(driver.device.findObject(By.res("android", "button2"))).click()
                    assertTrue("Destination form was not discarded", driver.device.wait(Until.gone(longitude()), 5000))
                }
            } finally {
                driver.tearDown()
            }
        }
    }
}
