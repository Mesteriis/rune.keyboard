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
import org.junit.Assert.assertNull
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
    fun `spanish layout includes the alphabet and a dedicated n-tilde key`() {
        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.SPANISH), textEditor)
        val values = committedValues(layout)

        assertTrue(('a'..'z').all { letter -> letter.toString() in values })
        assertTrue("ñ" in values)
    }

    @Test
    fun `spanish accents are reachable through long press`() {
        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.SPANISH), textEditor)
        val alternates = alternateValues(layout)

        assertTrue(listOf("á", "é", "í", "ó", "ú", "ü").all { accent -> accent in alternates })
    }

    @Test
    fun `shifted spanish shows uppercase labels on keys and alternates`() {
        val state = KeyboardState(language = KeyboardLanguage.SPANISH, shiftMode = ShiftMode.LOCKED)

        val layout = provider.layoutFor(state, textEditor)
        val keys = layout.rows.flatten()

        assertNotNull(keys.firstOrNull { it.label == "Ñ" })
        val aKey = keys.first { it.action == KeyboardAction.CommitLetter("a") }
        assertEquals("A", aKey.label)
        assertEquals("Á", aKey.longPressAlternates.first().label)
        assertEquals(KeyboardAction.CommitLetter("á"), aKey.longPressAlternates.first().action)
    }

    @Test
    fun `russian shifted layout includes uppercase letters and yo long press`() {
        val state = KeyboardState(
            language = KeyboardLanguage.RUSSIAN,
            shiftMode = ShiftMode.LOCKED,
        )
        val layout = provider.layoutFor(state, textEditor)
        val eKey = layout.rows.flatten().first { it.label == "Е" }

        assertTrue("Й" in layout.rows.flatten().map { it.label })
        assertTrue("й" in committedValues(layout))
        assertEquals("Ё", eKey.longPressAlternates.single().label)
        assertEquals(KeyboardAction.CommitLetter("ё"), eKey.longPressAlternates.single().action)
    }

    @Test
    fun `russian guillemets and dashes are reachable`() {
        val symbols = KeyboardState(KeyboardLanguage.RUSSIAN).toggleSymbols()

        val alternates = alternateValues(provider.layoutFor(symbols, textEditor))

        assertTrue(listOf("«", "»", "–", "—").all { symbol -> symbol in alternates })
    }

    @Test
    fun `both symbol pages together cover the required inventory`() {
        val symbols = KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols()
        val alt = symbols.toggleSymbolsPage()
        val available = committedValues(provider.layoutFor(symbols, textEditor)) +
            committedValues(provider.layoutFor(alt, textEditor))

        val required = listOf(
            ".", ",", "?", "!", ":", ";", "@", "#", "%", "&", "*", "-", "_", "+", "=",
            "/", "\\", "|", "~", "`", "'", "\"", "(", ")", "[", "]", "{", "}", "<", ">",
            "€", "$", "£", "₽", "…", "«", "»", "–", "—", "¿", "¡",
        )

        required.forEach { symbol ->
            assertTrue(symbol, symbol in available)
        }
    }

    @Test
    fun `the currency key follows the language and keeps the rest reachable`() {
        KeyboardLanguage.entries.forEach { language ->
            val symbols = KeyboardState(language).toggleSymbols()
            val layout = provider.layoutFor(symbols, textEditor)
            val expectedBase = LongPressAlternates.currencyBase(language)
            val currencyKey = layout.rows.flatten().first { it.label == expectedBase }

            assertEquals(
                LongPressAlternates.CURRENCIES.toSet(),
                currencyKey.longPressAlternates.map { it.label }.toSet() + expectedBase,
            )
        }
    }

    @Test
    fun `each symbol page offers a way to the other page and back to letters`() {
        val symbols = KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols()
        val alt = symbols.toggleSymbolsPage()

        listOf(symbols, alt).forEach { state ->
            val keys = provider.layoutFor(state, textEditor).rows.flatten()

            assertEquals(1, keys.count { it.action == KeyboardAction.ToggleSymbolsPage })
            assertEquals(1, keys.count { it.action == KeyboardAction.ToggleSymbols })
        }
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
    fun `multi-line editor labels the enter key as newline`() {
        val context = EditorContext.from(
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
            EditorInfo.IME_ACTION_DONE,
        )

        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), context)
        val enterKey = layout.rows.flatten().first { it.action == KeyboardAction.Enter }

        assertEquals("↵", enterKey.label)
        assertNull(enterKey.accessibilityLabel)
    }

    @Test
    fun `the space bar carries the compact language label`() {
        KeyboardLanguage.entries.forEach { language ->
            val layout = provider.layoutFor(KeyboardState(language), textEditor)
            val spaceKey = layout.rows.flatten().first { it.action == KeyboardAction.Space }

            assertEquals(language.compactLabel, spaceKey.label)
            assertEquals(KeyStyle.SPACE, spaceKey.style)
        }
    }

    @Test
    fun `bottom rows omit redundant keyboard chrome`() {
        val states = listOf(
            KeyboardState(KeyboardLanguage.ENGLISH),
            KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols(),
            KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols().toggleSymbolsPage(),
        )

        states.forEach { state ->
            val keys = provider.layoutFor(state, textEditor).rows.flatten()

            assertTrue(keys.none { it.action == KeyboardAction.HideKeyboard })
            assertTrue(keys.none { it.action == KeyboardAction.NextInputMethod })
            assertTrue(keys.none { it.action is KeyboardAction.SwitchLanguage })
        }
    }

    @Test
    fun `the number row appears only when enabled`() {
        val state = KeyboardState(KeyboardLanguage.ENGLISH)
        val digits = (0..9).map(Int::toString)

        val withoutRow = provider.layoutFor(state, textEditor, LayoutOptions(showNumberRow = false))
        val withRow = provider.layoutFor(state, textEditor, LayoutOptions(showNumberRow = true))

        assertTrue(digits.none { digit -> digit in committedValues(withoutRow) })
        assertTrue(digits.all { digit -> digit in committedValues(withRow) })
        assertEquals(withoutRow.rows.size + 1, withRow.rows.size)
    }

    @Test
    fun `the number row never reaches the symbol pages`() {
        val symbols = KeyboardState(KeyboardLanguage.ENGLISH).toggleSymbols()

        val layout = provider.layoutFor(symbols, textEditor, LayoutOptions(showNumberRow = true))

        assertEquals(4, layout.rows.size)
    }

    @Test
    fun `letter rows share one weight grid per language`() {
        KeyboardLanguage.entries.forEach { language ->
            val expected = if (language == KeyboardLanguage.RUSSIAN) {
                KeyboardLayoutProvider.RUSSIAN_ROW_WEIGHT
            } else {
                KeyboardLayoutProvider.LATIN_ROW_WEIGHT
            }
            val layout = provider.layoutFor(
                KeyboardState(language),
                textEditor,
                LayoutOptions(showNumberRow = true),
            )

            layout.rows.dropLast(1).forEach { row ->
                assertEquals(language.name, expected, rowWeight(row), WEIGHT_TOLERANCE)
            }
            assertEquals(
                language.name,
                KeyboardLayoutProvider.BOTTOM_ROW_WEIGHT,
                rowWeight(layout.rows.last()),
                WEIGHT_TOLERANCE,
            )
        }
    }

    @Test
    fun `symbol page rows share the latin weight grid`() {
        val symbols = KeyboardState(KeyboardLanguage.RUSSIAN).toggleSymbols()

        listOf(symbols, symbols.toggleSymbolsPage()).forEach { state ->
            provider.layoutFor(state, textEditor).rows.forEach { row ->
                assertEquals(
                    KeyboardLayoutProvider.LATIN_ROW_WEIGHT,
                    rowWeight(row),
                    WEIGHT_TOLERANCE,
                )
            }
        }
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
    fun `the phone layout stays free of keyboard chrome`() {
        val phoneEditor = EditorContext.from(InputType.TYPE_CLASS_PHONE, EditorInfo.IME_ACTION_DONE)

        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.ENGLISH), phoneEditor)
        val keys = layout.rows.flatten()

        assertTrue(keys.none { it.action == KeyboardAction.HideKeyboard })
        assertTrue(keys.none { it.action == KeyboardAction.Space })
        assertTrue(committedValues(layout).containsAll(listOf("+", "#", "*")))
    }

    @Test
    fun `every visible key has a valid action and positive weight`() {
        val layout = provider.layoutFor(KeyboardState(KeyboardLanguage.RUSSIAN), textEditor)

        layout.rows.flatten().forEach { key ->
            assertTrue(key.weight > 0f)
            if (key.style != KeyStyle.SPACER) assertNotNull(key.action)
        }
    }

    private fun rowWeight(row: List<KeySpec>): Float = row.sumOf { it.weight.toDouble() }.toFloat()

    private fun committedValues(layout: KeyboardLayout): List<String> = layout.rows
        .flatten()
        .mapNotNull { key ->
            when (val action = key.action) {
                is KeyboardAction.CommitLetter -> action.value
                is KeyboardAction.CommitText -> action.value
                else -> null
            }
        }

    private fun alternateValues(layout: KeyboardLayout): List<String> = layout.rows
        .flatten()
        .flatMap { key -> key.longPressAlternates }
        .mapNotNull { alternate ->
            when (val action = alternate.action) {
                is KeyboardAction.CommitLetter -> action.value
                is KeyboardAction.CommitText -> action.value
                else -> null
            }
        }

    private companion object {
        const val WEIGHT_TOLERANCE = 0.001f
    }
}
