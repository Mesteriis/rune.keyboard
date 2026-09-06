package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import android.os.Bundle
import android.content.Context
import android.content.ContextWrapper
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringClient
import io.github.mesteriis.rune.keyboard.smarttyping.session.ModelCandidateCoordinator
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedRanking
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Optional installed-model flow; ordinary CI has no model and never enables this probe. */
class RealModelTypingInstrumentedTest {
    @Test fun installedModelCorrectsOnSpaceWithoutTapAndBackspaceRestoresOriginal() {
        assumeTrue("Explicit installed-model typing probe only",
            InstrumentationRegistry.getArguments().getString("runeRealTyping") == "true")
        val driver = ImeTestDriver()
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        try {
            driver.setUp()
            driver.prepareLiveCorrection() // Establish the real lexicon using its existing public fixture.
            driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
                mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
            driver.launchComposingQa()
            // The preceding preparation/settings transition spends real CPU. Let the existing
            // budget refill without resetting it; this is a functional fixture, not a timing claim.
            SystemClock.sleep(9_000)
            driver.tapKey("a")
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            for (key in listOf("h", "e", "l", "l", "l", "o")) driver.tapKey(key)
            driver.awaitFieldText("qa_composing_text", "a helllo")
            assertNotNull(driver.device.wait(Until.findObject(By.desc(
                context.getString(R.string.candidate_correction, "hello"))), 5_000))
            // Allow one normal typing pause to finish. Space itself must never wait for the model.
            SystemClock.sleep(1_500)
            if (InstrumentationRegistry.getArguments().getString("runeRealTypingTrace") == "true") {
                reportModelAdmission()
            }
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            driver.awaitFieldText("qa_composing_text", "a hello ")
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "a helllo")
            val original = driver.device.wait(Until.findObject(By.desc(
                context.getString(R.string.candidate_original, "helllo"))), 5_000)
            assertNotNull(original); assertTrue(original!!.isSelected)
            val stats = driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))
                .text.orEmpty().split(' ').associate { field ->
                    val (name, value) = field.split('='); name to value.toInt()
                }
            for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
                assertEquals("Unexpected editor readback", 0, stats.getValue(name))
            }
        } finally {
            driver.tearDown()
        }
    }

    /** Opt-in triage only: inspect the resident path, never alter it or copy input/model payloads. */
    private fun reportModelAdmission() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val snapshot = keyboardSnapshot()
        var result: Result<Bundle>? = null
        instrumentation.runOnMainSync {
            result = runCatching {
                fun field(owner: Any, name: String): Any? = owner.javaClass.getDeclaredField(name)
                    .apply { isAccessible = true }.get(owner)
                var owner: Context = snapshot.keyboard.context
                while (owner !is RuneInputMethodService && owner is ContextWrapper) owner = owner.baseContext
                val service = checkNotNull(owner as? RuneInputMethodService)
                val controller = field(service, "typingSession") as TypingSessionController
                val local = checkNotNull(field(service, "candidates"))
                val model = field(local, "modelRanking") as ModelCandidateCoordinator
                val client = field(model, "client") as ModelScoringClient
                val selection = field(controller, "candidateSelection")
                val ranking = selection?.let { field(it, "ranking") as? CalibratedRanking }
                Bundle().apply {
                    putInt("typingReadinessOrdinal", model.modelReadinessHint.ordinal)
                    putBoolean("typingClientAvailable", client.available)
                    putBoolean("typingSessionEnabled", controller.state.enabled)
                    putBoolean("typingCanRequestCandidates", controller.canRequestCandidates)
                    putBoolean("typingCanRequestModelRanking", controller.canRequestModelRanking)
                    putBoolean("typingPendingRanking", field(controller, "pendingModelRanking") != null)
                    putBoolean("typingPausePending", field(model, "timer") != null)
                    putBoolean("typingModelRanked", selection?.let { field(it, "modelRanked") as Boolean } ?: false)
                    putBoolean("typingRankingUsedModel", ranking?.usedModel == true)
                    putInt("typingPreferredId", ranking?.preferredId ?: -1)
                    putLong("typingRequestCount", field(model, "requestId") as Long)
                }
            }
        }
        instrumentation.sendStatus(0, checkNotNull(result).getOrThrow())
    }
}
