package io.github.mesteriis.rune.keyboard.ime.model

import java.util.Locale

enum class KeyboardLanguage(val locale: Locale) {
    ENGLISH(Locale.US),
    RUSSIAN(Locale.forLanguageTag("ru-RU"));

    fun toggled(): KeyboardLanguage = when (this) {
        ENGLISH -> RUSSIAN
        RUSSIAN -> ENGLISH
    }

    companion object {
        fun fromLanguageTag(languageTag: String?): KeyboardLanguage =
            if (languageTag?.startsWith("ru", ignoreCase = true) == true) RUSSIAN else ENGLISH
    }
}

enum class KeyboardLayer {
    LETTERS,
    SYMBOLS,
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
    val layer: KeyboardLayer = KeyboardLayer.LETTERS,
    val shiftMode: ShiftMode = ShiftMode.OFF,
    private val lastShiftTapAtMillis: Long? = null,
) {
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

    fun toggleLanguage(): KeyboardState = copy(
        language = language.toggled(),
        layer = KeyboardLayer.LETTERS,
        shiftMode = ShiftMode.OFF,
        lastShiftTapAtMillis = null,
    )

    fun useLanguage(language: KeyboardLanguage): KeyboardState = copy(
        language = language,
        layer = KeyboardLayer.LETTERS,
        shiftMode = ShiftMode.OFF,
        lastShiftTapAtMillis = null,
    )

    companion object {
        const val DOUBLE_TAP_WINDOW_MILLIS = 400L

        fun initial(
            language: KeyboardLanguage,
            automaticCapitalization: Boolean,
        ): KeyboardState = KeyboardState(
            language = language,
            shiftMode = if (automaticCapitalization) ShiftMode.AUTO else ShiftMode.OFF,
        )
    }
}
