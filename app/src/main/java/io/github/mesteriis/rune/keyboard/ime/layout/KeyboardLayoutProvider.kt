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
    fun layoutFor(
        state: KeyboardState,
        editorContext: EditorContext,
        options: LayoutOptions = LayoutOptions.DEFAULT,
    ): KeyboardLayout = when (editorContext.mode) {
        EditorMode.NUMBER -> numberLayout(editorContext)
        EditorMode.PHONE -> phoneLayout(editorContext)
        EditorMode.DATE_TIME -> dateTimeLayout(editorContext)
        EditorMode.TEXT,
        EditorMode.EMAIL,
        EditorMode.URI,
        -> when (state.layer) {
            KeyboardLayer.SYMBOLS -> symbolsLayout(state, editorContext)
            KeyboardLayer.SYMBOLS_ALT -> symbolsAltLayout(state, editorContext)
            KeyboardLayer.LETTERS -> lettersLayout(state, editorContext, options)
        }
    }

    private fun lettersLayout(
        state: KeyboardState,
        editorContext: EditorContext,
        options: LayoutOptions,
    ): KeyboardLayout {
        val sourceRows = when (state.language) {
            KeyboardLanguage.ENGLISH -> ENGLISH_ROWS
            KeyboardLanguage.RUSSIAN -> RUSSIAN_ROWS
            KeyboardLanguage.SPANISH -> SPANISH_ROWS
        }
        val rowWeight = rowWeightFor(state.language)
        val rows = mutableListOf<List<KeySpec>>()
        if (options.showNumberRow) {
            rows += numberRow(rowWeight)
        }
        sourceRows.forEachIndexed { index, row ->
            val keys = row.map { letter -> letterKey(letter, state) }
            val composed = if (index == sourceRows.lastIndex) {
                listOf(shiftKey(state)) + keys + deleteKey()
            } else {
                keys
            }
            rows += padToWeight(composed, rowWeight)
        }
        rows += bottomRow(state, editorContext)
        return KeyboardLayout(rows)
    }

    private fun symbolsLayout(
        state: KeyboardState,
        editorContext: EditorContext,
    ): KeyboardLayout = KeyboardLayout(
        rows = listOf(
            characterRow("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"),
            listOf(
                characterKey("@"),
                characterKey("#"),
                currencyKey(state.language),
                characterKey("_"),
                characterKey("&"),
                symbolKey("-", state.language),
                characterKey("+"),
                symbolKey("(", state.language),
                symbolKey(")", state.language),
                symbolKey("/", state.language),
            ),
            listOf(symbolsPageKey(SYMBOLS_ALT_LABEL)) +
                listOf(
                    characterKey("*"),
                    symbolKey("\"", state.language),
                    symbolKey("'", state.language),
                    characterKey(":"),
                    characterKey(";"),
                    symbolKey("!", state.language),
                    symbolKey("?", state.language),
                ) +
                deleteKey(),
            bottomRow(state, editorContext, includeModeKey = false),
        ),
    )

    private fun symbolsAltLayout(
        state: KeyboardState,
        editorContext: EditorContext,
    ): KeyboardLayout = KeyboardLayout(
        rows = listOf(
            characterRow("€", "$", "£", "₽", "¥", "¢", "~", "`", "|", "\\"),
            characterRow("[", "]", "{", "}", "<", ">", "«", "»", "–", "—"),
            listOf(symbolsPageKey(SYMBOLS_LABEL)) +
                characterRow("=", "%", "¿", "¡", "…", "·", "§") +
                deleteKey(),
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

    /**
     * The bottom row keeps identical proportions on every layer and in every language so keys do
     * not jump when the layer or the language changes.
     */
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
        val modeKey = if (includeModeKey) symbolsKey() else lettersKey()
        val punctuationKey = symbolKey(punctuation, state.language, weight = PUNCTUATION_WEIGHT)
        val periodKey = symbolKey(".", state.language, weight = PUNCTUATION_WEIGHT)
        val enterKey = enterKey(editorContext)
        val spaceWeight = BOTTOM_ROW_WEIGHT -
            (modeKey.weight + punctuationKey.weight + periodKey.weight + enterKey.weight)
        return listOf(
            modeKey,
            punctuationKey,
            spaceKey(state.language, spaceWeight),
            periodKey,
            enterKey,
        )
    }

    private fun numberRow(rowWeight: Float): List<KeySpec> {
        val digits = listOf("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
        val weight = rowWeight / digits.size
        return digits.map { digit -> characterKey(digit, weight = weight) }
    }

    /** Centres a short row with half-key gutters instead of stretching its keys. */
    private fun padToWeight(row: List<KeySpec>, rowWeight: Float): List<KeySpec> {
        val remainder = rowWeight - row.sumOf { it.weight.toDouble() }.toFloat()
        if (remainder < WEIGHT_EPSILON) return row
        val gutter = KeySpec.spacer(remainder / 2f)
        return listOf(gutter) + row + gutter
    }

    private fun letterKey(letter: String, state: KeyboardState): KeySpec {
        val uppercase = state.shiftMode.usesUppercase
        val visibleLetter = if (uppercase) letter.uppercase(state.language.locale) else letter
        val alternates = LongPressAlternates.forLetter(letter, state.language).map { alternate ->
            KeyAlternate(
                label = if (uppercase) alternate.uppercase(state.language.locale) else alternate,
                action = KeyboardAction.CommitLetter(alternate),
            )
        }
        return KeySpec(
            label = visibleLetter,
            action = KeyboardAction.CommitLetter(letter),
            longPressAlternates = alternates,
        )
    }

    private fun characterRow(vararg values: String): List<KeySpec> = values.map { characterKey(it) }

    private fun characterKey(
        value: String,
        weight: Float = 1f,
        alternates: List<String> = emptyList(),
    ): KeySpec = KeySpec(
        label = value,
        action = KeyboardAction.CommitText(value),
        weight = weight,
        longPressAlternates = alternates.map { alternate ->
            KeyAlternate(label = alternate, action = KeyboardAction.CommitText(alternate))
        },
    )

    private fun symbolKey(
        value: String,
        language: KeyboardLanguage,
        weight: Float = 1f,
    ): KeySpec = characterKey(
        value = value,
        weight = weight,
        alternates = LongPressAlternates.forSymbol(value, language),
    )

    private fun currencyKey(language: KeyboardLanguage): KeySpec = characterKey(
        value = LongPressAlternates.currencyBase(language),
        alternates = LongPressAlternates.currencyAlternates(language),
    )

    private fun shiftKey(state: KeyboardState): KeySpec = KeySpec(
        label = if (state.shiftMode == ShiftMode.LOCKED) "⇪" else "⇧",
        action = KeyboardAction.Shift,
        weight = MODIFIER_WEIGHT,
        style = KeyStyle.ACTION,
    )

    private fun deleteKey(): KeySpec = KeySpec(
        label = "⌫",
        action = KeyboardAction.Delete,
        weight = MODIFIER_WEIGHT,
        style = KeyStyle.ACTION,
    )

    private fun symbolsKey(): KeySpec = KeySpec(
        label = SYMBOLS_LABEL,
        action = KeyboardAction.ToggleSymbols,
        weight = MODE_KEY_WEIGHT,
        style = KeyStyle.ACTION,
    )

    private fun lettersKey(): KeySpec = KeySpec(
        label = "ABC",
        action = KeyboardAction.ToggleSymbols,
        weight = MODE_KEY_WEIGHT,
        style = KeyStyle.ACTION,
    )

    private fun symbolsPageKey(label: String): KeySpec = KeySpec(
        label = label,
        action = KeyboardAction.ToggleSymbolsPage,
        weight = MODIFIER_WEIGHT,
        style = KeyStyle.ACTION,
    )

    private fun spaceKey(language: KeyboardLanguage, weight: Float): KeySpec = KeySpec(
        label = language.compactLabel,
        action = KeyboardAction.Space,
        weight = weight,
        style = KeyStyle.SPACE,
    )

    private fun enterKey(
        editorContext: EditorContext,
        weight: Float = ENTER_KEY_WEIGHT,
    ): KeySpec {
        // Mirrors KeyboardReducer.resolveEnterCommand so the label never promises the wrong action.
        val suppressAction = editorContext.imeOptions and EditorInfo.IME_FLAG_NO_ENTER_ACTION != 0 ||
            editorContext.isMultiLine
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

    private fun rowWeightFor(language: KeyboardLanguage): Float =
        if (language == KeyboardLanguage.RUSSIAN) RUSSIAN_ROW_WEIGHT else LATIN_ROW_WEIGHT

    internal companion object {
        const val MAX_CUSTOM_ACTION_LABEL_LENGTH = 8

        const val LATIN_ROW_WEIGHT = 10f
        const val RUSSIAN_ROW_WEIGHT = 12f
        const val BOTTOM_ROW_WEIGHT = 10f
        const val MODIFIER_WEIGHT = 1.5f
        const val MODE_KEY_WEIGHT = 1.3f
        const val PUNCTUATION_WEIGHT = 0.9f
        const val ENTER_KEY_WEIGHT = 1.25f
        const val WEIGHT_EPSILON = 0.01f

        const val SYMBOLS_LABEL = "?123"
        const val SYMBOLS_ALT_LABEL = "=\\<"

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

        val SPANISH_ROWS = listOf(
            listOf("q", "w", "e", "r", "t", "y", "u", "i", "o", "p"),
            listOf("a", "s", "d", "f", "g", "h", "j", "k", "l", "ñ"),
            listOf("z", "x", "c", "v", "b", "n", "m"),
        )
    }
}
