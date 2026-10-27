package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.view.View
import android.view.ViewGroup
import android.widget.Switch
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.intelligence.inference.LifecycleModelInferenceService as Remote
import io.github.mesteriis.rune.keyboard.settings.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class UndoContinuityInstrumentedTest : ImeTestBase() {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun readyModelUndoSurvivesTheNextLetter() = modelUndo(late = false)
    @Test fun lateModelUndoSurvivesTheNextLetter() = modelUndo(late = true)

    private fun modelUndo(late: Boolean) {
        // An owner may have explicitly disabled Restore; this reversible fixture opts in.
        KeyboardPreferences(context).writeVisibleUndo(true)
        LiveFakeModelBinderFixture.install(driver).use { f ->
            val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
            if (late) f.spaceThenReleaseWithinGrace(token) else {
                f.release(); f.awaitCompletion(token, Remote.MODE_PUBLIC_CORRECTION)
                f.awaitRanking(token, 1); f.space()
            }
            f.editor("a hello ", 8, 7, 8)
            driver.tapKey("w"); f.editor("a hello w", 9, 7, 9)
            undo("helllo")
            f.editor("a helllo w", 10, 8, 10)
        }
    }

    @Test fun canonicalCaseUndoSurvivesTheNextLetter() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        KeyboardPreferences(context).writeVisibleUndo(true)
        driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
        "я москва".forEach { if (it == ' ') driver.tapKeyByDescription(context.getString(R.string.key_space)) else driver.tapKey(it.toString()) }
        checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "Москва"))), ImeTestDriver.WAIT_MILLIS))
        driver.tapKeyByDescription(context.getString(R.string.key_space))
        driver.awaitFieldText("qa_composing_text", "я Москва ")
        driver.tapKey("д"); driver.awaitFieldText("qa_composing_text", "я Москва д")
        undo("москва")
        driver.awaitFieldText("qa_composing_text", "я москва д")
    }

    private fun undo(original: String) {
        checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_undo, original))),
            ImeTestDriver.WAIT_MILLIS)) { "Previous-word Restore was not visible" }.click()
    }

    @Test fun schemaThreeMigrationPreservesOffAndUndoLivesInSmartTyping() {
        assertTrue(SettingsCodec.decode(emptyMap()).visibleUndo)
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true)
        val raw = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE)
        assertTrue(raw.edit().putInt(SettingsCodec.KEY_SCHEMA_VERSION, 3).remove(SettingsCodec.KEY_VISIBLE_UNDO).commit())
        val preferences = KeyboardPreferences(context)
        assertFalse(preferences.readSettings().visibleUndo)
        preferences.writeNumberRow(true)
        assertEquals(4, raw.getInt(SettingsCodec.KEY_SCHEMA_VERSION, -1))
        assertFalse(raw.getBoolean(SettingsCodec.KEY_VISIBLE_UNDO, true))
        assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, preferences.readSettings().autocorrectionMode)
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.TYPING)).use { scenario ->
            scenario.onActivity { activity ->
                val labels = mutableListOf<String>()
                fun visit(view: View) {
                    if (view is TextView) labels += view.text.toString()
                    if (view is ViewGroup) for (i in 0 until view.childCount) visit(view.getChildAt(i))
                }
                visit(activity.window.decorView)
                fun index(id: Int) = labels.indexOfFirst { it.equals(activity.getString(id), ignoreCase = true) }
                val smart = index(R.string.settings_section_smart_typing)
                val undo = index(R.string.settings_visible_undo)
                val mechanics = index(R.string.settings_mechanical_punctuation)
                assertTrue(smart >= 0 && undo > smart && mechanics > undo)
                val row = activity.window.decorView.findViewWithTag<View>(R.string.settings_visible_undo)
                assertFalse(row.findViewById<Switch>(R.id.row_checkbox).isChecked)
                assertTrue(row.performClick())
            }
            scenario.recreate()
            scenario.onActivity { activity ->
                val row = activity.window.decorView.findViewWithTag<View>(R.string.settings_visible_undo)
                assertTrue(row.findViewById<Switch>(R.id.row_checkbox).isChecked)
                assertTrue(preferences.readSettings().visibleUndo)
                assertTrue(row.performClick())
                assertFalse(preferences.readSettings().visibleUndo)
            }
        }
    }
}
