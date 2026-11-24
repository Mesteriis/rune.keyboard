package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.os.Debug
import android.os.SystemClock
import android.view.View
import android.view.ViewGroup
import android.widget.GridView
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import org.junit.After
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/** Exploratory process snapshots; no memory or performance budget is asserted. */
class EmojiMemoryMeasurementInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false

    @Before fun prepare() {
        assumeTrue("Explicit emoji memory measurement required",
            InstrumentationRegistry.getArguments().getString("runeEmojiMemory") == "true")
        check(Build.HARDWARE in setOf("ranchu", "goldfish"))
        prepared = true
        driver.setUp()
        driver.launchComposingQa()
    }

    @After fun restore() { if (prepared) driver.tearDown() }

    @Test fun observeProcessMemoryBeforeAfterOpeningAndVisitingCategories() {
        SystemClock.sleep(5_000)
        measure("before")
        driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        driver.tapKeyByDescription("Emoji")
        assertNotNull(driver.device.wait(Until.findObject(By.clazz(GridView::class.java)), 5_000))
        instrumentation.waitForIdleSync()
        assertPopulatedGrid()
        SystemClock.sleep(1_000)
        measure("first_category")
        for (title in listOf("People & Body", "Animals & Nature", "Food & Drink", "Travel & Places",
                "Activities", "Objects", "Symbols", "Flags")) {
            val keyboard = keyboardSnapshot().keyboard
            instrumentation.runOnMainSync {
                val tab = descendants(keyboard).single { it.contentDescription?.toString() == title }
                tab.requestRectangleOnScreen(Rect(0, 0, tab.width, tab.height), true)
            }
            checkNotNull(driver.device.wait(Until.findObject(By.desc(title)), 5_000)).click()
            instrumentation.waitForIdleSync()
            instrumentation.runOnMainSync {
                val tab = descendants(keyboard).single { it.contentDescription?.toString() == title }
                val node = tab.createAccessibilityNodeInfo()
                try { assertTrue("Category was not selected: $title", node.isSelected) }
                finally { node.recycle() }
            }
            assertPopulatedGrid()
        }
        SystemClock.sleep(1_000)
        measure("all_categories")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        SystemClock.sleep(1_000)
        measure("after_closing")
        Runtime.getRuntime().gc()
        SystemClock.sleep(2_000)
        measure("after_gc_request")
        driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        driver.tapKeyByDescription("Emoji")
        assertNotNull(driver.device.wait(Until.findObject(By.clazz(GridView::class.java)), 5_000))
        instrumentation.waitForIdleSync()
        assertPopulatedGrid()
        SystemClock.sleep(1_000)
        measure("after_reopening")
    }

    private fun assertPopulatedGrid() {
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            val grid = descendants(keyboard).filterIsInstance<GridView>().single()
            assertTrue("Emoji grid must contain items", grid.adapter.count > 0 && grid.childCount > 0)
        }
    }

    private fun measure(stage: String) {
        val memory = Debug.MemoryInfo()
        Debug.getMemoryInfo(memory)
        val runtime = Runtime.getRuntime()
        instrumentation.sendStatus(2, Bundle().apply {
            putString("emoji_memory_stage", stage)
            putInt("emoji_memory_api", Build.VERSION.SDK_INT)
            putInt("emoji_memory_total_pss_kib", memory.totalPss)
            putLong("emoji_memory_java_used_bytes", runtime.totalMemory() - runtime.freeMemory())
            putLong("emoji_memory_native_allocated_bytes", Debug.getNativeHeapAllocatedSize())
        })
    }

    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
}
