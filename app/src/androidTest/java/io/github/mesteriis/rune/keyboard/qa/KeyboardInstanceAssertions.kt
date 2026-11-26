package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
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
            // The home screen now embeds a RuneKeyboardView preview. Only the input-method
            // window belongs to the resident service exercised by Binder/lifecycle tests.
            roots.filter { (it.layoutParams as? WindowManager.LayoutParams)?.type ==
                WindowManager.LayoutParams.TYPE_INPUT_METHOD }.forEach(::findKeyboard)
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

/** Isolate a test-owned controller that drives the real editor connection directly. */
internal fun independentControllerConnection(): android.view.inputmethod.InputConnection {
    val keyboard = keyboardSnapshot().keyboard
    var result: Result<android.view.inputmethod.InputConnection>? = null
    InstrumentationRegistry.getInstrumentation().runOnMainSync {
        result = runCatching {
            var owner: android.content.Context = keyboard.rootView.context
            while (owner is android.content.ContextWrapper && owner !is android.inputmethodservice.InputMethodService) {
                val next = owner.baseContext
                check(next !== owner)
                owner = next
            }
            val service = checkNotNull(owner as? io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService)
            val field = service.javaClass.getDeclaredField("typingSession").apply { isAccessible = true }
            val resident = field.get(service) as io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
            // This does not touch the editor. It prevents the resident owner from treating
            // the independent test controller's composing spans as foreign editor mutations.
            resident.endSession()
            check(!resident.state.enabled)
            checkNotNull(service.currentInputConnection)
        }
    }
    return checkNotNull(result).getOrThrow()
}
