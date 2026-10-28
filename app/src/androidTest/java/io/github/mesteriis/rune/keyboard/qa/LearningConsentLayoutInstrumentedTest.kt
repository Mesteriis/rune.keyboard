package io.github.mesteriis.rune.keyboard.qa

import android.app.Dialog
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Build
import android.os.LocaleList
import android.view.ContextThemeWrapper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.SettingsActivity
import io.github.mesteriis.rune.keyboard.settings.SettingsPage
import io.github.mesteriis.rune.keyboard.settings.SettingsToggleRow
import java.util.Locale
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Attached consent-row fixture on disposable emulators; no toggle/reset/editor actions. */
@Suppress("DEPRECATION")
class LearningConsentLayoutInstrumentedTest {
    @Before fun requireDisposableEmulator() {
        check(Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
    }

    private fun assertDisclosures(language: String) {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val base = instrumentation.targetContext
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(base, SettingsPage.DICTIONARY)).use { scenario ->
            for (scale in listOf(1f, 1.3f)) {
                for ((title, description) in listOf(
                    R.string.settings_personal_learning to R.string.settings_personal_learning_summary,
                    R.string.settings_collect_examples to R.string.settings_collect_examples_summary,
                    R.string.settings_typo_patterns to R.string.settings_typo_patterns_summary,
                )) {
                    var dialog: Dialog? = null
                    var row: View? = null
                    try {
                        scenario.onActivity { activity ->
                            val configuration = Configuration(activity.resources.configuration).apply {
                                setLocales(LocaleList(Locale.forLanguageTag(language)))
                                fontScale = scale
                            }
                            val themed = ContextThemeWrapper(activity.createConfigurationContext(configuration),
                                R.style.Theme_RuneKeyboard_Setup)
                            val content = LayoutInflater.from(themed).inflate(R.layout.view_settings_row, null)
                            content.findViewById<TextView>(R.id.row_title).setText(title)
                            content.findViewById<TextView>(R.id.row_summary).apply {
                                setText(description)
                                visibility = View.VISIBLE
                            }
                            SettingsToggleRow.bind(content, checked = false)
                            row = content
                            dialog = Dialog(activity).apply {
                                setContentView(ScrollView(themed).apply { addView(content) })
                                show()
                                checkNotNull(window).apply {
                                    setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
                                    setLayout((320 * themed.resources.displayMetrics.density).toInt(),
                                        ViewGroup.LayoutParams.MATCH_PARENT)
                                }
                            }
                        }
                        // Attachment/traversal must happen before requesting the real node.
                        instrumentation.waitForIdleSync()
                        scenario.onActivity {
                            val content = checkNotNull(row)
                            assertTrue(content.isAttachedToWindow)
                            val summary = content.findViewById<TextView>(R.id.row_summary)
                            val layout = checkNotNull(summary.layout)
                            assertTrue("Long consent must wrap", layout.lineCount > 1)
                            assertEquals(summary.text.length, layout.getLineEnd(layout.lineCount - 1))
                            for (line in 0 until layout.lineCount) assertEquals(0, layout.getEllipsisCount(line))
                            assertTrue(summary.measuredHeight >= layout.height)
                            val toggle = content.findViewById<Switch>(R.id.row_checkbox)
                            val node = checkNotNull(toggle.createAccessibilityNodeInfo())
                            try {
                                assertTrue(node.isCheckable)
                                assertTrue(node.contentDescription.toString().contains(summary.text.toString()))
                            } finally { node.recycle() }
                        }
                    } finally { scenario.onActivity { dialog?.dismiss() } }
                }
            }
        }
    }

    @Test fun englishConsentWrapsAndKeepsFullSwitchLabel() = assertDisclosures("en")
    @Test fun russianConsentWrapsAndKeepsFullSwitchLabel() = assertDisclosures("ru")
}
