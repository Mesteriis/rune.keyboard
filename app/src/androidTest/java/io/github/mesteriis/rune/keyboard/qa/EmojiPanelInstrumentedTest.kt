package io.github.mesteriis.rune.keyboard.qa

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
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Selected native controls in an isolated QA editor; no arbitrary text injection. */
class EmojiPanelInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false

    @Before fun prepare() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish"))
        prepared = true
        driver.setUp()
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
    }

    @After fun restore() { if (prepared) driver.tearDown() }

    @Test fun paletteCommitIsLiteralRecentsAreNamedAndPanelHeightStaysFourRows() {
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

    @Test fun supportedZwjAndFlagInsertFromGridAndDeleteAsOneGrapheme() {
        driver.tapKey("a")
        openPanel()
        clickEmoji("people", "👩‍💻")
        driver.awaitFieldText("qa_composing_text", "a👩‍💻")
        noPayloadReads()
        driver.tapKeyByDescription(context.getString(R.string.key_delete))
        driver.awaitFieldText("qa_composing_text", "a")
        clickEmoji("flags", "🇪🇸")
        driver.awaitFieldText("qa_composing_text", "a🇪🇸")
        driver.tapKeyByDescription(context.getString(R.string.key_delete))
        driver.awaitFieldText("qa_composing_text", "a")
    }

    @Test fun incognitoShowsEmojiButHidesRecents() {
        driver.launchComposingQa("private")
        openPanel()
        assertNull(driver.device.findObject(By.desc("Recent emoji")))
        clickEmoji("smileys", "😀")
        driver.awaitFieldText("qa_composing_text", "😀")
        noPayloadReads()
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

    private fun noPayloadReads() {
        val counts = checkNotNull(driver.device.findObject(By.res(context.packageName, "qa_composing_stats"))).text
            .orEmpty().split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $name", 0, counts.getValue(name))
    }
}
