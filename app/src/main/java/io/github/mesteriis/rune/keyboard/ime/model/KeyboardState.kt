package io.github.mesteriis.rune.keyboard.ime.model

import java.util.Locale

enum class KeyboardLanguage(
    val locale: Locale,
    val compactLabel: String,
    val displayLabel: String,
) {
    ENGLISH(Locale.US, "EN", "English"),
    RUSSIAN(Locale.forLanguageTag("ru-RU"), "RU", "Русский"),
    SPANISH(Locale.forLanguageTag("es-ES"), "ES", "Español"),
}

enum class LanguageDirection {
    PREVIOUS,
    NEXT,
}

enum class KeyboardLayer {
    LETTERS,
    SYMBOLS,
    SYMBOLS_ALT,
}

enum class ShiftMode {
    OFF,
    AUTO,
    ONCE,
    LOCKED;

    val usesUppercase: Boolean
        get() = this != OFF
}

data class KeyboardState(
    val language: KeyboardLanguage,
    val enabledLanguages: List<KeyboardLanguage> = DEFAULT_LANGUAGES,
    val layer: KeyboardLayer = KeyboardLayer.LETTERS,
    val shiftMode: ShiftMode = ShiftMode.OFF,
    val doubleSpacePeriodEnabled: Boolean = true,
    val pendingDoubleSpaceUndo: Boolean = false,
    private val lastShiftTapAtMillis: Long? = null,
) {
    init {
        require(enabledLanguages.isNotEmpty()) { "At least one language must stay enabled" }
    }

    fun onShiftPressed(nowMillis: Long): KeyboardState = when (shiftMode) {
        ShiftMode.AUTO -> copy(shiftMode = ShiftMode.OFF, lastShiftTapAtMillis = nowMillis)
        ShiftMode.OFF -> {
            val followsAutomaticShiftTap = lastShiftTapAtMillis?.let { previousTap ->
                nowMillis - previousTap in 0..DOUBLE_TAP_WINDOW_MILLIS
            } ?: false
            copy(
                shiftMode = if (followsAutomaticShiftTap) ShiftMode.LOCKED else ShiftMode.ONCE,
                lastShiftTapAtMillis = if (followsAutomaticShiftTap) null else nowMillis,
            )
        }
        ShiftMode.ONCE -> {
            val isDoubleTap = lastShiftTapAtMillis?.let { previousTap ->
                nowMillis - previousTap in 0..DOUBLE_TAP_WINDOW_MILLIS
            } ?: false
            copy(
                shiftMode = if (isDoubleTap) ShiftMode.LOCKED else ShiftMode.OFF,
                lastShiftTapAtMillis = null,
            )
        }
        ShiftMode.LOCKED -> copy(shiftMode = ShiftMode.OFF, lastShiftTapAtMillis = null)
    }

    fun afterTextCommitted(): KeyboardState = when (shiftMode) {
        ShiftMode.AUTO,
        ShiftMode.ONCE,
        -> copy(shiftMode = ShiftMode.OFF, lastShiftTapAtMillis = null)
        ShiftMode.OFF,
        ShiftMode.LOCKED,
        -> this
    }

    fun withAutomaticCapitalization(enabled: Boolean): KeyboardState = when (shiftMode) {
        ShiftMode.OFF,
        ShiftMode.AUTO,
        -> copy(
            shiftMode = if (enabled) ShiftMode.AUTO else ShiftMode.OFF,
            lastShiftTapAtMillis = null,
        )
        ShiftMode.ONCE,
        ShiftMode.LOCKED,
        -> this
    }

    fun toggleSymbols(): KeyboardState = copy(
        layer = if (layer == KeyboardLayer.LETTERS) KeyboardLayer.SYMBOLS else KeyboardLayer.LETTERS,
        shiftMode = ShiftMode.OFF,
        lastShiftTapAtMillis = null,
    )

    fun toggleSymbolsPage(): KeyboardState = when (layer) {
        KeyboardLayer.SYMBOLS -> copy(layer = KeyboardLayer.SYMBOLS_ALT)
        KeyboardLayer.SYMBOLS_ALT -> copy(layer = KeyboardLayer.SYMBOLS)
        KeyboardLayer.LETTERS -> this
    }

    fun switchLanguage(direction: LanguageDirection): KeyboardState {
        val currentIndex = enabledLanguages.indexOf(language)
        val target = if (currentIndex < 0) {
            enabledLanguages.first()
        } else {
            val step = if (direction == LanguageDirection.NEXT) 1 else enabledLanguages.size - 1
            enabledLanguages[(currentIndex + step) % enabledLanguages.size]
        }
        // A swipe that cannot change the language must not reset the layer or shift either.
        return if (target == language) this else useLanguage(target)
    }

    fun useLanguage(language: KeyboardLanguage): KeyboardState = copy(
        language = language,
        layer = KeyboardLayer.LETTERS,
        shiftMode = ShiftMode.OFF,
        lastShiftTapAtMillis = null,
    )

    fun withEnabledLanguages(languages: List<KeyboardLanguage>): KeyboardState {
        require(languages.isNotEmpty()) { "At least one language must stay enabled" }
        val coercedLanguage = if (language in languages) language else languages.first()
        return copy(
            language = coercedLanguage,
            enabledLanguages = languages,
            layer = if (coercedLanguage == language) layer else KeyboardLayer.LETTERS,
        )
    }

    fun clearDoubleSpaceUndo(): KeyboardState =
        if (pendingDoubleSpaceUndo) copy(pendingDoubleSpaceUndo = false) else this

    companion object {
        const val DOUBLE_TAP_WINDOW_MILLIS = 400L

        val DEFAULT_LANGUAGES: List<KeyboardLanguage> = listOf(
            KeyboardLanguage.ENGLISH,
            KeyboardLanguage.RUSSIAN,
            KeyboardLanguage.SPANISH,
        )

        fun initial(
            language: KeyboardLanguage,
            automaticCapitalization: Boolean,
            enabledLanguages: List<KeyboardLanguage> = DEFAULT_LANGUAGES,
            doubleSpacePeriodEnabled: Boolean = true,
        ): KeyboardState = KeyboardState(
            language = if (language in enabledLanguages) language else enabledLanguages.first(),
            enabledLanguages = enabledLanguages,
            shiftMode = if (automaticCapitalization) ShiftMode.AUTO else ShiftMode.OFF,
            doubleSpacePeriodEnabled = doubleSpacePeriodEnabled,
        )
    }
}
