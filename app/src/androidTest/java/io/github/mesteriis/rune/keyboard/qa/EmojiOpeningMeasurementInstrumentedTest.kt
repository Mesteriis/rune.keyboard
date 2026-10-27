package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.widget.GridView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayoutProvider
import io.github.mesteriis.rune.keyboard.ime.layout.LayoutOptions
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardReducer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.settings.SetupActivity
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import org.junit.Assert.*
import org.junit.Test

/** Measurement validity is the test result; the published 50 ms budget has a separate result. */
class EmojiOpeningMeasurementInstrumentedTest {
    @Test fun measureFreshPaletteHandlerAndFirstDrawStart() {
        check(Build.HARDWARE in setOf("ranchu", "goldfish"))
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
            repeat(4) { sample ->
                lateinit var keyboard: RuneKeyboardView
                var listener: ViewTreeObserver.OnDrawListener? = null
                val start = AtomicLong()
                val firstDraw = AtomicLong()
                val handler = AtomicLong()
                val drawn = CountDownLatch(1)
                var setup: Result<Unit>? = null
                scenario.onActivity { activity ->
                    setup = runCatching {
                        val density = activity.resources.displayMetrics.density
                        keyboard = RuneKeyboardView(activity, KeyboardViewMetrics((48 * density).toInt(), (3 * density).toInt()))
                        // Match SetupActivity's embedded preview: the shell owns system insets.
                        keyboard.setOnApplyWindowInsetsListener { _, insets -> insets }
                        val layouts = KeyboardLayoutProvider()
                        val editor = EditorContext.from(1, 0)
                        var state = KeyboardState(KeyboardLanguage.ENGLISH)
                        val options = LayoutOptions(emojiKey = true)
                        keyboard.setOnActionListener { action ->
                            state = KeyboardReducer.reduce(state, action, editor, 0).state
                            keyboard.render(layouts.layoutFor(state, editor, options), state)
                        }
                        keyboard.render(layouts.layoutFor(state, editor, options), state)
                        val host = activity.findViewById<ViewGroup>(R.id.menu_preview)
                        host.removeAllViews()
                        host.addView(keyboard)
                    }
                }
                checkNotNull(setup).getOrThrow()
                instrumentation.waitForIdleSync()
                var clicked: Result<Unit>? = null
                scenario.onActivity {
                    clicked = runCatching {
                        keyboard.requestRectangleOnScreen(android.graphics.Rect(0, 0, keyboard.width, keyboard.height), true)
                        val drawListener = ViewTreeObserver.OnDrawListener {
                            val observed = System.nanoTime()
                            if (start.get() != 0L && descendants(keyboard).filterIsInstance<GridView>().any { grid ->
                                grid.childCount > 0 && grid.isShown && grid.getGlobalVisibleRect(android.graphics.Rect())
                            } && firstDraw.compareAndSet(0L, observed)) drawn.countDown()
                        }
                        listener = drawListener
                        keyboard.viewTreeObserver.addOnDrawListener(drawListener)
                        val key = descendants(keyboard).single { it.contentDescription == "Emoji" }
                        start.set(System.nanoTime())
                        assertTrue(key.performClick())
                        handler.set(System.nanoTime() - start.get())
                    }
                }
                try {
                    checkNotNull(clicked).getOrThrow()
                    assertTrue("A populated native grid must reach draw", drawn.await(5, TimeUnit.SECONDS))
                    val drawStart = firstDraw.get() - start.get()
                    assertTrue(drawStart >= handler.get() && handler.get() > 0)
                    val geometry = Bundle()
                    scenario.onActivity { activity ->
                        geometry.putInt("emoji_measurement_width_px", keyboard.width)
                        geometry.putInt("emoji_measurement_height_px", keyboard.height)
                        geometry.putInt("emoji_measurement_density_dpi", activity.resources.displayMetrics.densityDpi)
                        geometry.putFloat("emoji_measurement_font_scale", activity.resources.configuration.fontScale)
                    }
                    instrumentation.sendStatus(2, Bundle().apply {
                        putAll(geometry)
                        putInt("emoji_measurement_api", Build.VERSION.SDK_INT)
                        putInt("emoji_measurement_sample", sample)
                        putLong("emoji_handler_nanos", handler.get())
                        putLong("emoji_first_draw_start_nanos", drawStart)
                        putLong("emoji_budget_nanos", 50_000_000)
                        putBoolean("emoji_handler_budget_pass", handler.get() <= 50_000_000)
                        putBoolean("emoji_draw_start_budget_pass", drawStart <= 50_000_000)
                    })
                } finally {
                    scenario.onActivity { listener?.let { drawListener ->
                        if (keyboard.viewTreeObserver.isAlive) keyboard.viewTreeObserver.removeOnDrawListener(drawListener)
                    } }
                }
            }
        }
    }

    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
}
