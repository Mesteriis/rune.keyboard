package io.github.mesteriis.rune.keyboard.qa

import android.content.ClipData
import android.content.ClipboardManager
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Offline WebView in :qa_editor, real Rune keys, test-owned clipboard and numeric-only diagnostics. */
class EditingWebViewInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false
    private var clipboardTouched = false

    @Before fun prepare() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish"))
        prepared = true
        driver.setUp()
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchWebViewQa()
        awaitSelection(0, 0, 0)
        noPayloadReads()
    }

    @After fun restore() {
        if (clipboardTouched) instrumentation.runOnMainSync {
            context.getSystemService(ClipboardManager::class.java).clearPrimaryClip()
        }
        if (prepared) driver.tearDown()
    }

    @Test fun webViewSelectionCutPasteAndHomeEndUseNativeEditorCommands() {
        type("abcd")
        awaitField("abcd")
        openPanel()
        driver.tapKeyByDescription("Selection off")
        driver.tapKeyByDescription("Move left")
        // DOM exposes normalized selection bounds; Android reports direction separately.
        awaitSelection(3, 4, 4)
        clipboardTouched = true
        driver.tapKeyByDescription("Cut")
        awaitField("abc")
        awaitSelection(3, 3, 3)
        setClip("X")
        driver.tapKeyByDescription("Paste")
        awaitField("abcX")
        awaitSelection(4, 4, 4)
        driver.tapKey("Home")
        awaitSelection(0, 0, 4)
        driver.tapKey("End")
        awaitSelection(4, 4, 4)
        driver.tapKeyByDescription("Select all")
        awaitSelection(0, 4, 4)
        driver.tapKeyByDescription("Copy")
        instrumentation.runOnMainSync {
            assertEquals("abcX", context.getSystemService(ClipboardManager::class.java)
                .primaryClip?.getItemAt(0)?.text?.toString())
        }
        noPayloadReads()
    }

    @Test fun webViewPasteKeepsAdjacentSuffixLiteralAndOwnSpaceRestoresCorrection() {
        type("old")
        awaitField("old")
        openPanel()
        setClip("foreign")
        driver.tapKeyByDescription("Paste")
        awaitField("oldforeign")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        type("teh")
        awaitField("oldforeignteh")
        space()
        type("teh")
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
        space()
        awaitField("oldforeignteh the ")
        noPayloadReads()
    }

    @Test fun webViewVerticalSelectionCrossesNewlineWithoutPayloadReads() {
        type("abcd")
        driver.tapKeyByDescription(context.getString(R.string.key_enter))
        type("efgh")
        awaitField("abcd\nefgh")
        openPanel()
        driver.tapKeyByDescription("Move up")
        awaitSelection(4, 4, 9)
        driver.tapKey("Home")
        awaitSelection(0, 0, 9)
        driver.tapKeyByDescription("Move down")
        awaitSelection(5, 5, 9)
        driver.tapKey("End")
        awaitSelection(9, 9, 9)
        driver.tapKeyByDescription("Selection off")
        driver.tapKeyByDescription("Move up")
        awaitSelection(4, 9, 9)
        driver.tapKeyByDescription("Selection on")
        driver.tapKeyByDescription("Move right")
        awaitSelection(9, 9, 9)
        noPayloadReads()
    }

    private fun setClip(value: String) = instrumentation.runOnMainSync {
        clipboardTouched = true
        context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Rune QA", value))
    }
    private fun openPanel() {
        val key = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync { assertTrue(key.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null)) }
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Paste")), 3_000))
    }
    private fun type(value: String) = value.forEach { driver.tapKey(it.toString()) }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(By.res(context.packageName, "qa_webview_stats")))
        .text.orEmpty().split(' ').associate { val (name, value) = it.split('='); name to value.toInt() }
    private fun awaitField(expected: String) {
        val deadline = SystemClock.uptimeMillis() + 5_000
        do {
            if (driver.device.findObject(By.clazz("android.widget.EditText"))?.text == expected) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Offline WebView field did not reach fixed public input; numeric stats=${stats()}")
    }
    private fun awaitSelection(start: Int, end: Int, length: Int) {
        val deadline = SystemClock.uptimeMillis() + 5_000
        do {
            val counts = stats()
            if (counts.getValue("connections") > 0 && counts["ready"] == 1 && counts["selectionStart"] == start && counts["selectionEnd"] == end && counts["length"] == length) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Offline DOM selection did not reach $start,$end length=$length; numeric stats=${stats()}")
    }
    private fun noPayloadReads() {
        val counts = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $name", 0, counts.getValue(name))
    }
}
