package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry
import androidx.test.runner.lifecycle.Stage
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.UiScrollable
import androidx.test.uiautomator.UiSelector
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.intelligence.inference.LifecycleModelInferenceService
import io.github.mesteriis.rune.keyboard.settings.SettingsActivity
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticStream
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** Real debug controls, resident IME observer and remote Binder editor; synthetic input only. */
@RunWith(AndroidJUnit4::class)
class TypingDiagnosticsInstrumentedTest : ImeTestBase() {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val recorder get() = TypingDiagnosticsProvider.create(context) as DiagnosticsRecorder
    private var mayClean = false

    @Before fun requireEmptyOptOutRecorder() {
        operation(recorder::barrier)
        // Never erase a phone owner's existing diagnostic capture when this suite is run there.
        val managed = File(context.noBackupFilesDir, "typing-diagnostics")
        assumeTrue("Existing user diagnostics must be preserved", !recorder.preferences.metadata &&
            !recorder.preferences.text && managed.listFiles().orEmpty().none { it.length() > 0 })
        mayClean = true
    }

    @After fun removeOnlyThisSyntheticCapture() {
        if (mayClean) operation(recorder::delete)
    }

    @Test fun twoConfirmationsCancelIndependentlyAndSwitchesRemainIndependent() {
        driver.launchSettings()
        row("diagnostics_text_toggle").click(); dialog("diagnostics_scope_title")
        assertFalse(recorder.preferences.text)
        driver.device.pressBack(); settle(); assertFalse(recorder.preferences.text)
        row("diagnostics_text_toggle").click(); dialog("diagnostics_scope_title"); positive()
        dialog("diagnostics_storage_title"); assertFalse(recorder.preferences.text)
        button("button2").click(); settle(); assertFalse(recorder.preferences.text)
        enableTextThroughDialogs()
        assertFalse(recorder.preferences.metadata)
        row("diagnostics_text_toggle").click(); awaitPreference(text = false)
        row("diagnostics_metadata_toggle").click(); awaitPreference(metadata = true)
        assertFalse(recorder.preferences.text)
        row("diagnostics_metadata_toggle").click(); awaitPreference(metadata = false)
    }

    @Test fun recreationDuringSecondConfirmationLeavesTextOff() {
        driver.launchSettings()
        row("diagnostics_text_toggle").click(); dialog("diagnostics_scope_title"); positive()
        dialog("diagnostics_storage_title")
        var failure: Throwable? = null
        instrumentation.runOnMainSync {
            try {
                val settings = ActivityLifecycleMonitorRegistry.getInstance()
                    .getActivitiesInStage(Stage.RESUMED).filterIsInstance<SettingsActivity>().single()
                settings.recreate()
            } catch (caught: Throwable) { failure = caught }
        }
        failure?.let { throw it }
        settle()
        assertFalse(recorder.preferences.text)
        assertFalse(driver.device.hasObject(By.res("android", "button1")))
        assertNotNull(row("diagnostics_text_toggle"))
    }

    @Test fun consentStartsWithFreshRuneInputAndDisableStopsTextOnly() {
        driver.configureMechanicalPunctuation(mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        type("beforecanary"); space()
        driver.launchSettings(); enableTextThroughDialogs()
        row("diagnostics_metadata_toggle").click(); awaitPreference(metadata = true)
        driver.launchComposingQa(); type("aftercanary"); space()
        val text = snapshot(DiagnosticStream.TEXT)
        assertTrue("Permitted input did not reach recorder", text.contains("aftercanary"))
        assertFalse("Pre-consent input was captured", text.contains("beforecanary"))
        val metadata = snapshot(DiagnosticStream.METADATA)
        assertTrue(metadata.isNotBlank()); assertMetadataVocabulary(metadata)
        assertFalse(metadata.contains("aftercanary")); noReadback()

        driver.launchSettings(); row("diagnostics_text_toggle").click(); awaitPreference(text = false)
        val stoppedText = snapshot(DiagnosticStream.TEXT)
        val metadataBefore = snapshot(DiagnosticStream.METADATA)
        driver.launchComposingQa(); type("disabledcanary"); space()
        assertEquals(stoppedText, snapshot(DiagnosticStream.TEXT))
        assertTrue(snapshot(DiagnosticStream.METADATA).length > metadataBefore.length)
        assertTrue(recorder.preferences.metadata); assertFalse(recorder.preferences.text); noReadback()
    }

    @Test fun actualCandidateDecisionUndoAndSensitiveExclusionsReachSeparateStreams() {
        driver.launchSettings(); enableTextThroughDialogs()
        row("diagnostics_metadata_toggle").click(); awaitPreference(metadata = true)
        // Return to a real input window before installing the existing bounded fake scorer.
        driver.launchComposingQa()
        LiveFakeModelBinderFixture.install(driver).use { fixture ->
            val token = fixture.blockedWord(LifecycleModelInferenceService.SCORES_PUBLIC_CORRECTION)
            fixture.release(); fixture.awaitCompletion(token, LifecycleModelInferenceService.MODE_PUBLIC_CORRECTION)
            fixture.awaitRanking(token, 1)
            fixture.space(); fixture.editor("a hello ", 8, 7, 8)
            fixture.backspace(); fixture.editor("a helllo", 8, 1, 8)
            val text = snapshot(DiagnosticStream.TEXT)
            val rows = text.lineSequence().filter(String::isNotBlank).map(::JSONObject).toList()
            assertTrue("Actual candidates missing", rows.any { it.getString("kind") == "CANDIDATES" &&
                it.getString("original") == "helllo" && it.getJSONArray("candidates").toString().contains("hello") })
            assertTrue("Actual automatic branch missing", rows.any { it.getString("kind") == "BOUNDARY" &&
                it.getString("reason") == "AUTO_REPLACE" })
            assertTrue("Actual Undo missing", rows.any { it.getString("kind") == "UNDO" })
            assertMetadataVocabulary(snapshot(DiagnosticStream.METADATA)); noReadback()
        }
        // Freeze after fixture cleanup; neither excluded field may add per-input metadata or text.
        val textBefore = snapshot(DiagnosticStream.TEXT)
        val metadataBefore = snapshot(DiagnosticStream.METADATA)
        for (mode in listOf("password", "private")) {
            driver.launchComposingQa(mode)
            type("sensitivecanary")
            assertEquals(15, stats().getValue("length"))
            assertEquals(0, stats().getValue("caps")); noReadback()
            assertEquals(textBefore, snapshot(DiagnosticStream.TEXT))
            assertEquals(metadataBefore, snapshot(DiagnosticStream.METADATA))
        }
    }

    @Test fun managementDeleteDisablesBothAndRemovesManagedLogs() {
        driver.launchSettings(); enableTextThroughDialogs()
        row("diagnostics_metadata_toggle").click(); awaitPreference(metadata = true)
        driver.launchComposingQa(); type("deletecanary"); space()
        assertTrue(snapshot(DiagnosticStream.TEXT).isNotBlank())
        driver.launchSettings(); row("diagnostics_manage").click()
        checkNotNull(driver.device.wait(Until.findObject(By.res(ImeTestDriver.PACKAGE_NAME,
            "diagnostics_delete")), ImeTestDriver.WAIT_MILLIS)).click()
        awaitPreference(text = false, metadata = false); operation(recorder::barrier)
        assertEquals("", snapshot(DiagnosticStream.TEXT))
        assertEquals("", snapshot(DiagnosticStream.METADATA))
        assertTrue(File(context.noBackupFilesDir, "typing-diagnostics").listFiles().orEmpty().none { it.length() > 0 })
    }

    private fun enableTextThroughDialogs() {
        row("diagnostics_text_toggle").click(); dialog("diagnostics_scope_title"); positive()
        dialog("diagnostics_storage_title"); assertFalse(recorder.preferences.text); positive()
        awaitPreference(text = true)
    }
    private fun row(id: String): UiObject2 {
        if (!driver.device.hasObject(By.res(ImeTestDriver.PACKAGE_NAME, id))) {
            @Suppress("DEPRECATION")
            UiScrollable(UiSelector().resourceId("${ImeTestDriver.PACKAGE_NAME}:id/settings_scroll"))
                .apply { setAsVerticalList(); scrollIntoView(UiSelector().resourceId("${ImeTestDriver.PACKAGE_NAME}:id/$id")) }
        }
        return checkNotNull(driver.device.wait(Until.findObject(By.res(ImeTestDriver.PACKAGE_NAME, id)), ImeTestDriver.WAIT_MILLIS))
    }
    private fun dialog(name: String) {
        val id = context.resources.getIdentifier(name, "string", context.packageName)
        assertTrue(id != 0)
        assertTrue(driver.device.wait(Until.hasObject(By.text(context.getString(id))), ImeTestDriver.WAIT_MILLIS))
    }
    private fun button(name: String) = checkNotNull(driver.device.wait(
        Until.findObject(By.res("android", name)), ImeTestDriver.WAIT_MILLIS))
    private fun positive() { button("button1").click(); settle() }
    private fun settle() { instrumentation.waitForIdleSync(); driver.device.waitForIdle() }
    private fun awaitPreference(text: Boolean? = null, metadata: Boolean? = null) {
        operation(recorder::barrier); settle()
        text?.let { assertEquals(it, recorder.preferences.text) }
        metadata?.let { assertEquals(it, recorder.preferences.metadata) }
    }
    private fun operation(start: ((Boolean) -> Unit) -> Unit) {
        val done = CountDownLatch(1); val success = AtomicBoolean()
        start { success.set(it); done.countDown() }
        assertTrue("Diagnostic operation timed out", done.await(10, TimeUnit.SECONDS))
        assertTrue("Diagnostic operation failed", success.get())
    }
    private fun snapshot(stream: DiagnosticStream): String {
        val bytes = ByteArrayOutputStream()
        operation { done -> recorder.export(recorder.newExport(), stream, { bytes }, done) }
        return bytes.toString(Charsets.UTF_8.name())
    }
    private fun assertMetadataVocabulary(text: String) {
        val allowed = setOf("schema", "kind", "reason", "session", "revision", "candidateCount", "selectedIndex", "modelUsed")
        text.lineSequence().filter(String::isNotBlank).forEach { line ->
            assertEquals(allowed, JSONObject(line).keys().asSequence().toSet())
        }
    }
    private fun type(word: String) = word.forEach { driver.tapKey(it.toString()) }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('='); name to value.toInt()
    }
    private fun noReadback() {
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor payload read", 0, stats().getValue(name))
    }
}
