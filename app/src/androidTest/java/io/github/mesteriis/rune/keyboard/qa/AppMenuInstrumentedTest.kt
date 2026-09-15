package io.github.mesteriis.rune.keyboard.qa

import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.*
import org.junit.Assert.*
import org.junit.Test

/** Synthetic local editor and settings navigation; never touches a physical device or model download. */
class AppMenuInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext

    @Test fun homeThemeChoicesPersistAndPreviewEditsOnlyTheSample() {
        val preferences = KeyboardPreferences(context)
        val before = preferences.readSettings()
        try {
            ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val choices = activity.findViewById<LinearLayout>(R.id.menu_theme_choices)
                    val field = activity.findViewById<EditText>(R.id.menu_try_input)
                    field.setText("test")
                    field.setSelection(4)
                    KeyboardTheme.entries.forEachIndexed { index, theme ->
                        assertTrue(choices.getChildAt(index).performClick())
                        assertEquals(theme, preferences.readSettings().keyboardTheme)
                        assertEquals("test", field.text.toString())
                        assertTrue(choices.getChildAt(index).isSelected)
                    }
                    val delete = descendants(activity.findViewById(R.id.menu_preview)).first {
                        it.contentDescription == activity.getString(R.string.key_delete)
                    }
                    assertTrue(delete.performClick())
                    assertEquals("tes", field.text.toString())
                    val enter = descendants(activity.findViewById(R.id.menu_preview)).first {
                        it.contentDescription == activity.getString(R.string.key_enter)
                    }
                    assertTrue(enter.performClick())
                    assertEquals("tes\n", field.text.toString())
                }
                scenario.recreate()
                scenario.onActivity { activity ->
                    assertTrue(activity.findViewById<EditText>(R.id.menu_try_input).text.isEmpty())
                    assertTrue(activity.findViewById<LinearLayout>(R.id.menu_theme_choices).getChildAt(4).isSelected)
                }
            }
            assertEquals(before.copy(keyboardTheme = KeyboardTheme.SILENT), preferences.readSettings())
        } finally { preferences.writeKeyboardTheme(before.keyboardTheme) }
    }

    @Test fun searchOpensMatchingControlAndBackRestoresQuery() {
        val preferences = KeyboardPreferences(context)
        val before = preferences.readSettings()
        try {
            ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val label = activity.getString(R.string.settings_number_row)
                    activity.findViewById<EditText>(R.id.menu_search).setText(label)
                    val result = descendants(activity.window.decorView).filterIsInstance<TextView>().single {
                        it !is EditText && it.text.toString() == label
                    }
                    clickableParent(result).performClick()
                    assertEquals(activity.getString(R.string.menu_appearance), activity.findViewById<TextView>(R.id.menu_detail_title).text)
                    val row = activity.findViewById<LinearLayout>(R.id.settings_container).findViewWithTag<View>(R.string.settings_number_row)
                    assertTrue(row.performClick())
                    assertEquals(!before.numberRow, preferences.readSettings().numberRow)
                }
                scenario.recreate()
                scenario.onActivity { activity ->
                    val row = activity.findViewById<LinearLayout>(R.id.settings_container).findViewWithTag<View>(R.string.settings_number_row)
                    assertEquals(!before.numberRow, row.findViewById<CheckBox>(R.id.row_checkbox).isChecked)
                    activity.findViewById<View>(R.id.menu_back).performClick()
                    val search = activity.findViewById<EditText>(R.id.menu_search)
                    assertEquals(activity.getString(R.string.settings_number_row), search.text.toString())
                    search.setText("zzzznoresult")
                    assertTrue(descendants(activity.window.decorView).filterIsInstance<TextView>().any {
                        it.text.toString() == activity.getString(R.string.menu_empty)
                    })
                }
            }
        } finally { preferences.writeNumberRow(before.numberRow) }
    }

    @Test fun previewDeletesWholeUnicodeCodePointAndReplacesSelections() {
        instrumentation.runOnMainSync {
            val field = EditText(context).apply { setText("A😀"); setSelection(3) }
            val state = io.github.mesteriis.rune.keyboard.ime.model.KeyboardState(io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.ENGLISH)
            val editor = io.github.mesteriis.rune.keyboard.ime.model.EditorContext.from(android.text.InputType.TYPE_CLASS_TEXT, 0)
            PreviewEditor.apply(field, state, io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction.Delete, editor)
            assertEquals("A", field.text.toString())
            field.setSelection(0, 1)
            PreviewEditor.apply(field, state, io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction.CommitText("ok"), editor)
            assertEquals("ok", field.text.toString())
        }
    }

    @Test fun detailHeaderRespectsStatusBarInsets() {
        ActivityScenario.launch(KeyboardSetupActivity::class.java).use { scenario ->
            instrumentation.waitForIdleSync()
            scenario.onActivity { activity ->
                val title = activity.findViewById<TextView>(R.id.menu_detail_title)
                val position = IntArray(2)
                title.getLocationOnScreen(position)
                if (android.os.Build.VERSION.SDK_INT >= 30) {
                    val top = activity.window.decorView.rootWindowInsets.getInsets(android.view.WindowInsets.Type.statusBars()).top
                    assertTrue("Header overlaps status bar: y=${position[1]}, inset=$top", position[1] >= top)
                }
                assertTrue(title.width > 0)
            }
        }
    }

    private fun clickableParent(view: View): View = if (view.isClickable) view else clickableParent(view.parent as View)
    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
}
