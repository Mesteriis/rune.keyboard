package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.content.Context
import android.os.Build
import android.os.SystemClock
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.LearningLabActivity
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LearningLabProgressInstrumentedTest {
    @Test fun showsEligibleThresholdProgressAndActualRefusalReason() {
        assumeTrue(InstrumentationRegistry.getArguments().getString("reviewU13") == "true")
        assumeTrue(Build.HARDWARE in setOf("ranchu", "goldfish"))
        val context = ApplicationProvider.getApplicationContext<Context>()
        val store = LearningStore.get(context)
        val loadDeadline = SystemClock.elapsedRealtime() + 10_000
        while (!store.isReady && SystemClock.elapsedRealtime() < loadDeadline) SystemClock.sleep(10)
        assertTrue(store.isReady)
        val snapshot = store.snapshot()
        val progress = LearningEvaluator.holdoutProgress(snapshot)
        assertTrue("Run after the isolated promotion fixture", progress.hasMinimumSamples)
        assertEquals(snapshot.candidatePolicy(), snapshot.activePolicy)
        ActivityScenario.launch(LearningLabActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                assertEquals(activity.getString(R.string.learning_progress_format,
                    progress.examples, LearningEvaluator.MINIMUM_HOLDOUT,
                    progress.corrections, LearningEvaluator.MINIMUM_CORRECTIONS,
                    progress.identities, LearningEvaluator.MINIMUM_IDENTITIES,
                    activity.getString(R.string.learning_samples_ready)),
                    activity.findViewById<TextView>(R.id.learning_progress).text.toString())
                assertTrue(activity.findViewById<Button>(R.id.learning_run).performClick())
            }
            var explained = false
            val deadline = SystemClock.elapsedRealtime() + 20_000
            while (!explained && SystemClock.elapsedRealtime() < deadline) {
                scenario.onActivity { activity ->
                    explained = activity.findViewById<TextView>(R.id.learning_results).text.toString()
                        .contains(activity.getString(R.string.learning_reason_unchanged))
                }
                if (!explained) SystemClock.sleep(50)
            }
            assertTrue("Candidate-unchanged refusal should be explained", explained)
        }
        assertEquals(snapshot, store.snapshot())
    }
}
