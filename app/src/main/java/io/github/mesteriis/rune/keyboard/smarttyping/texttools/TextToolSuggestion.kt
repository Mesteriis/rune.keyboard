package io.github.mesteriis.rune.keyboard.smarttyping.texttools

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import java.util.Locale

enum class TextToolKind { WORD_SPLIT, WORD_JOIN, PHRASE_REVIEW }

/** RAM-only proposal. The caller must revalidate ownership and require explicit selection. */
data class TextToolSuggestion(
    val sourceSuffix: String,
    val replacementSuffix: String,
    val kind: TextToolKind,
) {
    override fun toString(): String = "TextToolSuggestion(kind=$kind, text=redacted)"
}

internal object TextToolInput {
    const val MAX_CONTEXT_UTF16 = 256

    /** Reject oversized input: truncating can manufacture a word or sentence boundary. */
    fun valid(context: String): Boolean {
        if (context.isEmpty() || context.length > MAX_CONTEXT_UTF16) return false
        var offset = 0
        while (offset < context.length) {
            val char = context[offset]
            if (Character.isLowSurrogate(char) || Character.isHighSurrogate(char) &&
                (offset + 1 == context.length || !Character.isLowSurrogate(context[offset + 1]))) return false
            if (Character.isISOControl(char) && char != '\n') return false
            offset += Character.charCount(context.codePointAt(offset))
        }
        return true
    }

    fun word(token: String, language: KeyboardLanguage): Boolean {
        if (token.isEmpty() || ProtectedTokenPolicy.isProtected(token)) return false
        val script = when (language) {
            KeyboardLanguage.RUSSIAN -> Character.UnicodeScript.CYRILLIC
            KeyboardLanguage.ENGLISH, KeyboardLanguage.SPANISH -> Character.UnicodeScript.LATIN
        }
        // Combining-mark and apostrophe boundaries need a separate lexical policy. Fail closed.
        return token.codePoints().allMatch { Character.isLetter(it) && Character.UnicodeScript.of(it) == script }
    }

    fun fold(token: String): String = token.lowercase(Locale.ROOT)
}
