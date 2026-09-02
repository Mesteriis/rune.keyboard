package io.github.mesteriis.rune.keyboard.smarttyping.correction

import java.util.Locale

enum class CasePattern {
    LOWER,
    TITLE,
    UPPER,
    MIXED,
    UNCASED;

    /** Null forbids automatic case rewriting of mixed/uncased input or an oversized result. */
    fun preserve(candidate: String): String? {
        val normalized = TokenUnicode.nfc(candidate)
        val preserved = when (this) {
            LOWER -> normalized.lowercase(Locale.ROOT)
            UPPER -> normalized.uppercase(Locale.ROOT)
            TITLE -> {
                val lower = normalized.lowercase(Locale.ROOT)
                var offset = 0
                while (offset < lower.length) {
                    val cp = lower.codePointAt(offset)
                    if (Character.isLowerCase(cp) || Character.isUpperCase(cp) || Character.isTitleCase(cp)) break
                    offset += Character.charCount(cp)
                }
                if (offset == lower.length) return null
                val cp = lower.codePointAt(offset)
                val end = offset + Character.charCount(cp)
                val title = if (Character.isBmpCodePoint(cp)) cp.toChar().titlecase(Locale.ROOT)
                    else String(Character.toChars(Character.toTitleCase(cp)))
                lower.substring(0, offset) + title + lower.substring(end)
            }
            MIXED, UNCASED -> return null
        }
        return if (TokenUnicode.bounded(preserved)) TokenUnicode.nfc(preserved) else null
    }

    companion object {
        fun analyze(token: String): CasePattern {
            val normalized = TokenUnicode.nfc(token)
            var offset = 0
            var cased = 0
            var uppercase = 0
            var firstUppercase = false
            while (offset < normalized.length) {
                val cp = normalized.codePointAt(offset)
                val upper = Character.isUpperCase(cp) || Character.isTitleCase(cp)
                if (upper || Character.isLowerCase(cp)) {
                    if (cased == 0) firstUppercase = upper
                    cased++
                    if (upper) uppercase++
                }
                offset += Character.charCount(cp)
            }
            return when {
                cased == 0 -> UNCASED
                uppercase == 0 -> LOWER
                uppercase == cased -> UPPER
                uppercase == 1 && firstUppercase -> TITLE
                else -> MIXED
            }
        }
    }
}
