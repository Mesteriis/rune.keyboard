package io.github.mesteriis.rune.keyboard.smarttyping.correction

import java.util.Locale

enum class ProtectedTokenReason {
    TOO_LONG,
    MALFORMED_UNICODE,
    PATH_OR_IDENTIFIER,
    MIXED_SCRIPT,
    UNSUPPORTED_SCRIPT,
    LETTERS_AND_DIGITS,
    MIXED_CASE,
    ALL_CAPS,
    TECHNICAL_HYPHEN,
    UNUSUAL_SYMBOL,
    NON_WORD,
}

/** Conservative shape policy; it never reads editor context or decides AutoReplace. */
object ProtectedTokenPolicy {
    fun isProtected(token: String): Boolean = reason(token) != null

    fun reason(token: String): ProtectedTokenReason? {
        if (token.length > 64 || token.codePointCount(0, token.length) > 32) {
            return ProtectedTokenReason.TOO_LONG
        }
        if (!TokenUnicode.bounded(token)) return ProtectedTokenReason.MALFORMED_UNICODE
        val normalized = TokenUnicode.nfcOrNull(token) ?: return ProtectedTokenReason.TOO_LONG
        if (TokenUnicode.nfcOrNull(normalized.lowercase(Locale.ROOT)) == null) return ProtectedTokenReason.TOO_LONG
        var script: Character.UnicodeScript? = null
        var letters = 0
        var digits = 0
        var unusual = false
        var technicalHyphen = false
        var identifier = false
        var unsupported = false
        var mixed = false
        var offset = 0
        var followsLetter = false
        while (offset < normalized.length) {
            val cp = normalized.codePointAt(offset)
            val next = offset + Character.charCount(cp)
            val current = Character.UnicodeScript.of(cp)
            if (current != Character.UnicodeScript.COMMON && current != Character.UnicodeScript.INHERITED) {
                if (script != null && script != current) mixed = true
                script = current
                if (current != Character.UnicodeScript.LATIN && current != Character.UnicodeScript.CYRILLIC) {
                    unsupported = true
                }
            }
            when {
                cp == '/'.code || cp == '\\'.code || cp == '@'.code || cp == '_'.code -> identifier = true
                Character.isLetter(cp) -> letters++
                Character.isDigit(cp) -> digits++
                TokenUnicode.isMark(cp) -> if (!followsLetter) unusual = true
                cp == '-'.code -> technicalHyphen = true
                cp == '\''.code || cp == '’'.code -> {
                    if (!followsLetter || next == normalized.length ||
                        !Character.isLetter(normalized.codePointAt(next))) unusual = true
                }
                else -> unusual = true
            }
            followsLetter = Character.isLetter(cp) || (TokenUnicode.isMark(cp) && followsLetter)
            offset = next
        }
        val case = CasePattern.analyze(normalized)
        return when {
            mixed -> ProtectedTokenReason.MIXED_SCRIPT
            identifier -> ProtectedTokenReason.PATH_OR_IDENTIFIER
            unsupported -> ProtectedTokenReason.UNSUPPORTED_SCRIPT
            letters > 0 && digits > 0 -> ProtectedTokenReason.LETTERS_AND_DIGITS
            unusual -> ProtectedTokenReason.UNUSUAL_SYMBOL
            technicalHyphen -> ProtectedTokenReason.TECHNICAL_HYPHEN
            letters == 0 -> ProtectedTokenReason.NON_WORD
            case == CasePattern.MIXED -> ProtectedTokenReason.MIXED_CASE
            letters > 1 && case == CasePattern.UPPER -> ProtectedTokenReason.ALL_CAPS
            else -> null
        }
    }
}
