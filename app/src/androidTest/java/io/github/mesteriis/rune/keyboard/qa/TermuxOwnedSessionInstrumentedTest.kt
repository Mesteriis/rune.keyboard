package io.github.mesteriis.rune.keyboard.qa

import android.content.ContextWrapper
import android.content.Context
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.SystemClock
import android.text.InputType
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Requires a freshly created, separately verified Termux session. */
class TermuxOwnedSessionInstrumentedTest {
    @Test fun rawTypingBackspaceAndEnterInOwnedSession() {
        val args = InstrumentationRegistry.getArguments()
        assumeTrue("Explicit physical Fold and owned Termux session required",
            Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true" &&
                args.getString("runeOwnedTermuxSession") == "true")
        check(args.getString("runeFailureArtifacts") == "false")
        val driver = ImeTestDriver()
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val terminal = By.res("com.termux", "terminal_view")
        fun transcript(): String {
            check(driver.device.currentPackageName == "com.termux") { "Owned terminal lost foreground" }
            return checkNotNull(driver.device.findObject(terminal)).contentDescription?.toString().orEmpty()
        }
        fun awaitSuffix(expected: String) {
            val deadline = SystemClock.uptimeMillis() + 5000
            while (!transcript().trimEnd().endsWith(expected)) {
                check(SystemClock.uptimeMillis() < deadline) { "Terminal did not echo expected synthetic input" }
                SystemClock.sleep(50)
            }
        }
        var owner = keyboardSnapshot().keyboard.rootView.context
        while (owner !is InputMethodService && owner is ContextWrapper) owner = owner.baseContext
        val service = owner as InputMethodService
        val info = checkNotNull(service.currentInputEditorInfo)
        assertEquals("com.termux", info.packageName)
        assertEquals(InputType.TYPE_NULL, info.inputType)
        assertTrue("Fresh shell prompt unavailable", Regex("[$#%❯➜>]\\s*$").containsMatchIn(transcript().trimEnd()))
        val originalLanguage = listOf("EN", "RU", "ES").singleOrNull {
            driver.device.hasObject(By.pkg(context.packageName).text(it))
        } ?: error("Original keyboard language unavailable")
        val preferences = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE)
        val originalPreferences = HashMap(preferences.all)
        try {
            driver.switchLanguageUntil("EN")
            for (key in listOf("t", "r", "u", "x")) driver.tapKey(key)
            awaitSuffix("trux")
            driver.tapDelete()
            awaitSuffix("tru")
            driver.tapKey("e")
            awaitSuffix("true")
            driver.tapEnter(R.string.key_enter)
            val deadline = SystemClock.uptimeMillis() + 5000
            while (transcript().trimEnd().endsWith("true")) {
                check(SystemClock.uptimeMillis() < deadline) { "Terminal did not advance after Enter" }
                SystemClock.sleep(50)
            }
            assertTrue("Shell prompt unavailable after Enter", Regex("[$#%❯➜>]\\s*$").containsMatchIn(transcript().trimEnd()))
            // Only numeric status; never publish the terminal transcript or prompt.
            InstrumentationRegistry.getInstrumentation().sendStatus(2, android.os.Bundle().apply {
                putInt("raw_editor", 1); putInt("backspace", 1); putInt("enter", 1)
            })
        } finally {
            try { driver.switchLanguageUntil(originalLanguage) }
            finally { restorePreferenceSnapshot(preferences, originalPreferences) }
        }
    }
}
