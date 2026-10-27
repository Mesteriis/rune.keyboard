package io.github.mesteriis.rune.keyboard.qa

import android.content.ClipData
import android.content.ClipboardManager
import android.os.SystemClock
import android.view.ViewConfiguration
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

/** Public key actions through the real service and remote :qa_editor InputConnection. */
class EditingPanelInstrumentedTest {
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
        driver.launchComposingQa()
    }

    @After fun restore() {
        if (clipboardTouched) instrumentation.runOnMainSync {
            context.getSystemService(ClipboardManager::class.java).clearPrimaryClip()
        }
        if (prepared) driver.tearDown()
    }

    @Test fun publicSelectionNavigationAndCutReachTheEditorWithoutPayloadReads() {
        type("abcd")
        openPanel()
        driver.tapKeyByDescription("Selection off")
        driver.tapKeyByDescription("Move left")
        awaitSelection(4, 3)
        val select = keyboardSnapshot().keys.single { it.contentDescription == "Selection on" }
        instrumentation.runOnMainSync {
            val node = select.createAccessibilityNodeInfo()
            try { assertTrue(node.isCheckable); assertTrue(node.isChecked) } finally { node.recycle() }
        }
        clipboardTouched = true
        driver.tapKeyByDescription("Cut")
        driver.awaitFieldText("qa_composing_text", "abc")
        awaitSelection(3, 3)
        assertNotNull(driver.device.findObject(By.desc("Selection off")))
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        type("z")
        driver.awaitFieldText("qa_composing_text", "abcz")
        noPayloadReads()
    }

    @Test fun publicPasteAndFrameworkRestartKeepAdjacentSuffixLiteralUntilOwnSpace() {
        type("old")
        openPanel()
        instrumentation.runOnMainSync {
            clipboardTouched = true
            context.getSystemService(ClipboardManager::class.java)
                .setPrimaryClip(ClipData.newPlainText("Rune QA", "foreign"))
        }
        driver.tapKeyByDescription("Paste")
        driver.awaitFieldText("qa_composing_text", "oldforeign")
        checkNotNull(driver.device.findObject(By.res(context.packageName, "qa_composing_restart"))).click()
        driver.device.waitForIdle()
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        type("teh")
        driver.awaitFieldText("qa_composing_text", "oldforeignteh")
        space()
        type("teh")
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
        space()
        driver.awaitFieldText("qa_composing_text", "oldforeignteh the ")
        noPayloadReads()
    }

    @Test fun touchPopupEntryAndHeldArrowStopOnCancellation() {
        type("abcdefghijklmnop")
        driver.selectFirstAlternate("?123") {
            assertNull(driver.device.findObject(By.desc("Paste")))
        }
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Paste")), 3_000))
        assertNull(driver.device.findObject(By.desc("Move up")))
        assertNull(driver.device.findObject(By.desc("Move down")))
        val touch = driver.touchDown(checkNotNull(driver.device.findObject(By.desc("Move left"))))
        try {
            SystemClock.sleep(ViewConfiguration.getLongPressTimeout().toLong() + 250)
        } finally { driver.cancelTouch(touch) }
        driver.device.waitForIdle()
        val after = stats()
        assertTrue("Expected repeated movement", after.getValue("selectionStart") in 1..13)
        assertEquals(after.getValue("selectionStart"), after.getValue("selectionEnd"))
        SystemClock.sleep(250)
        val settled = stats()
        assertEquals(after.getValue("selectionStart"), settled.getValue("selectionStart"))
        assertEquals(after.getValue("keyDown"), settled.getValue("keyDown"))
        driver.tapKey("Home")
        awaitSelection(0, 0)
        driver.tapKey("End")
        awaitSelection(16, 16)
        noPayloadReads()
    }

    @Test fun rawEditorsHideMenuCommandsAndPasswordEditorsHideEntry() {
        driver.launchComposingQa("raw")
        val rawMode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            assertTrue(rawMode.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null))
        }
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Move left")), 3_000))
        for (label in listOf("Select all", "Copy", "Cut", "Paste"))
            assertNull(driver.device.findObject(By.desc(label)))
        driver.launchComposingQa("password")
        val passwordMode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            val node = passwordMode.createAccessibilityNodeInfo()
            try {
                assertFalse(node.actionList.any { it.id == AccessibilityNodeInfo.ACTION_LONG_CLICK })
            } finally { node.recycle() }
        }
        assertNull(driver.device.findObject(By.desc("Paste")))
        noPayloadReads()
    }

    @Test fun multilineArrowsPreserveColumnAndExtendAcrossLineBoundary() {
        driver.launchComposingQa("multiline")
        type("abcd")
        driver.tapKeyByDescription(context.getString(R.string.key_enter))
        type("efgh")
        driver.awaitFieldText("qa_composing_text", "abcd\nefgh")
        openPanel()
        driver.tapKeyByDescription("Move up")
        awaitSelection(4, 4)
        driver.tapKey("Home")
        awaitSelection(0, 0)
        driver.tapKeyByDescription("Move down")
        awaitSelection(5, 5)
        driver.tapKey("End")
        awaitSelection(9, 9)
        driver.tapKeyByDescription("Selection off")
        driver.tapKeyByDescription("Move up")
        awaitSelection(9, 4)
        driver.tapKeyByDescription("Selection on")
        driver.tapKeyByDescription("Move right")
        awaitSelection(9, 9)
        noPayloadReads()
    }

    @Test fun restartClearsSelectionModeAndFreshFieldDoesNotInheritTheForeignBoundary() {
        type("old")
        openPanel()
        driver.tapKeyByDescription("Selection off")
        // tapQaControl waits for Delete, which is intentionally absent from EDITING.
        checkNotNull(driver.device.findObject(By.res(context.packageName, "qa_composing_restart"))).click()
        driver.device.waitForIdle()
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Selection off")), 3_000))
        assertNull(driver.device.findObject(By.desc("Selection on")))
        driver.awaitFieldText("qa_composing_text", "old")
        // New Activity/editor instance with the same package and resource ID is a fresh start.
        // Public correction behavior proves the previous protective flag was not inherited.
        driver.launchComposingQa()
        type("teh")
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
        space()
        driver.awaitFieldText("qa_composing_text", "the ")
        noPayloadReads()
    }

    @Test fun hideAndShowKeepPastedSuffixLiteralUntilOwnBoundary() {
        type("old")
        openPanel()
        instrumentation.runOnMainSync {
            clipboardTouched = true
            context.getSystemService(ClipboardManager::class.java)
                .setPrimaryClip(ClipData.newPlainText("Rune QA", "foreign"))
        }
        driver.tapKeyByDescription("Paste")
        driver.awaitFieldText("qa_composing_text", "oldforeign")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        driver.device.pressBack()
        assertTrue(driver.device.wait(Until.gone(By.desc(context.getString(R.string.key_delete))), 3_000))
        checkNotNull(driver.device.findObject(By.res(context.packageName, "qa_composing_text"))).click()
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.key_delete))), 3_000))
        type("teh"); space()
        driver.awaitFieldText("qa_composing_text", "oldforeignteh ")
        type("teh"); space()
        driver.awaitFieldText("qa_composing_text", "oldforeignteh the ")
        noPayloadReads()
    }

    @Test fun realServiceRebindCannotCorrectThePastedAdjacentSuffix() {
        type("old")
        openPanel()
        instrumentation.runOnMainSync {
            clipboardTouched = true
            context.getSystemService(ClipboardManager::class.java)
                .setPrimaryClip(ClipData.newPlainText("Rune QA", "foreign"))
        }
        driver.tapKeyByDescription("Paste")
        driver.awaitFieldText("qa_composing_text", "oldforeign")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        fun serviceOwner(): io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService {
            var owner: android.content.Context = keyboardSnapshot().keyboard.rootView.context
            while (owner is android.content.ContextWrapper && owner !is io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService)
                owner = owner.baseContext
            return checkNotNull(owner as? io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService)
        }
        val old = serviceOwner()
        driver.rebindRuneKeepingEditor()
        val fresh = serviceOwner()
        assertNotSame("Require actual framework service recreation", old, fresh)
        val controller = io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService::class.java
            .getDeclaredField("typingSession").apply { isAccessible = true }.get(fresh)
            as io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
        var enabled = false
        var fenced = false
        instrumentation.runOnMainSync { enabled = controller.state.enabled; fenced = controller.requiresExternalWordBoundary }
        assertTrue("Actual smart typing session must be enabled", enabled)
        assertTrue("Fresh service must fence its unknown left context", fenced)
        // The fallback IME may legitimately read its editor. Retain its transition counters;
        // only subsequent Rune typing is subject to this case's no-additional-read assertion.
        val baseline = stats()
        type("teh")
        var adopted = false
        instrumentation.runOnMainSync { adopted = controller.state.composing != null || controller.state.contextText.isNotEmpty() }
        assertFalse("Adjacent unknown suffix must not be adopted", adopted)
        space()
        driver.awaitFieldText("qa_composing_text", "oldforeignteh ")
        type("teh"); space()
        driver.awaitFieldText("qa_composing_text", "oldforeignteh the ")
        val after = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Rune added a payload read: $name", baseline.getValue(name), after.getValue(name))
    }

    private fun openPanel() {
        val mode = keyboardSnapshot().keys.single { it.contentDescription == context.getString(R.string.key_symbols) }
        instrumentation.runOnMainSync {
            assertTrue(mode.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null))
        }
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Paste")), 3_000))
    }
    private fun type(value: String) = value.forEach { driver.tapKey(it.toString()) }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(context.packageName, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('='); name to value.toInt()
    }
    private fun awaitSelection(start: Int, end: Int) {
        val deadline = SystemClock.uptimeMillis() + 3_000
        do {
            val counts = stats()
            if (counts["selectionStart"] == start && counts["selectionEnd"] == end) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Fixed public selection did not reach $start,$end; numeric fixture stats=${stats()}")
    }
    private fun noPayloadReads() {
        val counts = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $name", 0, counts.getValue(name))
    }
}
