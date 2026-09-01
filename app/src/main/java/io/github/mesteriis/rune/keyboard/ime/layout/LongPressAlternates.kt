package io.github.mesteriis.rune.keyboard.ime.layout

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/**
 * Alternate characters reachable by holding a key (INPUT-108). Sets depend on the active
 * language: accents where the language uses them, Cyrillic extras and guillemets for Russian.
 */
object LongPressAlternates {
    val CURRENCIES: List<String> = listOf("€", "$", "£", "₽", "¥", "¢")

    private val LATIN_ACCENTS_ENGLISH = mapOf(
        "a" to listOf("á", "à", "â", "ä", "æ"),
        "e" to listOf("é", "è", "ê", "ë"),
        "i" to listOf("í", "ì", "î", "ï"),
        "o" to listOf("ó", "ò", "ô", "ö"),
        "u" to listOf("ú", "ù", "û", "ü"),
        "n" to listOf("ñ"),
        "c" to listOf("ç"),
    )

    private val LATIN_ACCENTS_SPANISH = mapOf(
        "a" to listOf("á", "à", "â", "ä"),
        "e" to listOf("é", "è", "ê", "ë"),
        "i" to listOf("í", "ì", "î", "ï"),
        "o" to listOf("ó", "ò", "ô", "ö"),
        "u" to listOf("ú", "ü", "ù", "û"),
        "c" to listOf("ç"),
    )

    private val CYRILLIC_EXTRAS = mapOf(
        "е" to listOf("ё"),
        "ь" to listOf("ъ"),
    )

    private val SYMBOLS_SHARED = mapOf(
        "'" to listOf("‘", "’", "‚"),
        "-" to listOf("–", "—", "·"),
        "!" to listOf("¡"),
        "?" to listOf("¿"),
        "(" to listOf("[", "{", "<"),
        ")" to listOf("]", "}", ">"),
        "/" to listOf("\\"),
    )

    private val QUOTES_RUSSIAN = listOf("«", "»", "„", "“", "”")
    private val QUOTES_LATIN = listOf("“", "”", "«", "»")

    private val PERIOD_ALTERNATES_LATIN = listOf("…", "'", "\"", "-", "_", "@", "/")
    private val PERIOD_ALTERNATES_RUSSIAN = listOf("…", "\"", "-", "_", "@", "/")

    fun forLetter(letter: String, language: KeyboardLanguage): List<String> = when (language) {
        KeyboardLanguage.ENGLISH -> LATIN_ACCENTS_ENGLISH[letter]
        KeyboardLanguage.SPANISH -> LATIN_ACCENTS_SPANISH[letter]
        KeyboardLanguage.RUSSIAN -> CYRILLIC_EXTRAS[letter]
    }.orEmpty()

    fun forSymbol(symbol: String, language: KeyboardLanguage): List<String> = when (symbol) {
        "\"" -> if (language == KeyboardLanguage.RUSSIAN) QUOTES_RUSSIAN else QUOTES_LATIN
        "." -> if (language == KeyboardLanguage.RUSSIAN) {
            PERIOD_ALTERNATES_RUSSIAN
        } else {
            PERIOD_ALTERNATES_LATIN
        }
        else -> SYMBOLS_SHARED[symbol].orEmpty()
    }

    fun currencyBase(language: KeyboardLanguage): String = when (language) {
        KeyboardLanguage.ENGLISH -> "$"
        KeyboardLanguage.RUSSIAN -> "₽"
        KeyboardLanguage.SPANISH -> "€"
    }

    fun currencyAlternates(language: KeyboardLanguage): List<String> {
        val base = currencyBase(language)
        return CURRENCIES.filter { it != base }
    }
}
