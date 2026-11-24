package io.github.mesteriis.rune.keyboard.qa

import android.content.ContextWrapper
import android.graphics.Bitmap
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.view.PixelCopy
import android.view.MotionEvent
import android.view.Window
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** PixelCopy completion bounds presentation; test instrumentation is not a release timing gate. */
class EmojiPresentedFrameInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val driver = ImeTestDriver()
    private var prepared = false
    private val worker = HandlerThread("emoji-pixel-copy")

    @Before fun prepare() {
        check(Build.VERSION.SDK_INT >= 26 && Build.HARDWARE in setOf("ranchu", "goldfish"))
        worker.start()
        prepared = true
        driver.setUp()
        driver.launchComposingQa()
        driver.tapKeyByDescription(instrumentation.targetContext.getString(R.string.key_symbols))
    }

    @After fun restore() {
        try { if (prepared) driver.tearDown() } finally { worker.quitSafely() }
    }

    @Test fun firstVisibleEmojiHasPixelCopyEvidence() {
        val keyboard = keyboardSnapshot().keyboard
        var owner = keyboard.rootView.context
        while (owner is ContextWrapper && owner !is RuneInputMethodService) {
            val next = owner.baseContext
            check(next !== owner)
            owner = next
        }
        val window = checkNotNull((owner as? RuneInputMethodService)?.window?.window)
        val decor = window.decorView
        val width = decor.width
        val height = decor.height
        assertTrue(width > 0 && height > 0)
        val handler = Handler(worker.looper)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        try {
            val before = yellowPixels(window, bitmap, handler).first
            instrumentation.sendStatus(2, Bundle().apply {
                putInt("emoji_pixelcopy_negative_pixels", before)
                putInt("emoji_pixelcopy_negative_width", width)
                putInt("emoji_pixelcopy_negative_height", height)
            })
            assertTrue("Symbols layer must be a negative pixel control, count=$before size=${width}x$height", before < 100)
            val emoji = checkNotNull(driver.device.wait(Until.findObject(By.desc("Emoji")), 3_000))
            val bounds = emoji.visibleBounds
            val start = SystemClock.elapsedRealtimeNanos()
            val downTime = SystemClock.uptimeMillis()
            val down = MotionEvent.obtain(downTime, downTime, MotionEvent.ACTION_DOWN,
                bounds.exactCenterX(), bounds.exactCenterY(), 0)
            try {
                instrumentation.sendPointerSync(down)
                val up = MotionEvent.obtain(downTime, SystemClock.uptimeMillis(), MotionEvent.ACTION_UP,
                    bounds.exactCenterX(), bounds.exactCenterY(), 0)
                try { instrumentation.sendPointerSync(up) } finally { up.recycle() }
            } finally {
                down.recycle()
            }
            var count = 0
            var copies = 0
            var copiedAt = 0L
            val deadline = SystemClock.uptimeMillis() + 5_000
            while (SystemClock.uptimeMillis() < deadline && count < 500) {
                val sample = yellowPixels(window, bitmap, handler)
                count = sample.first
                copiedAt = sample.second
                copies++
                if (count < 500) SystemClock.sleep(8)
            }
            val elapsed = copiedAt - start
            assertTrue("PixelCopy completion must follow the tap", elapsed > 0)
            assertTrue("PixelCopy must observe a populated yellow emoji grid", count >= 500)
            assertTrue("The live IME must expose its emoji grid",
                driver.device.wait(Until.hasObject(By.clazz("android.widget.GridView")), 3_000))
            instrumentation.sendStatus(2, Bundle().apply {
                putLong("emoji_pixelcopy_upper_bound_nanos", elapsed)
                putInt("emoji_pixelcopy_yellow_before", before)
                putInt("emoji_pixelcopy_yellow_after", count)
                putInt("emoji_pixelcopy_attempts", copies)
                putInt("emoji_pixelcopy_width", width)
                putInt("emoji_pixelcopy_height", height)
                putInt("emoji_pixelcopy_api", Build.VERSION.SDK_INT)
            })
        } finally {
            bitmap.recycle()
        }
    }

    private fun yellowPixels(window: Window, bitmap: Bitmap, handler: Handler): Pair<Int, Long> {
        val done = CountDownLatch(1)
        val result = AtomicInteger(-1)
        val completedAt = AtomicLong()
        PixelCopy.request(window, bitmap, { status ->
            completedAt.set(SystemClock.elapsedRealtimeNanos())
            result.set(status)
            done.countDown()
        }, handler)
        assertTrue("PixelCopy callback timed out", done.await(3, TimeUnit.SECONDS))
        assertEquals("PixelCopy must copy the IME surface", PixelCopy.SUCCESS, result.get())
        val width = bitmap.width
        val height = bitmap.height
        val pixels = IntArray(width * height)
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height)
        // The Emoji key itself is on the bottom row. Count only the central panel body.
        var yellow = 0
        for (y in height / 4 until height / 2) {
            for (x in 0 until width) {
                val color = pixels[y * width + x]
                if (Color.red(color) > 180 && Color.green(color) > 110 && Color.blue(color) < 80) yellow++
            }
        }
        return yellow to completedAt.get()
    }
}
