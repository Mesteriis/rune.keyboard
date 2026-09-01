package io.github.mesteriis.rune.keyboard.ime.layout

import android.text.InputType
import android.view.inputmethod.EditorInfo
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.ShiftMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class KeyboardLayoutProviderTest {
    private val provider = KeyboardLayoutProvider()
    private val textEditor = EditorContext.from(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_NONE)

    @Test
    fun `english layout includes all alphabet letters`() {
        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), textEditor)
        val committedLetters = committedValues(layout).filter { value -> value.length == 1 && value[0].isLetter() }

        assertTrue(('a'..'z').all { letter -> letter.toString() in committedLetters })
    }

    @Test
    fun `russian shifted layout includes uppercase letters and yo long press`() {
        val state = KeyboardState(
            language = KeyboardLanguage.RUSSIAN,
            shiftMode = ShiftMode.LOCKED,
        )
        val layout = provider.layoutFor(state, textEditor)
        val eKey = layout.rows.flatten().first { it.label == "Е" }

        assertTrue("Й" in committedValues(layout))
        assertEquals(KeyboardAction.CommitLetter("ё"), eKey.longPressAction)
    }

    @Test
    fun `email layout exposes at key`() {
        val emailEditor = EditorContext.from(
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,
            EditorInfo.IME_ACTION_NEXT,
        )

        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), emailEditor)

        assertTrue("@" in committedValues(layout))
    }

    @Test
    fun `symbols layout exposes a single letters key`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols()

        val layout = provider.layoutFor(state, textEditor)

        assertEquals(1, layout.rows.flatten().count { it.action == KeyboardAction.ToggleSymbols })
    }

    @Test
    fun `search editor exposes search action key`() {
        val searchEditor = EditorContext.from(
            InputType.TYPE_CLASS_TEXT,
            EditorInfo.IME_ACTION_SEARCH,
        )

        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), searchEditor)

        assertEquals("⌕", layout.rows.flatten().first { it.action == KeyboardAction.Enter }.label)
    }

    @Test
    fun `no-enter-action exposes newline even with custom label`() {
        val context = textEditor.copy(
            imeOptions = EditorInfo.IME_ACTION_SEND or EditorInfo.IME_FLAG_NO_ENTER_ACTION,
            customActionId = 7,
            customActionLabel = "Send now",
        )

        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), context)

        assertEquals("↵", layout.rows.flatten().first { it.action == KeyboardAction.Enter }.label)
    }

    @Test
    fun `integer layout omits signed and decimal actions`() {
        val integerEditor = EditorContext.from(InputType.TYPE_CLASS_NUMBER, EditorInfo.IME_ACTION_DONE)

        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), integerEditor)
        val values = committedValues(layout)

        assertTrue((0..9).all { digit -> digit.toString() in values })
        assertTrue("-" !in values)
        assertTrue("." !in values)
        assertNotNull(layout.rows.flatten().firstOrNull { it.action == KeyboardAction.Delete })
    }

    @Test
    fun `every visible key has a valid action and positive weight`() {
        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.RUSSIAN), textEditor)

        layout.rows.flatten().forEach { key ->
            assertTrue(key.weight > 0f)
            if (key.style != KeyStyle.SPACER) assertNotNull(key.action)
        }
    }

    private fun committedValues(layout: KeyboardLayout): List<String> = layout.rows
        .flatten()
        .mapNotNull { key ->
            when (val action = key.action) {
                is KeyboardAction.CommitLetter -> key.label
                is KeyboardAction.CommitText -> action.value
                else -> null
            }
        }
}
