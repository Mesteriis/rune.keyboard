package io.github.mesteriis.rune.keyboard.qa

import android.content.ClipData
import android.content.ClipboardManager
import android.os.SystemClock
import android.view.View
import android.view.ViewGroup
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.EditText
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.SetupActivity
import org.junit.Assert.*
import org.junit.Test

/** Actual embedded preview keys and its own editor; clipboard data is a test-owned sentinel. */
class EditingPreviewInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext

    @Test fun previewNavigationSelectionAndNativeClipboardCommandsEditOnlyTheSample() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish"))
        var clipboardTouched = false
        try {
            ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val field = activity.findViewById<EditText>(R.id.menu_try_input)
                    assertFalse(field.showSoftInputOnFocus)
                    field.setText("abcd")
                    field.setSelection(4)
                    val mode = keys(activity).single { it.contentDescription == activity.getString(R.string.key_symbols) }
                    assertTrue(mode.performAccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, null))
                }
                click(scenario, "Selection off")
                click(scenario, "Move left")
                awaitSample(scenario, "abcd", 4, 3)
                clipboardTouched = true
                click(scenario, "Cut")
                awaitSample(scenario, "abc", 3, 3)
                scenario.onActivity {
                    context.getSystemService(ClipboardManager::class.java)
                        .setPrimaryClip(ClipData.newPlainText("Rune QA", "X"))
                }
                click(scenario, "Paste")
                awaitSample(scenario, "abcX", 4, 4)
                click(scenario, "Line start")
                awaitSample(scenario, "abcX", 0, 0)
                click(scenario, "Line end")
                awaitSample(scenario, "abcX", 4, 4)
                click(scenario, "Select all")
                awaitSample(scenario, "abcX", 0, 4)
                click(scenario, "Copy")
                scenario.onActivity {
                    assertEquals("abcX", context.getSystemService(ClipboardManager::class.java)
                        .primaryClip?.getItemAt(0)?.text?.toString())
                    assertFalse(it.findViewById<EditText>(R.id.menu_try_input).showSoftInputOnFocus)
                }
            }
        } finally {
            if (clipboardTouched) instrumentation.runOnMainSync {
                context.getSystemService(ClipboardManager::class.java).clearPrimaryClip()
            }
        }
    }

    private fun click(scenario: ActivityScenario<SetupActivity>, description: String) {
        scenario.onActivity { activity ->
            assertTrue(keys(activity).single { it.contentDescription == description }.performClick())
        }
        instrumentation.waitForIdleSync()
    }
    private fun keys(activity: SetupActivity): List<View> {
        fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
            (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
        return descendants(activity.findViewById(R.id.menu_preview)).filter { it.isClickable }
    }
    private fun awaitSample(scenario: ActivityScenario<SetupActivity>, text: String, start: Int, end: Int) {
        val deadline = SystemClock.uptimeMillis() + 3_000
        var lastStart = -1
        var lastEnd = -1
        do {
            var matches = false
            scenario.onActivity {
                val field = it.findViewById<EditText>(R.id.menu_try_input)
                lastStart = field.selectionStart
                lastEnd = field.selectionEnd
                matches = field.text.toString() == text && lastStart == start && lastEnd == end
            }
            if (matches) return
            SystemClock.sleep(30)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Public preview fixture did not reach expected selection $start,$end; actual=$lastStart,$lastEnd")
    }
}
