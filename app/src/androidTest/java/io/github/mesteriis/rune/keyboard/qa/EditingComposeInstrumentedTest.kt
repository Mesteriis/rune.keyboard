package io.github.mesteriis.rune.keyboard.qa

import android.content.ContextWrapper
import android.content.ClipData
import android.graphics.Rect
import android.view.View
import android.view.ViewGroup
import android.widget.GridView
import android.view.inputmethod.EditorInfo
import android.content.ClipboardManager
import android.os.Build
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiEntry
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.Rule
import org.junit.rules.TestName

/** Independent Compose editor; only the private emoji case permits an explicitly authorized Fold. */
class EditingComposeInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false
    private var clipboardTouched = false
    private var physical = false
    private var stores: Map<String, Map<String, String>>? = null
    @get:Rule val testName = TestName()

    @Before fun prepare() {
        assumeTrue("Explicit independent Compose QA fixture required",
            InstrumentationRegistry.getArguments().getString("runeComposeQa") == "true")
        val args = InstrumentationRegistry.getArguments()
        val emulator = Build.HARDWARE in setOf("ranchu", "goldfish")
        physical = Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true" &&
            args.getString("runeFailureArtifacts") == "false" &&
            testName.methodName == "composePrivateEmojiDeletionAndContinuation"
        assumeTrue("Owned emulator or explicitly authorized Fold private case required", emulator || physical)
        if (physical) flushDiagnostics()
        prepared = true
        driver.setUp(privateQa = physical)
        if (physical) {
            val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, android.content.Context.MODE_PRIVATE).edit()
            for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
                SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
                SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
                SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
            assertTrue(edit.commit())
        }
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposeQa(privateInput = physical)
        awaitSelection(0, 0, 0)
        noPayloadReads()
        if (physical) {
            flushDiagnostics()
            stores = personalStoreSnapshot(context)
        }
    }
    @After fun restore() {
        if (clipboardTouched) instrumentation.runOnMainSync {
            val clipboard = context.getSystemService(ClipboardManager::class.java)
            if (android.os.Build.VERSION.SDK_INT >= 28) clipboard.clearPrimaryClip()
            else clipboard.setPrimaryClip(ClipData.newPlainText("Rune QA", ""))
        }
        try {
            if (physical && stores != null) {
                flushDiagnostics()
                assertEquals("Synthetic QA changed personal stores", stores, personalStoreSnapshot(context))
            }
        } finally {
            if (prepared) {
                if (driver.device.currentPackageName == PACKAGE) driver.device.pressHome()
                driver.tearDown()
            }
        }
    }

    private fun flushDiagnostics() {
        val recorder = TypingDiagnosticsProvider.create(context) as DiagnosticsRecorder
        val done = CountDownLatch(1)
        var success = false
        recorder.barrier { success = it; done.countDown() }
        assertTrue("Diagnostics queue fence timed out", done.await(5, TimeUnit.SECONDS))
        assertTrue("Diagnostics queue fence failed", success)
    }

    @Test fun composePrivateEmojiDeletionAndContinuation() {
        if (!physical) driver.launchComposeQa(privateInput = true)
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            var owner = keyboard.rootView.context
            while (owner is ContextWrapper && owner !is RuneInputMethodService) owner = owner.baseContext
            val service = checkNotNull(owner as? RuneInputMethodService)
            assertTrue("Compose must request no personalized learning",
                service.currentInputEditorInfo.imeOptions and EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING != 0)
        }
        type("a")
        awaitField("a")
        driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        driver.tapKeyByDescription("Emoji")
        for ((category, glyph) in listOf("People & Body" to "👩‍💻", "Flags" to "🇪🇸")) {
            clickEmoji(category, glyph)
            awaitField("a$glyph")
            driver.tapKeyByDescription(context.getString(R.string.key_delete))
            awaitField("a")
            noPayloadReads()
        }
        clickEmoji("People & Body", "👩‍💻")
        awaitField("a👩‍💻")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        type("b")
        awaitField("a👩‍💻b")
        noPayloadReads()
    }

    private fun clickEmoji(category: String, glyph: String) {
        val keyboard = keyboardSnapshot().keyboard
        fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
            (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
        instrumentation.runOnMainSync {
            val tab = descendants(keyboard).single { it.contentDescription?.toString() == category }
            tab.requestRectangleOnScreen(Rect(0, 0, tab.width, tab.height), true)
        }
        checkNotNull(driver.device.wait(Until.findObject(By.desc(category)), 3_000)).click()
        var selected = false
        instrumentation.runOnMainSync {
            val grid = descendants(keyboard).filterIsInstance<GridView>().single()
            val position = (0 until grid.adapter.count).single { (grid.adapter.getItem(it) as EmojiEntry).glyph == glyph }
            val cell = grid.adapter.getView(position, null, grid)
            selected = grid.performItemClick(cell, position, grid.adapter.getItemId(position))
        }
        assertTrue("Emoji grid must dispatch the selected public item", selected)
        instrumentation.waitForIdleSync()
    }

    @Test fun composeSelectionCutPasteAndNativeMenuKeepPayloadReadsZero() {
        type("abcd")
        awaitField("abcd")
        openPanel()
        driver.tapKeyByDescription("Selection off")
        driver.tapKeyByDescription("Move left")
        awaitSelection(4, 3, 4)
        clipboardTouched = true
        driver.tapKeyByDescription("Cut")
        awaitField("abc")
        awaitSelection(3, 3, 3)
        setClip("X")
        driver.tapKeyByDescription("Paste")
        awaitField("abcX")
        awaitSelection(4, 4, 4)
        driver.tapKeyByDescription("Select all")
        awaitSelection(0, 4, 4)
        driver.tapKeyByDescription("Copy")
        awaitClipboard("abcX")
        noPayloadReads()
    }

    @Test fun composePasteKeepsAdjacentSuffixLiteralAndOwnSpaceRestoresCorrection() {
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

    @Test fun composeVerticalSelectionAndHomeEndUseNativeBoundaries() {
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
        awaitSelection(9, 4, 9)
        driver.tapKeyByDescription("Selection on")
        driver.tapKeyByDescription("Move right")
        awaitSelection(9, 9, 9)
        noPayloadReads()
    }

    private fun setClip(value: String) = instrumentation.runOnMainSync {
        clipboardTouched = true
        context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Rune QA", value))
    }
    private fun awaitClipboard(expected: String) {
        val clipboard = context.getSystemService(ClipboardManager::class.java)
        val deadline = SystemClock.uptimeMillis() + 5_000
        do {
            var matches = false
            instrumentation.runOnMainSync {
                matches = clipboard.primaryClip?.getItemAt(0)?.text?.toString() == expected
            }
            if (matches) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Independent Compose editor did not publish the expected clipboard entry")
    }
    private fun openPanel() {
        val key = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync { assertTrue(key.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null)) }
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Paste")), 3_000))
    }
    private fun type(value: String) = value.forEach { driver.tapKey(it.toString()) }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(By.res(PACKAGE, "qa_compose_stats")))
        .text.orEmpty().split(' ').associate { val (name, value) = it.split('='); name to value.toInt() }
    private fun awaitField(expected: String) {
        val deadline = SystemClock.uptimeMillis() + 5_000
        do {
            if (driver.device.findObject(By.pkg(PACKAGE).clazz("android.widget.EditText"))?.text == expected) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Independent Compose field did not reach fixed public input; numeric stats=${stats()}")
    }
    private fun awaitSelection(start: Int, end: Int, length: Int) {
        val deadline = SystemClock.uptimeMillis() + 5_000
        do {
            val counts = stats()
            if (counts.getValue("connections") > 0 && counts["selectionStart"] == start && counts["selectionEnd"] == end && counts["length"] == length) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Compose selection did not reach $start,$end length=$length; numeric stats=${stats()}")
    }
    private fun noPayloadReads() {
        val counts = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $name", 0, counts.getValue(name))
    }
    private companion object { const val PACKAGE = "io.github.mesteriis.rune.qa.compose" }
}
