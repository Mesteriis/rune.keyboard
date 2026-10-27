package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Only the explicit separate application; never changes the default Rune's state. */
class QualificationPackageSafetyInstrumentedTest {
    @Test fun rejectedDefaultDriverTeardownPreservesImeAndFixturePreferences() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assumeTrue(context.packageName == ImeTestDriver.PACKAGE_NAME + ".qualification")
        val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        val fields = listOf("default_input_method", "enabled_input_methods", "show_ime_with_hard_keyboard")
        fun secure() = fields.associateWith { device.executeShellCommand("settings get secure $it").trim() }
        val before = secure()
        val preferences = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE)
        val previous = HashMap(preferences.all)
        check(preferences.edit().putBoolean("qualification_guard_probe", true).commit())
        val expected = HashMap(preferences.all)
        val driver = ImeTestDriver()
        try {
            try {
                driver.setUp()
                fail("The default-package driver must reject the qualification app")
            } catch (error: IllegalStateException) {
                assertEquals("IME QA driver requires the default Rune package", error.message)
            } finally {
                driver.tearDown()
                driver.tearDown() // Cleanup after an early refusal is also idempotent.
            }
            assertEquals(before, secure())
            assertEquals(expected, preferences.all)
        } finally {
            // The only fixture-written key is synthetic and belongs to this separate app.
            val edit = preferences.edit()
            if (previous.containsKey("qualification_guard_probe")) {
                edit.putBoolean("qualification_guard_probe", previous["qualification_guard_probe"] as Boolean)
            } else edit.remove("qualification_guard_probe")
            check(edit.commit())
        }
    }
}
