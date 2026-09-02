package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Static neighbours from verified layout rows; no touch data or device geometry. */
object KeyboardDistance {
    fun areAdjacent(first: Int, second: Int, language: KeyboardLanguage): Boolean {
        if (first == second) return false
        val rows = when (language) {
            KeyboardLanguage.ENGLISH -> ENGLISH
            KeyboardLanguage.RUSSIAN -> RUSSIAN
            KeyboardLanguage.SPANISH -> SPANISH
        }
        // Fixed half-key offsets, intentionally a feature approximation rather than measured positions.
        for (rowA in rows.indices) {
            val colA = rows[rowA].indexOf(first.toChar())
            if (colA < 0 || first > Char.MAX_VALUE.code || second > Char.MAX_VALUE.code) continue
            for (rowB in rows.indices) {
                val colB = rows[rowB].indexOf(second.toChar())
                if (colB < 0) continue
                val dx = kotlin.math.abs(2 * colA + OFFSETS[rowA] - 2 * colB - OFFSETS[rowB])
                val dy = kotlin.math.abs(rowA - rowB)
                return (dy == 0 && dx == 2) || (dy == 1 && dx <= 1)
            }
        }
        return false
    }

    private val ENGLISH = arrayOf("qwertyuiop", "asdfghjkl", "zxcvbnm")
    private val OFFSETS = intArrayOf(0, 1, 2)
    private val RUSSIAN = arrayOf("йцукенгшщзхъ", "фывапролджэ", "ячсмитьбю")
    private val SPANISH = arrayOf("qwertyuiop", "asdfghjklñ", "zxcvbnm")
}
