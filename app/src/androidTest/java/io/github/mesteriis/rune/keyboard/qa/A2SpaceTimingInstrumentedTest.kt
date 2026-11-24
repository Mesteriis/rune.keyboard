package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.graphics.Rect
import android.os.Build
import android.os.SystemClock
import android.os.Trace
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.BuildConfig
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.Assume.assumeTrue
import org.junit.Test

/** One public synthetic attempt in the separately installed debug package. */
class A2SpaceTimingInstrumentedTest {
    @Test fun captureOneSpace() {
        val arguments = InstrumentationRegistry.getArguments()
        assumeTrue(arguments.getString("runeA2Timing") == "true")
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        check(context.packageName == ImeTestDriver.QUALIFICATION_PACKAGE)
        check(Build.MODEL.startsWith("SM-F") && arguments.getString("allowPhysicalDevice") == "true")
        val length = requireNotNull(arguments.getString("runeA2Characters")).toInt()
        require(length in setOf(300, 600, 1000))
        val mode = arguments.getString("runeA2Window")
        require(mode == "on" || mode == "off")
        check(BuildConfig.MODEL_PREFIX_WINDOW == (mode == "on"))
        val capture = requireNotNull(arguments.getString("runeA2Capture"))
        require(capture.matches(Regex("[a-z0-9-]{1,40}")))
        val path = "/data/misc/perfetto-traces/rune-a2-$capture.pftrace"

        val driver = ImeTestDriver.forA2Timing()
        check(driver.shell("am get-current-user") == "0")
        try {
            driver.setUp()
            val preferences = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
            for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
                SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_DYNAMIC_TOUCH, SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY,
                SettingsCodec.KEY_QUALITY_METRICS, SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES,
                SettingsCodec.KEY_TYPO_PATTERNS)) preferences.putBoolean(key, false)
            check(preferences.putBoolean(SettingsCodec.KEY_KEY_PREVIEW, false).commit())
            driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false,
                doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
            driver.launchComposingQa()

            val prefix = "we go now ".repeat(length / 10)
            val probe = "helos"
            val keys = (prefix + probe).toSet().associateWith {
                if (it == ' ') driver.spaceKeyBounds() else Rect(driver.keyByText(it.toString()).visibleBounds)
            }
            fun type(text: String) {
                check(driver.device.currentPackageName == context.packageName)
                for (letter in text) driver.releaseTouch(driver.touchDown(keys.getValue(letter)))
            }
            type(prefix)
            driver.awaitFieldText("qa_composing_text", prefix)
            fun traceBytes() = driver.shell("stat -c %s $path").toLongOrNull()
            check(traceBytes() == null) { "A2 trace path already exists" }
            driver.shell("perfetto --background-wait --no-clobber -t 3s -b 4mb " +
                "-a ${context.packageName} -o $path ftrace/print")
            type("$probe ")
            SystemClock.sleep(500)
            instrumentation.runOnMainSync {
                Trace.beginSection("Rune#a2CaptureEnd")
                Trace.endSection()
            }
            SystemClock.sleep(3_000)
            check(driver.fieldText("qa_composing_text").startsWith(prefix))
            check((traceBytes() ?: 0) > 0) { "A2 trace is missing or empty" }
        } finally {
            driver.tearDown()
        }
    }
}
