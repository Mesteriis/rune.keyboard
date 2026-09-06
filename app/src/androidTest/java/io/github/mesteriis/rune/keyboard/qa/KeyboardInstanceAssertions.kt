package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.view.View
import android.view.ViewGroup
import android.view.inspector.WindowInspector
import io.github.mesteriis.rune.keyboard.ime.ui.CancelableKey
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*

/** Test-local references only; inspect our in-process IME tree, never external windows/text. */
internal fun keyboardSnapshot(): KeyboardSnapshot {
    var result: Result<KeyboardSnapshot>? = null
    InstrumentationRegistry.getInstrumentation().runOnMainSync {
        // Propagate inspection/assertion failures on the test thread, not the app main thread.
        result = runCatching {
            val roots = if (Build.VERSION.SDK_INT >= 29) {
                WindowInspector.getGlobalWindowViews()
            } else {
                // Legacy test-only inspection; public WindowInspector is available from API29.
                val type = Class.forName("android.view.WindowManagerGlobal")
                val owner = type.getDeclaredMethod("getInstance").invoke(null)
                val field = type.getDeclaredField("mViews").apply { isAccessible = true }
                (field.get(owner) as List<*>).map { it as View }
            }
            val keyboards = mutableListOf<RuneKeyboardView>()
            fun findKeyboard(view: View) {
                if (view is RuneKeyboardView) {
                    if (view.isShown) keyboards.add(view)
                } else if (view is ViewGroup) {
                    for (index in 0 until view.childCount) findKeyboard(view.getChildAt(index))
                }
            }
            roots.forEach(::findKeyboard)
            assertEquals("Expected one visible in-process Rune keyboard", 1, keyboards.size)
            val keyboard = keyboards.single()
            val keys = mutableListOf<View>()
            fun collectKeys(view: View) {
                if (view is CancelableKey) keys.add(view)
                if (view is ViewGroup) {
                    for (index in 0 until view.childCount) collectKeys(view.getChildAt(index))
                }
            }
            collectKeys(keyboard)
            assertTrue("Expected actual Rune key instances", keys.isNotEmpty())
            KeyboardSnapshot(keyboard, keys)
        }
    }
    return checkNotNull(result) { "Keyboard inspection did not complete" }.getOrThrow()
}

internal fun assertSameKeys(expected: KeyboardSnapshot, actual: KeyboardSnapshot) {
    // assertSame would format View.toString on failure; report no view/text payloads.
    assertTrue("Keyboard instance changed", expected.keyboard === actual.keyboard)
    assertEquals("Key instance count changed", expected.keys.size, actual.keys.size)
    expected.keys.indices.forEach { index ->
        assertTrue("Key instance changed at index $index", expected.keys[index] === actual.keys[index])
    }
}

internal class KeyboardSnapshot(val keyboard: RuneKeyboardView, val keys: List<View>)
