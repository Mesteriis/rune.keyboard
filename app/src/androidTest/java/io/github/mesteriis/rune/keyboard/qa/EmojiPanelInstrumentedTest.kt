package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.content.ContextWrapper
import android.os.Build
import android.os.SystemClock
import android.graphics.Rect
import android.view.View
import android.view.ViewGroup
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.GridView
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiEntry
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assume.assumeTrue
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Selected native controls in an isolated QA editor; no arbitrary text injection. */
class EmojiPanelInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false
    private var privateInput = false
    private var stores: Map<String, Map<String, String>>? = null

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        val emulator = Build.HARDWARE in setOf("ranchu", "goldfish")
        val fold = Build.MODEL.startsWith("SM-F") && args.getString("allowPhysicalDevice") == "true" &&
            args.getString("runeFailureArtifacts") == "false"
        assumeTrue("Owned emulator or explicitly authorized Fold required", emulator || fold)
        privateInput = fold || emulator && args.getString("runeEmojiPrivateFixture") == "true"
        if (privateInput) flushDiagnostics()
        stores = personalStoreSnapshot(context).let { snapshot ->
            if (privateInput) snapshot else snapshot.filterKeys { it != "typing-diagnostics" }
        }
        prepared = true
        driver.setUp(privateQa = privateInput)
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        assertTrue(edit.commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false, doubleSpace = false)
        if (!privateInput) driver.launchComposingQa()
    }

    @After fun restore() {
        try {
            if (privateInput && stores != null) flushDiagnostics()
            stores?.let { before ->
                val after = personalStoreSnapshot(context).let { snapshot ->
                    if (privateInput) snapshot else snapshot.filterKeys { it != "typing-diagnostics" }
                }
                assertEquals("Synthetic QA changed personal stores", before, after)
            }
        } finally { if (prepared) driver.tearDown() }
    }

    private fun flushDiagnostics() {
        val recorder = TypingDiagnosticsProvider.create(context) as DiagnosticsRecorder
        val done = CountDownLatch(1)
        var success = false
        recorder.barrier { success = it; done.countDown() }
        assertTrue("Diagnostics queue fence timed out", done.await(5, TimeUnit.SECONDS))
        assertTrue("Diagnostics queue fence failed", success)
    }

    @Test fun paletteCommitIsLiteralRecentsAreNamedAndPanelHeightStaysFourRows() {
        assumeTrue("Recents are hidden in private editors", !privateInput)
        "teh".forEach { driver.tapKey(it.toString()) }
        val before = contentHeight()
        openPanel()
        assertEquals(before, contentHeight())
        clickEmoji("smileys", "😀")
        driver.awaitFieldText("qa_composing_text", "teh😀")
        noPayloadReads()
        clickTab("Recent emoji")
        assertNotNull(driver.device.wait(Until.findObject(By.desc("grinning face")), 3_000))
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        "teh".forEach { driver.tapKey(it.toString()) }
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
        driver.tapKeyByDescription(context.getString(R.string.key_space))
        driver.awaitFieldText("qa_composing_text", "teh😀the ")
        noPayloadReads()
    }

    @Test fun privatePaletteKeepsHeightAndInsertsEmojiWithoutReadingEditor() {
        if (!privateInput) driver.launchComposingQa("private")
        driver.tapKey("a")
        val before = contentHeight()
        openPanel()
        assertEquals(before, contentHeight())
        assertNull(driver.device.findObject(By.desc("Recent emoji")))
        clickEmoji("smileys", "😀")
        driver.awaitFieldText("qa_composing_text", "a😀")
        noPayloadReads()
    }

    @Test fun privateWebViewEmojiDeletionAndContinuation() {
        driver.launchWebViewQa(privateInput = true)
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            var owner = keyboard.rootView.context
            while (owner is ContextWrapper && owner !is RuneInputMethodService) owner = owner.baseContext
            val service = checkNotNull(owner as? RuneInputMethodService)
            assertTrue("WebView must request no personalized learning",
                service.currentInputEditorInfo.imeOptions and android.view.inputmethod.EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING != 0)
        }
        driver.tapKey("a")
        awaitWebText("a")
        openPanel()
        for ((category, glyph) in listOf("people" to "👩‍💻", "flags" to "🇪🇸")) {
            clickEmoji(category, glyph)
            awaitWebText("a$glyph")
            driver.tapKeyByDescription(context.getString(R.string.key_delete))
            awaitWebText("a")
            noPayloadReads(web = true)
        }
        clickEmoji("people", "👩‍💻")
        awaitWebText("a👩‍💻")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        driver.tapKey("b")
        awaitWebText("a👩‍💻b")
        noPayloadReads(web = true)
    }

    private fun awaitWebText(expected: String) {
        val selector = By.pkg(context.packageName).clazz(android.widget.EditText::class.java)
        val deadline = SystemClock.uptimeMillis() + 10_000
        do {
            if (driver.device.findObject(selector)?.text == expected) return
            SystemClock.sleep(25)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("WebView synthetic text did not reach the expected value")
    }

    @Test fun privateEmojiExternalRewriteKeepsEditorText() {
        if (!privateInput) driver.launchComposingQa("private")
        driver.tapKey("a")
        openPanel()
        clickEmoji("people", "👩‍💻")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        driver.tapQaControl("qa_composing_rewrite")
        driver.awaitFieldText("qa_composing_text", "editor")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        driver.tapKey("b")
        driver.awaitFieldText("qa_composing_text", "editorb")
        noPayloadReads()
    }

    @Test fun privateEmojiExternalCursorMoveDoesNotDeleteEmoji() {
        if (!privateInput) driver.launchComposingQa("private")
        driver.tapKey("a")
        openPanel()
        clickEmoji("people", "👩‍💻")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        driver.tapQaControl("qa_composing_cursor")
        driver.tapKeyByDescription(context.getString(R.string.key_delete))
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        driver.tapKey("b")
        driver.awaitFieldText("qa_composing_text", "ba👩‍💻")
        noPayloadReads()
    }

    @Test fun privateEmojiDroppedCompositionKeepsEmojiAndNextInput() {
        if (!privateInput) driver.launchComposingQa("private")
        driver.tapKey("a")
        openPanel()
        clickEmoji("people", "👩‍💻")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        driver.tapQaControl("qa_composing_drop")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        driver.tapKey("b")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻b")
        noPayloadReads()
    }

    @Test fun privateComplexEmojiDeletionNeverReadsEditor() {
        driver.launchComposingQa("private")
        supportedZwjAndFlagInsertFromGridAndDeleteAsOneGrapheme()
        noPayloadReads()
        driver.launchComposingQa("private")
        modifierCommitTextIsLiteralAcrossBinderAndDeletesAsOneGrapheme()
        noPayloadReads()
    }

    @Test fun privateEmojiThenLetterPreservesBothWithoutPayloadReads() {
        if (!privateInput) driver.launchComposingQa("private")
        driver.tapKey("a")
        openPanel()
        clickEmoji("people", "👩‍💻")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        driver.tapKey("b")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻b")
        noPayloadReads()
    }

    @Test fun supportedZwjAndFlagInsertFromGridAndDeleteAsOneGrapheme() {
        driver.tapKey("a")
        openPanel()
        clickEmoji("people", "👩‍💻")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        noPayloadReads()
        driver.tapKeyByDescription(context.getString(R.string.key_delete))
        driver.awaitFieldText("qa_composing_text", "a")
        if (privateInput) noPayloadReads()
        clickEmoji("flags", "🇪🇸")
        driver.awaitFieldText("qa_composing_text", "a🇪🇸")
        driver.tapKeyByDescription(context.getString(R.string.key_delete))
        driver.awaitFieldText("qa_composing_text", "a")
        if (privateInput) noPayloadReads()
    }

    @Test fun incognitoShowsEmojiButHidesRecents() {
        if (!privateInput) driver.launchComposingQa("private")
        openPanel()
        assertNull(driver.device.findObject(By.desc("Recent emoji")))
        clickEmoji("smileys", "😀")
        driver.awaitFieldText("qa_composing_text", "😀")
        noPayloadReads()
    }

    @Test fun modifierCommitTextIsLiteralAcrossBinderAndDeletesAsOneGrapheme() {
        "teh".forEach { driver.tapKey(it.toString()) }
        openPanel()
        // Tone selection is a separate UI stage. Exercise the existing service action
        // boundary with fixed synthetic Unicode sequences, without changing the catalog.
        for (glyph in listOf("👍🏽", "🧑🏽‍💻")) {
            val before = payloadReads()
            val keyboard = keyboardSnapshot().keyboard
            var result: Result<Unit>? = null
            instrumentation.runOnMainSync {
                result = runCatching {
                    var owner = keyboard.rootView.context
                    while (owner is ContextWrapper && owner !is RuneInputMethodService) {
                        val next = owner.baseContext
                        check(next !== owner)
                        owner = next
                    }
                    val service = checkNotNull(owner as? RuneInputMethodService)
                    val action = RuneInputMethodService::class.java.getDeclaredMethod("handleAction", KeyboardAction::class.java)
                    action.isAccessible = true
                    action.invoke(service, KeyboardAction.CommitText(glyph))
                }
            }
            checkNotNull(result).getOrThrow()
            driver.awaitFieldText("qa_composing_text", "teh$glyph")
            assertEquals("Isolated insertion must not read editor payload", before, payloadReads())
            driver.tapKeyByDescription(context.getString(R.string.key_delete))
            driver.awaitFieldText("qa_composing_text", "teh")
            if (privateInput) assertEquals("Private deletion must not read editor payload", before, payloadReads())
        }
    }

    private fun openPanel() {
        driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        driver.tapKeyByDescription("Emoji")
        assertNotNull(driver.device.wait(Until.findObject(By.clazz(GridView::class.java)), 3_000))
    }

    private fun contentHeight(): Int {
        val keyboard = keyboardSnapshot().keyboard
        var height = 0
        instrumentation.runOnMainSync { height = keyboard.getChildAt(keyboard.childCount - 1).height }
        return height
    }

    private fun clickEmoji(category: String, glyph: String) {
        val title = mapOf("smileys" to "Smileys & Emotion", "people" to "People & Body", "flags" to "Flags").getValue(category)
        clickTab(title)
        var name = ""
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            val grid = descendants(keyboard).filterIsInstance<GridView>().single()
            val position = (0 until grid.adapter.count).single { (grid.adapter.getItem(it) as EmojiEntry).glyph == glyph }
            name = (grid.adapter.getItem(position) as EmojiEntry).names.english
            // Scroll the actual native adapter, then activate the exposed, named cell through accessibility.
            grid.setSelection(position)
        }
        val cell = checkNotNull(driver.device.wait(Until.findObject(By.desc(name)), 3_000))
        var accessible = false
        instrumentation.runOnMainSync {
            val node = descendants(keyboard).single { it.contentDescription?.toString() == name }.createAccessibilityNodeInfo()
            try {
                accessible = node.className == "android.widget.TextView" &&
                    node.actionList.any { it.id == AccessibilityNodeInfo.ACTION_CLICK }
            } finally { node.recycle() }
        }
        assertTrue("Emoji must expose a named native TextView click action", accessible)
        cell.click()
    }

    private fun clickTab(description: String) {
        val keyboard = keyboardSnapshot().keyboard
        var selected: View? = null
        instrumentation.runOnMainSync {
            selected = descendants(keyboard).single { it.contentDescription?.toString() == description }
            selected!!.requestRectangleOnScreen(Rect(0, 0, selected!!.width, selected!!.height), true)
        }
        checkNotNull(driver.device.wait(Until.findObject(By.desc(description)), 3_000)).click()
        instrumentation.waitForIdleSync()
        var namedAction = false
        instrumentation.runOnMainSync {
            val node = descendants(keyboard).single { it.contentDescription?.toString() == description }.createAccessibilityNodeInfo()
            try {
                namedAction = !node.contentDescription.isNullOrBlank() && node.isSelected &&
                    node.actionList.any { it.id == AccessibilityNodeInfo.ACTION_CLICK }
            } finally { node.recycle() }
        }
        assertTrue("Category must expose a named, selected native click action", namedAction)
    }

    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()

    private fun payloadReads(web: Boolean = false): Map<String, Int> {
        val id = if (web) "qa_webview_stats" else "qa_composing_stats"
        val counts = checkNotNull(driver.device.findObject(By.res(context.packageName, id))).text
            .orEmpty().split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
        return counts.filterKeys { it in setOf("before", "after", "selected", "extracted", "surrounding", "snapshot") }
    }

    private fun noPayloadReads(web: Boolean = false) {
        val counts = payloadReads(web)
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $name", 0, counts.getValue(name))
    }
}
