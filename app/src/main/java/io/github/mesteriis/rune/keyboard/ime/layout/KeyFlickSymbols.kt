package io.github.mesteriis.rune.keyboard.ime.layout

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** English follows Apple's Key Flicks arrangement; Russian/Spanish fit Rune's native rows. */
internal object KeyFlickSymbols {
    private val english = mapRows(
        "qwertyuiop" to "1234567890",
        "asdfghjkl" to "@#$&*()'\"",
        "zxcvbnm" to "%-+=/;:",
    )
    private val russian = mapRows(
        "йцукенгшщзхъ" to "1234567890[]",
        "фывапролджэ" to "@#₽&*()'\":;",
        "ячсмитьбю" to "%-+=/?!«»",
    )
    private val spanish = english + mapOf("d" to "€", "ñ" to "¿")

    fun forLetter(letter: String, language: KeyboardLanguage): String? = when (language) {
        KeyboardLanguage.ENGLISH -> english[letter]
        KeyboardLanguage.RUSSIAN -> russian[letter]
        KeyboardLanguage.SPANISH -> spanish[letter]
    }

    private fun mapRows(vararg rows: Pair<String, String>): Map<String, String> = rows.flatMap { (letters, symbols) ->
        require(letters.length == symbols.length)
        letters.zip(symbols).map { (letter, symbol) -> letter.toString() to symbol.toString() }
    }.toMap()
}
