package io.github.mesteriis.rune.keyboard.intelligence.ui

import android.content.pm.ActivityInfo
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertNotNull
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ModelSettingsActivityInstrumentedTest {
    @Test
    fun opensWithoutModelAndSurvivesRotation() {
        ActivityScenario.launch(ModelSettingsActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                assertNotNull(activity.findViewById(R.id.model_status))
                activity.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            }
            scenario.onActivity { activity -> assertNotNull(activity.findViewById(R.id.model_status)) }
        }
    }
}
