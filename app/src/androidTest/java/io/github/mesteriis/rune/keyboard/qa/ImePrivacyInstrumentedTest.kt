package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ImePrivacyInstrumentedTest : ImeTestBase() {
    @Test
    fun passwordFieldSuppressesPopupWithNormalFieldPositiveControl() {
        driver.ensureKeyPreviewEnabled()
        driver.tapQaControl("qa_seed_cursor")
        val normalKey = driver.characterKey("a", "A")
        val normalBefore = driver.previewCropFor(normalKey)
        val normalTouch = driver.touchDown(normalKey)
        SystemClock.sleep(150)
        val normalDuringScreen = driver.captureScreen()
        val normalDuring = driver.previewCropFor(normalKey, normalDuringScreen)
        driver.cancelTouch(normalTouch)
        val normalChanged = driver.changedPixels(normalBefore, normalDuring)
        if (normalChanged <= 40) {
            driver.saveFailureBitmap("popup-normal-before.png", normalBefore)
            driver.saveFailureBitmap("popup-normal-during.png", normalDuring)
            driver.saveFailureBitmap("popup-normal-during-full.png", normalDuringScreen)
        }
        assertTrue("Normal-field positive control changed only $normalChanged pixels", normalChanged > 40)

        driver.focusField("qa_password")
        val passwordKey = driver.characterKey("a", "A")
        val passwordBefore = driver.previewCropFor(passwordKey)
        val passwordTouch = driver.touchDown(passwordKey)
        SystemClock.sleep(150)
        val passwordDuring = driver.previewCropFor(passwordKey)
        driver.cancelTouch(passwordTouch)
        assertTrue("Password field changed the preview crop", driver.changedPixels(passwordBefore, passwordDuring) <= 40)
    }

    @Test
    fun syntheticCanaryIsAbsentFromRuneProcessLogcat() {
        driver.shell("logcat -c")
        driver.tapQaControl("qa_seed_canary")
        driver.tapDelete()
        val imePid = driver.shell("pidof ${ImeTestDriver.PACKAGE_NAME}").split(' ').firstOrNull().orEmpty()
        val logs = if (imePid.isEmpty()) "" else driver.shell("logcat -d --pid=$imePid")
        assertTrue("Synthetic editor text appeared in Rune-scoped Logcat", "RUNE_QA_CANARY_7429" !in logs)
    }
}
