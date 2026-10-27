package io.github.mesteriis.rune.keyboard.qa

import android.view.View
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Optional presentation control, exercised through native settings and the actual IME. */
@Suppress("DEPRECATION")
class EmojiKeySettingsInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val preferences get() = KeyboardPreferences(context)
    private val driver = ImeTestDriver()
    private var prepared = false

    @Before fun prepare() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish"))
        prepared = true
        driver.setUp()
        preferences.writeEmojiKey(false)
    }

    @After fun restore() { if (prepared) driver.tearDown() }

    @Test fun searchFindsNativeAppearanceSwitchAndChoiceSurvivesRecreation() {
        preferences.writeCandidateStrip(false)
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, null)).use { scenario ->
            scenario.onActivity { activity ->
                activity.findViewById<EditText>(R.id.menu_search).setText(activity.getString(R.string.settings_emoji_key))
            }
            checkNotNull(driver.device.wait(Until.findObject(By.text(context.getString(R.string.settings_emoji_key))
                .clazz(TextView::class.java)), 3_000)).click()
            instrumentation.waitForIdleSync()
            scenario.onActivity { activity ->
                val row = row(activity)
                val toggle = row.findViewById<Switch>(R.id.row_checkbox)
                val node = toggle.createAccessibilityNodeInfo()
                try {
                    assertEquals("android.widget.Switch", node.className.toString())
                    assertTrue(node.isCheckable && node.isEnabled)
                    assertFalse(node.isChecked)
                    assertTrue(node.contentDescription.contains(activity.getString(R.string.settings_emoji_key)))
                    assertTrue(node.actionList.any { it.id == AccessibilityNodeInfo.ACTION_CLICK })
                } finally { node.recycle() }
                assertEquals(View.IMPORTANT_FOR_ACCESSIBILITY_NO, row.importantForAccessibility)
                toggle.requestRectangleOnScreen(android.graphics.Rect(0, 0, toggle.width, toggle.height), true)
            }
            val prefix = context.getString(R.string.settings_emoji_key) + "\n"
            checkNotNull(driver.device.wait(Until.findObject(By.res(context.packageName, "row_checkbox").descStartsWith(prefix)), 3_000)).click()
            instrumentation.waitForIdleSync()
            assertTrue(KeyboardPreferences(context).readSettings().emojiKey)
            assertFalse(preferences.readSettings().candidateStrip)
            scenario.recreate()
            scenario.onActivity { activity ->
                val toggle = row(activity).findViewById<Switch>(R.id.row_checkbox)
                assertTrue(toggle.isChecked)
                assertTrue(toggle.performAccessibilityAction(AccessibilityNodeInfo.ACTION_CLICK, null))
            }
            assertFalse(KeyboardPreferences(context).readSettings().emojiKey)
            driver.device.pressBack()
            assertNotNull(driver.device.wait(Until.findObject(By.res(context.packageName, "menu_search")), 3_000))
        }
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.APPEARANCE)).use { scenario ->
            scenario.onActivity { activity -> assertFalse(row(activity).findViewById<Switch>(R.id.row_checkbox).isChecked) }
        }
    }

    @Test fun livePreferenceAddsAndRemovesOnlyLettersEntryAndPreviewAlsoUsesIt() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true)
        driver.launchComposingQa()
        assertNull(driver.device.findObject(By.desc("Emoji")))
        preferences.writeEmojiKey(true)
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Emoji")), 3_000))
        "teh".forEach { driver.tapKey(it.toString()) }
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
        driver.tapKeyByDescription("Emoji")
        checkNotNull(driver.device.wait(Until.findObject(By.desc("grinning face")), 3_000)).click()
        driver.awaitFieldText("qa_composing_text", "teh😀")
        driver.tapKeyByDescription(context.getString(R.string.key_letters))
        preferences.writeEmojiKey(false)
        assertTrue(driver.device.wait(Until.gone(By.desc("Emoji")), 3_000))
        driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        assertNotNull(driver.device.wait(Until.findObject(By.desc("Emoji")), 3_000))
        preferences.writeEmojiKey(true)
        ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                assertFalse(activity.findViewById<EditText>(R.id.menu_try_input).showSoftInputOnFocus)
                val preview = descendants(activity.findViewById(R.id.menu_preview))
                assertEquals(1, preview.count { it.contentDescription == "Emoji" })
            }
        }
    }

    @Test fun enabledKeyRemainsAbsentInSensitiveRawAndNumericEditors() {
        preferences.writeEmojiKey(true)
        for (mode in listOf("password", "raw", "number", "phone", "date_time")) {
            driver.launchComposingQa(mode)
            assertNull("Emoji must stay hidden in $mode", driver.device.findObject(By.desc("Emoji")))
            if (mode == "password" || mode == "raw") {
                driver.tapKeyByDescription(context.getString(R.string.key_symbols))
                assertNull(driver.device.findObject(By.desc("Emoji")))
            }
        }
    }

    private fun row(activity: SettingsActivity): View = checkNotNull(activity
        .findViewById<LinearLayout>(R.id.settings_container).findViewWithTag(R.string.settings_emoji_key))

    private fun descendants(view: View): List<View> = listOf(view) + if (view is android.view.ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
}
