package io.github.mesteriis.rune.keyboard.ime.layout

import android.view.inputmethod.EditorInfo
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.ShiftMode

class KeyboardLayoutProvider {
    fun layoutFor(state: KeyboardState, editorContext: EditorContext): KeyboardLayout = when (editorContext.mode) {
        EditorMode.NUMBER -> numberLayout(editorContext)
        EditorMode.PHONE -> phoneLayout(editorContext)
        EditorMode.DATE_TIME -> dateTimeLayout(editorContext)
        EditorMode.TEXT,
        EditorMode.EMAIL,
        EditorMode.URI,
        -> if (state.layer == KeyboardLayer.SYMBOLS) {
            symbolsLayout(state, editorContext)
        } else {
            lettersLayout(state, editorContext)
        }
    }

    private fun lettersLayout(
        state: KeyboardState,
        editorContext: EditorContext,
    ): KeyboardLayout {
        val sourceRows = when (state.language) {
            KeyboardLanguage.ENGLISH -> ENGLISH_ROWS
            KeyboardLanguage.RUSSIAN -> RUSSIAN_ROWS
        }
        val rows = sourceRows.map { row -> row.map { letter -> letterKey(letter, state) } }.toMutableList()
        rows[2] = listOf(shiftKey(state)) + rows[2] + deleteKey()
        rows += bottomRow(state, editorContext)
        return KeyboardLayout(rows)
    }

    private fun symbolsLayout(
        state: KeyboardState,
        editorContext: EditorContext,
    ): KeyboardLayout = KeyboardLayout(
        rows = listOf(
            characterRow("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"),
            characterRow("@", "#", "₽", "_", "&", "-", "+", "(", ")", "/"),
            characterRow("=", "*", "%", "\"", "'", ":", ";", "!", "?") + deleteKey(),
            bottomRow(state, editorContext, includeModeKey = false),
        ),
    )

    private fun numberLayout(editorContext: EditorContext): KeyboardLayout {
        val signKey = if (editorContext.allowsSignedNumber) characterKey("-") else KeySpec.spacer()
        val decimalKey = if (editorContext.allowsDecimalNumber) characterKey(".") else KeySpec.spacer()
        return KeyboardLayout(
            rows = listOf(
                characterRow("1", "2", "3") + deleteKey(),
                characterRow("4", "5", "6") + signKey,
                characterRow("7", "8", "9") + decimalKey,
                listOf(KeySpec.spacer(), characterKey("0"), enterKey(editorContext, weight = 2f)),
            ),
        )
    }

    private fun phoneLayout(editorContext: EditorContext): KeyboardLayout = KeyboardLayout(
        rows = listOf(
            characterRow("1", "2", "3") + deleteKey(),
            characterRow("4", "5", "6") + characterKey("+"),
            characterRow("7", "8", "9") + characterKey("#"),
            listOf(characterKey("*"), characterKey("0"), enterKey(editorContext, weight = 2f)),
        ),
    )

    private fun dateTimeLayout(editorContext: EditorContext): KeyboardLayout = KeyboardLayout(
        rows = listOf(
            characterRow("1", "2", "3") + deleteKey(),
            characterRow("4", "5", "6") + characterKey("/"),
            characterRow("7", "8", "9") + characterKey(":"),
            listOf(characterKey("."), characterKey("0"), enterKey(editorContext, weight = 2f)),
        ),
    )

    private fun bottomRow(
        state: KeyboardState,
        editorContext: EditorContext,
        includeModeKey: Boolean = true,
    ): List<KeySpec> {
        val punctuation = when (editorContext.mode) {
            EditorMode.EMAIL -> "@"
            EditorMode.URI -> "/"
            else -> ","
        }
        return buildList {
            if (includeModeKey) add(symbolsKey()) else add(lettersKey())
            add(languageKey(state.language))
            add(characterKey(punctuation, weight = 0.9f))
            add(spaceKey(state.language))
            add(characterKey(".", weight = 0.9f))
            add(enterKey(editorContext))
        }
    }

    private fun letterKey(letter: String, state: KeyboardState): KeySpec {
        val visibleLetter = if (state.shiftMode.usesUppercase) {
            letter.uppercase(state.language.locale)
        } else {
            letter
        }
        val longPressAction = if (letter == "е") {
            KeyboardAction.CommitLetter("ё")
        } else {
            null
        }
        return KeySpec(
            label = visibleLetter,
            action = KeyboardAction.CommitLetter(letter),
            longPressAction = longPressAction,
        )
    }

    private fun characterRow(vararg values: String): List<KeySpec> = values.map(::characterKey)

    private fun characterKey(value: String, weight: Float = 1f): KeySpec = KeySpec(
        label = value,
        action = KeyboardAction.CommitText(value),
        weight = weight,
    )

    private fun shiftKey(state: KeyboardState): KeySpec = KeySpec(
        label = if (state.shiftMode == ShiftMode.LOCKED) "⇪" else "⇧",
        action = KeyboardAction.Shift,
        weight = 1.35f,
        style = KeyStyle.ACTION,
    )

    private fun deleteKey(): KeySpec = KeySpec(
        label = "⌫",
        action = KeyboardAction.Delete,
        weight = 1.35f,
        style = KeyStyle.ACTION,
    )

    private fun symbolsKey(): KeySpec = KeySpec(
        label = "?123",
        action = KeyboardAction.ToggleSymbols,
        weight = 1.3f,
        style = KeyStyle.ACTION,
    )

    private fun lettersKey(): KeySpec = KeySpec(
        label = "ABC",
        action = KeyboardAction.ToggleSymbols,
        weight = 1.3f,
        style = KeyStyle.ACTION,
    )

    private fun languageKey(language: KeyboardLanguage): KeySpec = KeySpec(
        label = if (language == KeyboardLanguage.ENGLISH) "RU" else "EN",
        action = KeyboardAction.ToggleLanguage,
        weight = 1.1f,
        style = KeyStyle.ACTION,
        longPressAction = KeyboardAction.NextInputMethod,
    )

    private fun spaceKey(language: KeyboardLanguage): KeySpec = KeySpec(
        label = if (language == KeyboardLanguage.ENGLISH) "English" else "Русский",
        action = KeyboardAction.Space,
        weight = 4f,
        style = KeyStyle.SPACE,
    )

    private fun enterKey(
        editorContext: EditorContext,
        weight: Float = 1.25f,
    ): KeySpec {
        val suppressAction = editorContext.imeOptions and EditorInfo.IME_FLAG_NO_ENTER_ACTION != 0
        val customLabel = if (suppressAction) {
            null
        } else {
            editorContext.customActionLabel?.trim()?.takeIf(String::isNotEmpty)
        }
        val actionId = if (suppressAction) {
            EditorInfo.IME_ACTION_NONE
        } else {
            editorContext.imeOptions and EditorInfo.IME_MASK_ACTION
        }
        val label = customLabel?.take(MAX_CUSTOM_ACTION_LABEL_LENGTH) ?: when (actionId) {
            EditorInfo.IME_ACTION_GO -> "→"
            EditorInfo.IME_ACTION_SEARCH -> "⌕"
            EditorInfo.IME_ACTION_SEND -> "➤"
            EditorInfo.IME_ACTION_NEXT -> "›"
            EditorInfo.IME_ACTION_DONE -> "✓"
            EditorInfo.IME_ACTION_PREVIOUS -> "‹"
            else -> "↵"
        }
        return KeySpec(
            label = label,
            action = KeyboardAction.Enter,
            weight = weight,
            style = KeyStyle.ACTION,
            accessibilityLabel = customLabel,
        )
    }

    private companion object {
        const val MAX_CUSTOM_ACTION_LABEL_LENGTH = 8

        val ENGLISH_ROWS = listOf(
            listOf("q", "w", "e", "r", "t", "y", "u", "i", "o", "p"),
            listOf("a", "s", "d", "f", "g", "h", "j", "k", "l"),
            listOf("z", "x", "c", "v", "b", "n", "m"),
        )

        val RUSSIAN_ROWS = listOf(
            listOf("й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ъ"),
            listOf("ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"),
            listOf("я", "ч", "с", "м", "и", "т", "ь", "б", "ю"),
        )
    }
}
