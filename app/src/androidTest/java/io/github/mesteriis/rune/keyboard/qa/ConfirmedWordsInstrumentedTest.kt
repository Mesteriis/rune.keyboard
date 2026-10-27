package io.github.mesteriis.rune.keyboard.qa

import android.os.Process
import android.os.Build
import android.os.SystemClock
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.accessibility.AccessibilityEvent
import android.widget.EditText
import android.widget.ListView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry
import androidx.test.runner.lifecycle.Stage
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.ConfirmedWordsActivity
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.SettingsActivity
import io.github.mesteriis.rune.keyboard.settings.SettingsPage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.*
import java.io.File
import java.security.MessageDigest
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.junit.Assert.*
import org.junit.Test
import org.junit.Before
import org.junit.Assume.assumeTrue
import org.junit.runner.RunWith

/** Public synthetic fixtures only. The host explicitly restarts the process between the first two phases. */
@RunWith(AndroidJUnit4::class)
class ConfirmedWordsInstrumentedTest : ImeTestBase() {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val store get() = PersonalTypingResources.get(context).personal
    private val profile get() = File(context.noBackupFilesDir, "personal-typing/profile.bin")
    private val proof get() = File(context.cacheDir, "u5-confirmed-removal-proof")
    private val language = KeyboardLanguage.ENGLISH

    @Before fun requireExplicitSyntheticEmulatorRun() {
        assumeTrue("Destructive synthetic fixtures are restricted to disposable emulators",
            Build.HARDWARE in setOf("ranchu", "goldfish") &&
                InstrumentationRegistry.getArguments().getString("runeSyntheticProfileFixture") == "true")
    }

    @Test fun originalConfirmationIsVisibleAndRemovalIsDurable() {
        emptyProfile()
        configureLearning()
        driver.launchComposingQa()
        WORD.forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText("qa_composing_text", WORD)
        checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_original, WORD))),
            ImeTestDriver.WAIT_MILLIS)).click()
        await { store.model.protectsOriginal(WORD, language) && store.lastWriteSucceeded == true }
        check(store.update { it.recordRejected(WORD, OTHER, language) })
        await { store.lastWriteSucceeded == true }
        ActivityScenario.launch(ConfirmedWordsActivity::class.java).use { scenario ->
            filter(scenario, WORD)
            val row = row(WORD)
            assertTrue(row.isClickable)
            scenario.onActivity { activity ->
                val field = activity.findViewById<EditText>(R.id.confirmed_words_filter)
                assertTrue(field.inputType and InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS != 0)
                assertTrue(field.imeOptions and EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING != 0)
                assertEquals(1, activity.findViewById<ListView>(R.id.confirmed_words_entries).adapter.count)
            }
            row.click(); positive()
            await { !store.model.protectsOriginal(WORD, language) && store.lastWriteSucceeded == true }
            assertTrue(store.model.rejects(WORD, OTHER, language))
            scenario.recreate()
            filter(scenario, WORD)
            assertFalse(driver.device.hasObject(By.desc(description(WORD))))
        }
        assertFalse(PersonalTypingCodec.decode(profile.readBytes()).confirmed.any { it.word == WORD })
        proof.writeText("${Process.myPid()}\n${digest(profile)}\n")
    }

    @Test fun removalSurvivesAProcessRestart() {
        await { store.isReady }
        check(proof.isFile) { "Run the deletion phase before the explicit process restart" }
        val fields = proof.readLines()
        assertNotEquals("A real process restart is required", fields[0].toInt(), Process.myPid())
        assertEquals(fields[1], digest(profile))
        val snapshot = store.model.snapshot()
        assertEquals(PersonalTypingCodec.decode(profile.readBytes()), snapshot)
        assertTrue(snapshot.confirmed.isEmpty() && snapshot.phrases.isEmpty())
        assertEquals(1, snapshot.feedback.size)
        assertTrue(store.model.rejects(WORD, OTHER, language))
        assertFalse(store.model.protectsOriginal(WORD, language))
        try {
            ActivityScenario.launch(ConfirmedWordsActivity::class.java).use { scenario ->
                filter(scenario, WORD)
                assertFalse(driver.device.hasObject(By.desc(description(WORD))))
            }
        } finally { reset(); check(proof.delete()) }
    }

    @Test fun fullConfirmationReportsLimitOnceAndListCanBeFiltered() {
        emptyProfile(); configureLearning()
        val words = List(PersonalTypingModel.MAX_CONFIRMED) { index ->
            PersonalWord(language, "capacity" + ('a' + index / 676) + ('a' + index / 26 % 26) + ('a' + index % 26))
        }
        check(store.update { it.restore(PersonalTypingSnapshot(confirmed = words)) })
        await { store.lastWriteSucceeded == true }
        try {
            var refusals = 0
            val bridge = AndroidTypingPersonalization(PersonalTypingResources.get(context)) { refusals++ }
            bridge.learningEnabled = true
            bridge.confirmed("overflow", language)
            assertEquals(1, refusals)
            bridge.confirmed(words.first().word, language)
            bridge.confirmed("not a word", language)
            assertEquals(1, refusals)
            bridge.accepted("mistype", "overflow", language)
            assertEquals(1, refusals)
            var acceptedRefusals = 0
            val acceptedBridge = AndroidTypingPersonalization(PersonalTypingResources.get(context)) { acceptedRefusals++ }
            acceptedBridge.learningEnabled = true
            acceptedBridge.accepted("mistype", "otheroverflow", language)
            assertEquals(1, acceptedRefusals)
            PersonalTypingCodec.validate(store.model.snapshot())
            driver.launchComposingQa()
            "overflow".forEach { driver.tapKey(it.toString()) }
            val original = checkNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_original, "overflow"))),
                ImeTestDriver.WAIT_MILLIS))
            val center = original.visibleCenter
            val message = context.getString(R.string.confirmed_words_full, PersonalTypingModel.MAX_CONFIRMED)
            val notification = instrumentation.uiAutomation.executeAndWaitForEvent(
                { check(driver.device.click(center.x, center.y)) },
                { event -> event.eventType == AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED &&
                    event.text.any { it.toString().contains(message) } }, ImeTestDriver.WAIT_MILLIS)
            assertEquals(AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED, notification.eventType)
            @Suppress("DEPRECATION") notification.recycle()
            assertEquals(PersonalTypingModel.MAX_CONFIRMED, store.model.snapshot().confirmed.size)
            assertFalse(store.model.protectsOriginal("overflow", language))
            ActivityScenario.launch(ConfirmedWordsActivity::class.java).use { scenario ->
                filter(scenario, words.first().word)
                scenario.onActivity { activity ->
                    assertEquals(1, activity.findViewById<ListView>(R.id.confirmed_words_entries).adapter.count)
                }
                row(words.first().word).click(); positive()
                await { store.model.snapshot().confirmed.size == PersonalTypingModel.MAX_CONFIRMED - 1 && store.lastWriteSucceeded == true }
            }
        } finally { reset() }
    }

    @Test fun failedRemovalOffersIdempotentRetryAndPreservesPairRejection() {
        emptyProfile()
        check(store.update { it.recordConfirmedWord(WORD, language); it.recordRejected(WORD, OTHER, language) })
        await { store.lastWriteSucceeded == true }
        val root = profile.parentFile!!
        val backup = File(context.cacheDir, "u5-profile-backup-${UUID.randomUUID()}")
        val before = profile.readBytes()
        try {
            ActivityScenario.launch(ConfirmedWordsActivity::class.java).use { scenario ->
                filter(scenario, WORD); row(WORD).click()
                check(root.renameTo(backup)); root.writeText(BLOCKER)
                positive()
                assertTrue(driver.device.wait(Until.hasObject(By.text(context.getString(R.string.confirmed_words_save_failed))),
                    ImeTestDriver.WAIT_MILLIS))
                assertArrayEquals(before, File(backup, "profile.bin").readBytes())
                assertTrue(store.model.rejects(WORD, OTHER, language))
                assertFalse(store.model.protectsOriginal(WORD, language))
                assertEquals(BLOCKER, root.readText()); check(root.delete()); check(backup.renameTo(root))
                positive()
                await { store.lastWriteSucceeded == true && !PersonalTypingCodec.decode(profile.readBytes()).confirmed.any { it.word == WORD } }
                assertTrue(store.model.rejects(WORD, OTHER, language))
                scenario.recreate(); filter(scenario, WORD)
                assertFalse(driver.device.hasObject(By.desc(description(WORD))))
            }
        } finally {
            if (root.isFile && root.readText() == BLOCKER) check(root.delete())
            if (backup.exists() && !root.exists()) check(backup.renameTo(root))
            reset()
        }
    }

    @Test fun settingsNavigationOpensTheConfirmedWordsList() {
        ActivityScenario.launch<SettingsActivity>(SettingsActivity.intent(context, SettingsPage.DICTIONARY)).use { scenario ->
            scenario.onActivity { activity ->
                val row = activity.window.decorView.findViewWithTag<View>(R.string.confirmed_words_title)
                assertNotNull(row); assertTrue(row.isShown && row.isEnabled)
                assertTrue(row.performClick())
            }
            assertTrue(driver.device.wait(Until.hasObject(By.res(ImeTestDriver.PACKAGE_NAME, "confirmed_words_entries")),
                ImeTestDriver.WAIT_MILLIS))
            instrumentation.runOnMainSync {
                ActivityLifecycleMonitorRegistry.getInstance().getActivitiesInStage(Stage.RESUMED)
                    .filterIsInstance<ConfirmedWordsActivity>().single().finish()
            }
        }
    }

    private fun configureLearning() {
        driver.configureSmartTyping(AutocorrectionMode.SUGGESTIONS, true, mechanical = false, doubleSpace = false)
        KeyboardPreferences(context).writePersonalLearning(true)
        instrumentation.waitForIdleSync()
    }
    private fun emptyProfile() {
        await { store.isReady }
        assertEquals("Only an empty synthetic profile may be used", PersonalTypingSnapshot(), store.model.snapshot())
    }
    private fun filter(scenario: ActivityScenario<ConfirmedWordsActivity>, query: String) {
        await { store.isReady }
        scenario.onActivity { it.findViewById<EditText>(R.id.confirmed_words_filter).setText(query) }
        driver.device.waitForIdle()
    }
    private fun description(word: String) = context.getString(R.string.confirmed_words_remove_description, word, language.displayLabel)
    private fun row(word: String) = checkNotNull(driver.device.wait(Until.findObject(By.desc(description(word))), ImeTestDriver.WAIT_MILLIS))
    private fun positive() = checkNotNull(driver.device.wait(Until.findObject(By.res("android", "button1")), ImeTestDriver.WAIT_MILLIS)).click()
    private fun reset() {
        val latch = CountDownLatch(1); val success = AtomicBoolean()
        store.reset { success.set(it); latch.countDown() }
        assertTrue(latch.await(5, TimeUnit.SECONDS)); assertTrue(success.get())
    }
    private fun await(condition: () -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!condition()) { check(SystemClock.uptimeMillis() < deadline) { "Synthetic confirmed-word condition timed out" }; SystemClock.sleep(20) }
    }
    private fun digest(file: File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
    private companion object { const val WORD = "runesynthetic"; const val OTHER = "other"; const val BLOCKER = "synthetic blocked storage" }
}
