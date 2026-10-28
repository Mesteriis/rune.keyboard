package io.github.mesteriis.rune.keyboard.smarttyping.tools

import android.widget.Button
import androidx.test.filters.SdkSuppress
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.quality.QualityExportActivity
import io.github.mesteriis.rune.keyboard.settings.quality.QualityDashboardActivity
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsActivity
import io.github.mesteriis.rune.keyboard.smarttyping.quality.*
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Real local SAF provider on the disposable emulator only; never resets owner statistics. */
class QualityExportInstrumentedTest {
    @Test fun qualityDashboardOwnsNumericExportNavigation() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish"))
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        check(InstrumentationRegistry.getArguments().getString("runeOwnedEmulator") == "q8-editor")
        val context = instrumentation.targetContext
        val device = UiDevice.getInstance(instrumentation)
        ActivityScenario.launch(DiagnosticsActivity::class.java).use { scenario ->
            scenario.onActivity {
                assertNull(it.findViewById<Button>(R.id.quality_export_manage))
                assertNotNull(it.findViewById<Button>(R.id.diagnostics_export_metadata))
            }
        }
        ActivityScenario.launch(QualityDashboardActivity::class.java).use { scenario ->
            scenario.onActivity { assertTrue(it.findViewById<Button>(R.id.quality_export_manage).performClick()) }
            assertTrue(device.wait(Until.hasObject(By.res(context.packageName, "quality_export_choose")), 10000))
            device.pressBack()
            assertTrue(device.wait(Until.hasObject(By.res(context.packageName, "quality_status")), 10000))
        }
    }

    // This system-picker fixture was verified on API 26. It does not assert API 37 picker layout.
    @SdkSuppress(maxSdkVersion = 26)
    @Test fun realDocumentPickerCancelAndSaveExportOnlyNumericSnapshot() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish"))
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        check(InstrumentationRegistry.getArguments().getString("runeOwnedEmulator") == "q4-counters")
        val context = instrumentation.targetContext
        val device = UiDevice.getInstance(instrumentation)
        val store = QualityStore.get(context)
        fun reset() {
            val done = CountDownLatch(1)
            var success = false
            store.reset { success = it; done.countDown() }
            assertTrue(done.await(10, TimeUnit.SECONDS)); assertTrue(success)
        }
        reset()
        store.configure(true, false, true)
        store.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED)
        store.modelResponseMillis(250)
        val expected = store.snapshot()
        val path = "/sdcard/Download/rune-quality.txt"
        fun documentExists() = device.executeShellCommand("ls /sdcard/Download").lineSequence()
            .any { it.trim() == "rune-quality.txt" }
        assertFalse("Existing synthetic export must not be overwritten", documentExists())
        var exported = false
        try {
            ActivityScenario.launch(QualityExportActivity::class.java).use { scenario ->
                scenario.onActivity { assertTrue(it.findViewById<Button>(R.id.quality_export_choose).performClick()) }
                assertTrue(device.wait(Until.hasObject(By.pkg("com.android.documentsui")), 10000))
                device.pressBack() // The picker may first dismiss its filename keyboard.
                if (!device.wait(Until.hasObject(By.res(context.packageName, "quality_export_choose")), 1000) &&
                    device.hasObject(By.pkg("com.android.documentsui"))) device.pressBack()
                assertTrue(device.wait(Until.hasObject(By.res(context.packageName, "quality_export_choose")), 10000))
                scenario.onActivity { assertTrue(it.findViewById<Button>(R.id.quality_export_choose).isEnabled) }
                assertEquals(expected, store.snapshot())
                scenario.onActivity { it.findViewById<Button>(R.id.quality_export_choose).performClick() }
                assertTrue(device.wait(Until.hasObject(By.pkg("com.android.documentsui")), 10000))
                device.waitForIdle()
                val roots = device.findObject(By.desc("Show roots"))
                if (roots != null) {
                    roots.click()
                    val downloads = device.wait(Until.findObject(By.text("Downloads")), 10000)
                    assertNotNull("Local Downloads root missing", downloads)
                    downloads.click()
                    device.waitForIdle()
                }
                // API 26's filename IME moves the Save row after root navigation. Dismiss it
                // while it is observable, then obtain the button at its final bounds.
                if (device.hasObject(By.pkg("com.google.android.inputmethod.latin"))) {
                    device.pressBack()
                    assertTrue(device.wait(Until.gone(By.pkg("com.google.android.inputmethod.latin")), 10000))
                }
                device.waitForIdle()
                val save = device.wait(Until.findObject(By.res("android", "button1").enabled(true)), 10000)
                assertNotNull("Document picker Save missing", save)
                device.waitForIdle()
                // Use platform input for the system-owned surface: this API 26 image does
                // not deliver UiObject2's gesture on this row. Bounds come from live UI.
                val bounds = save.visibleBounds
                device.executeShellCommand("input tap ${bounds.centerX()} ${bounds.centerY()}")
                val completed = device.wait(Until.hasObject(By.text(context.getString(R.string.diagnostics_exported))), 10000)
                if (!completed) device.dumpWindowHierarchy(java.io.File(context.cacheDir, "quality-export-failure.xml"))
                assertTrue("Numeric export did not complete; UI captured in private cache", completed)
                exported = true
                // The picker selects DownloadsProvider, whose returned grant belongs to the
                // activity. Read its real public file via shell, without inventing a second URI.
                val bytes = device.executeShellCommand("cat $path").toByteArray(Charsets.US_ASCII)
                assertTrue(bytes.size <= QualityCodec.MAX_BYTES)
                assertEquals(expected, QualityCodec.decode(bytes))
                assertEquals(expected, store.snapshot())
                scenario.recreate()
                scenario.onActivity { assertTrue(it.findViewById<Button>(R.id.quality_export_choose).isEnabled) }
            }
        } finally {
            try {
                if (exported) {
                    device.executeShellCommand("rm -f $path")
                    assertFalse("Synthetic document cleanup failed", documentExists())
                }
            } finally {
                store.configure(false, false, false)
                reset()
            }
        }
    }
}
