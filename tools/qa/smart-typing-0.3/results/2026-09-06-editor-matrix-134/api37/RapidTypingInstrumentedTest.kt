package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Rect
import android.os.Bundle
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RapidTypingInstrumentedTest : ImeTestBase() {
    @Test fun rapidTouchBurstKeepsEveryCharacterAcrossWordBoundaries() {
        driver.configureSmartTyping(AutocorrectionMode.SUGGESTIONS, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        val text = "hello world ".repeat(6) + "end"
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        // Resolve every target before the burst. Accessibility idle waits must not pace typing.
        val bounds = text.toSet().associateWith { character ->
            val key = if (character == ' ') checkNotNull(driver.device.findObject(
                By.desc(context.getString(R.string.key_space))))
            else driver.characterKey(character.toString())
            Rect(key.visibleBounds)
        }
        val started = SystemClock.uptimeMillis()
        var releases = 0
        for (character in text) {
            val touch = driver.touchDown(bounds.getValue(character))
            var released = false
            try {
                driver.releaseTouch(touch)
                released = true
                releases++
            } finally {
                if (!released) driver.cancelTouch(touch)
            }
            SystemClock.sleep(15)
        }
        val elapsed = SystemClock.uptimeMillis() - started
        driver.awaitFieldText("qa_composing_text", text)
        driver.tapDelete()
        driver.awaitFieldText("qa_composing_text", text.dropLast(1))
        val stats = checkNotNull(driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME,
            "qa_composing_stats"))).text.orEmpty().split(' ').associate {
            val (name, count) = it.split('='); name to count.toInt()
        }
        for (counter in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected payload read during touch burst", 0, stats.getValue(counter))
        }
        assertEquals(text.length, releases)
        InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
            putInt("rapid_touch_releases", releases)
            putLong("rapid_touch_burst_ms", elapsed)
        })
        // Actual injection duration is reported, not equated to the requested spacing or a
        // physical-device frame/latency budget. Exact editor text is the delivery assertion.
    }
}
