package io.github.mesteriis.rune.keyboard.qa

import android.content.ClipData
import android.content.ClipboardManager
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import java.io.File
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/** Host-driven synthetic process-death phases, restricted to disposable emulators. */
class EditingProcessDeathInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private val proof get() = File(context.cacheDir, "editing-process-death-proof")
    private val editorPackage = "io.github.mesteriis.rune.qa.compose"

    @Before fun requireSyntheticEmulator() {
        assumeTrue("Explicit process-death fixture required",
            InstrumentationRegistry.getArguments().getString("runeEditingDeathFixture") == "true")
        check(Build.HARDWARE in setOf("ranchu", "goldfish"))
    }

    @Test fun prepareForeignTextForHostKill() {
        driver.setUp()
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposeQa()
        type("old")
        val mode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            assertTrue(mode.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null))
            context.getSystemService(ClipboardManager::class.java)
                .setPrimaryClip(ClipData.newPlainText("Rune QA", "foreign"))
        }
        driver.tapKeyByDescription("Paste")
        awaitField("oldforeign")
        val rightContext = InstrumentationRegistry.getArguments().getString("runeRightContext") == "true"
        if (rightContext) {
            driver.tapKey("Home")
            val deadline = SystemClock.uptimeMillis() + 5_000
            while (stats()["selectionStart"] != 0 && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(40)
            assertEquals(0, stats().getValue("selectionStart"))
            assertEquals(0, stats().getValue("selectionEnd"))
        }
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        val editorPid = driver.shell("pidof $editorPackage").trim().toInt()
        proof.writeText("${Process.myPid()}\n$editorPid\n$rightContext\n")
        SystemClock.sleep(60_000)
        fail("Host did not kill the synthetic IME process")
    }

    @Test fun recreatedProcessKeepsForeignSuffixIsolated() {
        val fields = proof.readLines()
        val oldPid = fields[0].toInt()
        val editorPid = fields[1].toInt()
        val rightContext = fields[2].toBooleanStrict()
        assertNotEquals("Host must kill Rune", oldPid, Process.myPid())
        assertEquals("Editor process must survive", editorPid, driver.shell("pidof $editorPackage").trim().toInt())
        if (Build.VERSION.SDK_INT == 26) {
            driver.device.setCompressedLayoutHierarchy(true)
            val fallback = checkNotNull(InstrumentationRegistry.getArguments().getString("runeRecoveryFallbackIme"))
            require(fallback.matches(Regex("[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+")))
            driver.shell("ime set $fallback")
            driver.shell("ime set ${context.packageName}/.ime.RuneInputMethodService")
            instrumentation.waitForIdleSync()
            assertEquals("${context.packageName}/.ime.RuneInputMethodService",
                driver.shell("settings get secure default_input_method").trim())
        }
        awaitField("oldforeign")
        if (rightContext) {
            assertEquals(0, stats().getValue("selectionStart"))
            assertEquals(0, stats().getValue("selectionEnd"))
        }
        if (!driver.device.hasObject(By.desc(context.getString(R.string.key_delete)))) {
            checkNotNull(driver.device.findObject(By.pkg(editorPackage).clazz("android.widget.EditText"))).click()
        }
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.key_delete))), 10_000))
        if (rightContext && stats()["selectionStart"] != 0) {
            val mode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
            instrumentation.runOnMainSync {
                assertTrue(mode.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null))
            }
            driver.tapKey("Home")
            driver.tapKeyByDescription(context.getString(R.string.key_letters))
            val deadline = SystemClock.uptimeMillis() + 5_000
            while (stats()["selectionStart"] != 0 && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(40)
        }
        val baseline = stats()
        val position = if (rightContext) 0 else 10
        assertEquals(position, baseline.getValue("selectionStart"))
        assertEquals(position, baseline.getValue("selectionEnd"))
        if (rightContext) {
            type("abc"); space(); awaitField("abc oldforeign")
            type("teh"); space(); awaitField("abc the oldforeign")
        } else {
            type("teh"); space(); awaitField("oldforeignteh ")
            type("teh"); space(); awaitField("oldforeignteh the ")
        }
        val after = stats()
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Rune added a payload read: $key", baseline.getValue(key), after.getValue(key))
        assertTrue(proof.delete())
    }

    private fun type(value: String) = value.forEach { driver.tapKey(it.toString()) }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(By.res(editorPackage, "qa_compose_stats")))
        .text.orEmpty().split(' ').associate { val (name, value) = it.split('='); name to value.toInt() }
    private fun awaitField(expected: String) {
        val deadline = SystemClock.uptimeMillis() + 5_000
        do {
            if (driver.device.findObject(By.pkg(editorPackage).clazz("android.widget.EditText"))?.text == expected) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Independent editor did not retain the expected synthetic text")
    }
}
