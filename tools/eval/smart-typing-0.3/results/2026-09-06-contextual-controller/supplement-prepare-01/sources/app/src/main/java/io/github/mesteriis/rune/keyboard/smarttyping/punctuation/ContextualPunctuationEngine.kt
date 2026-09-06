package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Pure bounded rule engine. Model I/O and editor ownership remain outside this type. */
object ContextualPunctuationEngine {
    data class Variant(val id: Int, val boundary: String, val continuation: String)

    fun variants(prefix: String, currentWord: String, language: KeyboardLanguage): List<Variant> {
        if (!ordinaryWord(currentWord) || !hasOrdinaryLeftWord(prefix)) return emptyList()
        val capitalized = capitalizeFirst(currentWord, language)
        return listOf(
            Variant(0, " ", " $currentWord"),
            Variant(1, ", ", ", $currentWord"),
            Variant(2, ": ", ": $currentWord"),
            Variant(3, "; ", "; $currentWord"),
            Variant(4, ". ", ". $capitalized"),
            Variant(5, "? ", "? $capitalized"),
            Variant(6, "! ", "! $capitalized"),
        )
    }

    private fun hasOrdinaryLeftWord(prefix: String): Boolean {
        if (prefix.isEmpty() || prefix.last().isWhitespace()) return false
        var start = prefix.length
        while (start > 0) {
            val cp = prefix.codePointBefore(start)
            if (!Character.isLetter(cp) && !isMark(cp)) break
            start -= Character.charCount(cp)
        }
        if (start == prefix.length || start > 0 && !prefix[start - 1].isWhitespace()) return false
        return ordinaryWord(prefix.substring(start))
    }

    private fun ordinaryWord(value: String): Boolean {
        if (value.isEmpty() || value.length > 64 || value.codePointCount(0, value.length) > 32) return false
        var script: Character.UnicodeScript? = null
        var letters = 0
        var uppercase = 0
        var firstUpper = false
        var offset = 0
        while (offset < value.length) {
            val cp = value.codePointAt(offset)
            if (Character.isLetter(cp)) {
                val current = Character.UnicodeScript.of(cp)
                if (current != Character.UnicodeScript.LATIN && current != Character.UnicodeScript.CYRILLIC) return false
                if (script != null && script != current) return false
                script = current
                val upper = Character.isUpperCase(cp) || Character.isTitleCase(cp)
                if (letters == 0) firstUpper = upper
                letters++
                if (upper) uppercase++
            } else if (!isMark(cp) || letters == 0) return false
            offset += Character.charCount(cp)
        }
        return letters > 0 && (uppercase == 0 || uppercase == 1 && firstUpper)
    }

    private fun capitalizeFirst(word: String, language: KeyboardLanguage): String {
        val end = Character.charCount(word.codePointAt(0))
        return word.substring(0, end).uppercase(language.locale) + word.substring(end)
    }

    private fun isMark(cp: Int) = Character.getType(cp) in MARK_TYPES
    private val MARK_TYPES = setOf(Character.NON_SPACING_MARK.toInt(),
        Character.COMBINING_SPACING_MARK.toInt(), Character.ENCLOSING_MARK.toInt())
}
