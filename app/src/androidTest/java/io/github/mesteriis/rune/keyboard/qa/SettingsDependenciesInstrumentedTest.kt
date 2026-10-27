package io.github.mesteriis.rune.keyboard.qa

import android.view.View
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Settings-only synthetic fixture. It never resets, imports or reads a personal store. */
@Suppress("DEPRECATION")
class SettingsDependenciesInstrumentedTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val preferences get() = KeyboardPreferences(context)

    @Before fun requireDisposableEmulator() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
    }

    private fun withSettings(block: () -> Unit) {
        val before = preferences.readSettings()
        try {
            preferences.writeEnabledLanguages(listOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.ENGLISH))
            preferences.writeCandidateStrip(true)
            block()
        } finally {
            preferences.writeEnabledLanguages(before.enabledLanguages)
            preferences.writeCandidateStrip(before.candidateStrip)
            AdditionalFeatures.entries.forEach { preferences.writeAdditionalFeature(it.key, it.value.get(before)) }
        }
    }

    private fun row(activity: SettingsActivity, title: Int): View =
        checkNotNull(activity.findViewById<LinearLayout>(R.id.settings_container).findViewWithTag(title))

    @Test fun nativeSwitchHasOneNamedCheckableTargetAndBothClickPathsPersist() = withSettings {
        preferences.writeVisibleUndo(false)
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.TYPING)).use { scenario ->
            scenario.onActivity { activity ->
                val row = row(activity, R.string.settings_visible_undo)
                val toggle = row.findViewById<Switch>(R.id.row_checkbox)
                val info = toggle.createAccessibilityNodeInfo()
                assertEquals("android.widget.Switch", info.className.toString())
                assertTrue(info.isCheckable)
                assertFalse(info.isChecked)
                assertTrue(info.isEnabled)
                assertTrue(info.actionList.any { it.id == AccessibilityNodeInfo.ACTION_CLICK })
                assertTrue(info.contentDescription.contains(activity.getString(R.string.settings_visible_undo)))
                assertEquals(View.IMPORTANT_FOR_ACCESSIBILITY_NO, row.importantForAccessibility)
                assertEquals(View.IMPORTANT_FOR_ACCESSIBILITY_NO, row.findViewById<View>(R.id.row_title).importantForAccessibility)
                assertEquals(View.IMPORTANT_FOR_ACCESSIBILITY_NO, row.findViewById<View>(R.id.row_summary).importantForAccessibility)
                assertTrue(toggle.performClick())
                assertTrue(preferences.readSettings().visibleUndo)
            }
            scenario.recreate()
            scenario.onActivity { activity ->
                val row = row(activity, R.string.settings_visible_undo)
                assertTrue(row.findViewById<Switch>(R.id.row_checkbox).isChecked)
                assertTrue(row.performClick())
                assertFalse(preferences.readSettings().visibleUndo)
            }
        }
    }

    @Test fun nativeSwitchAndLabelRespondToObservedTouchBounds() = withSettings {
        preferences.writeVisibleUndo(false)
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val device = androidx.test.uiautomator.UiDevice.getInstance(instrumentation)
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.TYPING)).use { scenario ->
            instrumentation.waitForIdleSync()
            device.waitForIdle()
            val prefix = context.getString(R.string.settings_visible_undo) + "\n"
            val target = checkNotNull(device.wait(androidx.test.uiautomator.Until.findObject(
                androidx.test.uiautomator.By.res(context.packageName, "row_checkbox").descStartsWith(prefix)), 3_000))
            target.click() // Real touch, distinct from performClick/accessibility activation tests.
            fun awaitChoice(expected: Boolean) {
                val deadline = android.os.SystemClock.uptimeMillis() + 3_000
                while (preferences.readSettings().visibleUndo != expected && android.os.SystemClock.uptimeMillis() < deadline) {
                    android.os.SystemClock.sleep(50)
                }
                assertEquals(expected, preferences.readSettings().visibleUndo)
            }
            awaitChoice(true)
            instrumentation.waitForIdleSync()
            device.waitForIdle()
            var x = 0
            var y = 0
            scenario.onActivity { activity ->
                val label = row(activity, R.string.settings_visible_undo).findViewById<TextView>(R.id.row_title)
                val bounds = android.graphics.Rect()
                assertTrue(label.getGlobalVisibleRect(bounds))
                x = bounds.centerX()
                y = bounds.centerY()
            }
            assertTrue(device.click(x, y))
            awaitChoice(false)
        }
    }

    @Test fun hiddenStripDisablesDisplayFeatureWithoutClearingItsStoredValue() = withSettings {
        preferences.writeCandidateStrip(false)
        preferences.writeLearnedRanking(true)
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.EXPERIMENTS)).use { scenario ->
            scenario.onActivity { activity ->
                val row = row(activity, R.string.settings_learned_ranking)
                val toggle = row.findViewById<Switch>(R.id.row_checkbox)
                assertFalse(row.isEnabled)
                assertFalse(toggle.isEnabled)
                assertTrue(toggle.isChecked)
                assertTrue(toggle.contentDescription.contains(activity.getString(R.string.feature_requires_candidate_strip)))
                val before = preferences.readSettings()
                row.performClick()
                toggle.performClick() // Programmatic dispatch must also refuse the disabled action.
                assertEquals(before, preferences.readSettings())
                assertTrue(toggle.isChecked)
            }
            preferences.writeCandidateStrip(true)
            scenario.recreate()
            scenario.onActivity { activity ->
                val toggle = row(activity, R.string.settings_learned_ranking).findViewById<Switch>(R.id.row_checkbox)
                assertTrue(toggle.isEnabled)
                assertTrue(toggle.isChecked)
                assertTrue(toggle.performClick())
                assertFalse(preferences.readSettings().learnedRanking)
            }
        }
    }

    @Test fun everyRussianExperimentSharesTheBadgeAndLanguageDependency() = withSettings {
        preferences.writeEnabledLanguages(listOf(KeyboardLanguage.ENGLISH))
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.EXPERIMENTS)).use { scenario ->
            scenario.onActivity { activity ->
                for (feature in AdditionalFeatures.entries.filter { it.russianOnly }) {
                    val row = row(activity, feature.title)
                    val badge = row.findViewById<TextView>(R.id.row_badge)
                    val toggle = row.findViewById<Switch>(R.id.row_checkbox)
                    assertEquals(View.VISIBLE, badge.visibility)
                    assertEquals(activity.getString(R.string.feature_experiment_ru), badge.text.toString())
                    assertFalse(toggle.isEnabled)
                    val info = toggle.createAccessibilityNodeInfo()
                    assertTrue(info.isCheckable)
                    assertFalse(info.isEnabled)
                    assertTrue(info.contentDescription.contains(badge.text))
                    assertTrue(info.contentDescription.contains(activity.getString(R.string.feature_requires_russian)))
                }
                assertTrue(row(activity, R.string.controls_disable_all).isEnabled)
            }
        }
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.DICTIONARY)).use { scenario ->
            scenario.onActivity { activity ->
                for (title in listOf(R.string.settings_abbreviations, R.string.settings_collect_examples, R.string.settings_typo_patterns)) {
                    assertTrue(row(activity, title).findViewById<Switch>(R.id.row_checkbox).isEnabled)
                }
            }
        }
    }

    @Test fun touchApplyRequiresShadowAndNightStatusRequiresBothLearningOptions() = withSettings {
        preferences.writeCandidateStrip(false)
        preferences.writeDynamicTouch(false)
        preferences.writeDynamicTouchApply(true)
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.EXPERIMENTS)).use { scenario ->
            scenario.onActivity { activity ->
                val apply = row(activity, R.string.settings_dynamic_touch_apply).findViewById<Switch>(R.id.row_checkbox)
                assertFalse(apply.isEnabled)
                assertTrue(apply.isChecked)
                assertTrue(apply.contentDescription.contains(activity.getString(R.string.feature_requires_dynamic_touch)))
                val shadow = row(activity, R.string.settings_dynamic_touch).findViewById<Switch>(R.id.row_checkbox)
                assertTrue(shadow.isEnabled)
                assertTrue(shadow.performClick())
                assertTrue(row(activity, R.string.settings_dynamic_touch_apply).findViewById<Switch>(R.id.row_checkbox).isEnabled)
            }
        }
        for (collect in listOf(false, true)) for (patterns in listOf(false, true)) {
            preferences.writeCollectExamples(collect)
            preferences.writeTypoPatterns(patterns)
            ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.DICTIONARY)).use { scenario ->
                scenario.onActivity { activity ->
                    val lab = row(activity, R.string.learning_title)
                    assertTrue(lab.isEnabled)
                    val expected = if (collect && patterns) R.string.learning_night_enabled else R.string.learning_night_requires_features
                    assertTrue(lab.findViewById<TextView>(R.id.row_summary).text.contains(activity.getString(expected)))
                    assertTrue(row(activity, R.string.settings_collect_examples).findViewById<Switch>(R.id.row_checkbox).isEnabled)
                    assertTrue(row(activity, R.string.settings_typo_patterns).findViewById<Switch>(R.id.row_checkbox).isEnabled)
                }
            }
        }
    }
}
