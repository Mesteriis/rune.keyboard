package io.github.mesteriis.rune.keyboard.settings

import android.content.Context
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

class KeyboardPreferences(context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    fun readLanguage(): KeyboardLanguage? = preferences
        .getString(KEY_LANGUAGE, null)
        ?.let { storedValue ->
            runCatching { KeyboardLanguage.valueOf(storedValue) }.getOrNull()
        }

    fun writeLanguage(language: KeyboardLanguage) {
        preferences.edit().putString(KEY_LANGUAGE, language.name).apply()
    }

    private companion object {
        const val PREFERENCES_NAME = "keyboard_preferences"
        const val KEY_LANGUAGE = "language"
    }
}

