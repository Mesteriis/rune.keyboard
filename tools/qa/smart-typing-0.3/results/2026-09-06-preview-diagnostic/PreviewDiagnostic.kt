package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.view.View
import android.view.ViewConfiguration
import android.view.PixelCopy
import android.widget.PopupWindow
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Numeric test-only observation after the screenshot; no editor, labels or external windows. */
internal fun recordPreviewDiagnostic(down: Long, captureStart: Long, captureEnd: Long, screen: Bitmap) {
    val instrumentation = InstrumentationRegistry.getInstrumentation()
    val values = linkedMapOf("diagnostic_error" to 0)
    var request: PixelCopy.Request? = null
    val snapshot = runCatching { keyboardSnapshot() }.getOrElse {
        instrumentation.sendStatus(0, Bundle().apply {
            putString("preview_diagnostic", "diagnostic_error=1")
        })
        return
    }
    instrumentation.runOnMainSync {
        // Diagnostic failure must not crash main or replace the original screenshot assertion.
        runCatching {
            fun flag(name: String, value: Boolean) { values[name] = if (value) 1 else 0 }
            fun field(owner: Any, name: String): Any? = owner.javaClass.getDeclaredField(name)
                .apply { isAccessible = true }.get(owner)
            fun geometry(name: String, view: View?) {
                flag(name + "_present", view != null)
                if (view == null) return
                val location = IntArray(2)
                view.getLocationOnScreen(location)
                values[name + "_screen_x"] = location[0]; values[name + "_screen_y"] = location[1]
                view.getLocationInWindow(location)
                values[name + "_window_x"] = location[0]; values[name + "_window_y"] = location[1]
                values[name + "_width"] = view.width; values[name + "_height"] = view.height
                flag(name + "_attached", view.isAttachedToWindow)
                flag(name + "_shown", view.isShown)
                flag(name + "_laid_out", view.isLaidOut)
                flag(name + "_window_focus", view.hasWindowFocus())
            }
            val preferences = instrumentation.targetContext.getSharedPreferences(
                ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).all
            values["raw_preview"] = when (preferences[SettingsCodec.KEY_KEY_PREVIEW]) {
                true -> 1; false -> 0; null -> -1; else -> -2
            }
            flag("decoded_preview", SettingsCodec.decode(preferences).keyPreview)
            val keyboard = snapshot.keyboard
            flag("view_preview", field(keyboard, "previewEnabled") as Boolean)
            values["input_policy"] = (field(keyboard, "inputPolicy") as InputPolicy).ordinal
            values["active_touches"] = field(keyboard, "activeTouchCount") as Int
            flag("pending_render", field(keyboard, "pendingRender") != null)
            val pressed = snapshot.keys.filter { it.isPressed }
            values["pressed_keys"] = pressed.size
            val key = pressed.singleOrNull()
            if (key != null) {
                val spec = field(key, "spec") as KeySpec
                values["key_style"] = spec.style.ordinal
                values["alternate_count"] = spec.longPressAlternates.size
                flag("key_armed", field(key, "armed") as Boolean)
                flag("key_long_press", field(key, "longPressTriggered") as Boolean)
            }
            val controller = field(keyboard, "popupController")
            flag("controller", controller != null)
            var popup: PopupWindow? = null
            if (controller != null) {
                popup = field(controller, "previewPopup") as PopupWindow?
                flag("preview_owner_matches", key != null && field(controller, "previewOwner") === key)
                flag("alternate_owner", field(controller, "alternatesOwner") != null)
            }
            flag("preview_showing", popup?.isShowing == true)
            geometry("keyboard", keyboard); geometry("key", key); geometry("preview", popup?.contentView)
            if (Build.VERSION.SDK_INT >= 34 && popup?.isShowing == true) {
                val content = popup.contentView
                if (content.width in 1..512 && content.height in 1..512) {
                    val position = IntArray(2); content.getLocationInWindow(position)
                    request = PixelCopy.Request.Builder.ofWindow(content).setSourceRect(Rect(
                        position[0], position[1], position[0] + content.width, position[1] + content.height))
                        .setDestinationBitmap(Bitmap.createBitmap(content.width, content.height, Bitmap.Config.ARGB_8888))
                        .build()
                }
            }
            values["capture_start_after_down_ms"] = (captureStart - down).toInt()
            values["capture_duration_ms"] = (captureEnd - captureStart).toInt()
            values["observation_after_capture_ms"] = (SystemClock.uptimeMillis() - captureEnd).toInt()
            values["long_press_timeout_ms"] = ViewConfiguration.getLongPressTimeout()
        }.onFailure { values["diagnostic_error"] = 2 }
    }
    // Observe one queued popup buffer, never substitute it for the original screen assertion.
    // An alternate-bearing key stops at its platform deadline. The optional no-alternate
    // fixture allows at most one second after capture for this separate surface observation.
    if (Build.VERSION.SDK_INT >= 34 && request != null) {
        runCatching {
            val deadline = if (values["alternate_count"] == 0) captureEnd + 1_000L
                else down + ViewConfiguration.getLongPressTimeout()
            if (SystemClock.uptimeMillis() >= deadline) {
                values["pixelcopy_inconclusive"] = 1
            } else {
                val complete = CountDownLatch(1)
                val copied = linkedMapOf<String, Int>()
                val x0 = values.getValue("preview_screen_x"); val y0 = values.getValue("preview_screen_y")
                values["pixelcopy_request_after_down_ms"] = (SystemClock.uptimeMillis() - down).toInt()
                PixelCopy.request(checkNotNull(request), { it.run() }) { result ->
                    try {
                        copied["pixelcopy_status"] = result.status
                        copied["pixelcopy_completed_after_down_ms"] = (SystemClock.uptimeMillis() - down).toInt()
                        if (result.status == PixelCopy.SUCCESS) {
                            val bitmap = result.bitmap
                            var opaque = 0; var different = 0; var visible = 0
                            for (y in 0 until bitmap.height) for (x in 0 until bitmap.width) {
                                val pixel = bitmap.getPixel(x, y)
                                if (pixel ushr 24 != 0) visible++
                                if (pixel ushr 24 == 255) {
                                    opaque++
                                    if (x0 + x in 0 until screen.width && y0 + y in 0 until screen.height &&
                                        screen.getPixel(x0 + x, y0 + y) != pixel) different++
                                }
                            }
                            copied["pixelcopy_nontransparent"] = visible
                            copied["pixelcopy_opaque"] = opaque
                            copied["pixelcopy_opaque_screen_difference"] = different
                            bitmap.recycle()
                        }
                    } catch (_: Throwable) {
                        copied["pixelcopy_diagnostic_error"] = 1
                    } finally { complete.countDown() }
                }
                val remaining = (deadline - SystemClock.uptimeMillis()).coerceAtLeast(0)
                if (complete.await(remaining, TimeUnit.MILLISECONDS)) values.putAll(copied)
                else values["pixelcopy_inconclusive"] = 1
            }
        }.onFailure { values["pixelcopy_diagnostic_error"] = 2 }
    }
    instrumentation.sendStatus(0, Bundle().apply {
        putString("preview_diagnostic", values.entries.joinToString(" ") { "${it.key}=${it.value}" })
    })
}
