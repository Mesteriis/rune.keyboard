package io.github.mesteriis.rune.keyboard.qa

import android.os.Process
import android.os.SystemClock
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ImePrivacyInstrumentedTest : ImeTestBase() {
    @Test
    fun passwordFieldSuppressesPopupWithNormalFieldPositiveControl() {
        driver.setKeyPreviewForTest(true)
        driver.tapQaControl("qa_seed_cursor")
        observePreview(driver, phase = 0, enabled = true, policy = InputPolicy.NORMAL, expectedVisible = true)
        driver.setKeyPreviewForTest(false)
        // The same editor is still focused. Tapping its misspelled seed on API 26 opens
        // Android's spelling popup and changes the accessibility window under observation.
        observePreview(driver, phase = 1, enabled = false, policy = InputPolicy.NORMAL, expectedVisible = false)
        driver.setKeyPreviewForTest(true)
        driver.focusField("qa_password")
        observePreview(driver, phase = 2, enabled = true, policy = InputPolicy.SENSITIVE, expectedVisible = false)
    }

    @Test
    fun syntheticCanaryIsAbsentFromRuneProcessLogcat() {
        val pid = Process.myPid().toString()
        assertEquals("Instrumentation must observe the active Rune process", pid,
            driver.shell("pidof ${ImeTestDriver.PACKAGE_NAME}"))
        val probe = "rune-qa-logcat-$pid-${SystemClock.elapsedRealtimeNanos()}"
        val begin = "$probe-begin"
        val end = "$probe-end"
        val canary = "RUNE_QA_CANARY_7429"
        val passwordCanary = "runeqalogleak"

        Log.i("RuneQaLogcatProbe", begin)
        driver.tapQaControl("qa_seed_canary")
        driver.awaitFieldText("qa_plain_text", canary)
        driver.tapDelete()
        driver.awaitFieldText("qa_plain_text", canary.dropLast(1))
        driver.launchComposingQa(mode = "password")
        passwordCanary.forEach { driver.tapKey(it.toString(), it.uppercase()) }
        driver.tapDelete()
        driver.device.waitForIdle()
        val stats = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME,
            "qa_composing_stats"))).text.orEmpty().split(' ').associate {
            val (name, count) = it.split('='); name to count.toInt()
        }
        assertEquals(passwordCanary.length, stats.getValue("commit"))
        assertEquals(passwordCanary.length - 1, stats.getValue("selectionEnd"))
        for (counter in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected password payload read: $counter", 0, stats.getValue(counter))
        }
        assertEquals("Rune process changed during the probe", pid, driver.shell("pidof ${ImeTestDriver.PACKAGE_NAME}"))
        Log.i("RuneQaLogcatProbe", end)

        val lines = driver.shell("logcat -d --pid=$pid -v raw").lines()
        val first = lines.indexOf(begin)
        val last = lines.lastIndexOf(end)
        assertTrue("The scoped Logcat interval was not observed", first >= 0 && last > first)
        val interval = lines.subList(first + 1, last)
        assertFalse("Synthetic ordinary editor text appeared in Rune-scoped Logcat",
            interval.any { it.contains(canary.dropLast(1), ignoreCase = true) })
        assertFalse("Synthetic password editor text appeared in Rune-scoped Logcat",
            interval.any { it.contains(passwordCanary.dropLast(1), ignoreCase = true) })
    }
}
