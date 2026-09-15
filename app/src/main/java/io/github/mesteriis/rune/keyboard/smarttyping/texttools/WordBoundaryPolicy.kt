package io.github.mesteriis.rune.keyboard.smarttyping.texttools

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Bounded dictionary-only proposals; never authorizes an automatic replacement. */
object WordBoundaryPolicy {
    /**
     * Context includes the current composing word. [contains] receives lowercase, language-scoped keys.
     * It must be bounded and return exact membership; throw on unavailable or incomplete lookup.
     */
    fun suggest(context: String, language: KeyboardLanguage, contains: (String) -> Boolean): TextToolSuggestion? {
        if (!TextToolInput.valid(context)) return null
        val trailing = if (context.endsWith(' ')) " " else ""
        val body = context.removeSuffix(trailing)
        val tokenStart = body.lastIndexOfAny(charArrayOf(' ', '\n')) + 1
        val token = body.substring(tokenStart)
        if (!TextToolInput.word(token, language)) return null
        // At most 1 original + 2 fragment + 1 join + 54 split lookups for a 32-letter token.
        return try {
            val candidates = mutableListOf<TextToolSuggestion>()
            val tokenKnown = contains(TextToolInput.fold(token))
            join(body, tokenStart, token, tokenKnown, trailing, language, contains)?.let(candidates::add)
            if (!tokenKnown) candidates += splits(token, trailing, language, contains)
            candidates.singleOrNull()
        } catch (_: RuntimeException) {
            // An unavailable dictionary cannot support a proposal. No input or exception is logged.
            null
        }
    }

    private fun splits(token: String, trailing: String, language: KeyboardLanguage,
        contains: (String) -> Boolean): List<TextToolSuggestion> {
        val folded = TextToolInput.fold(token)
        val curated = if (language == KeyboardLanguage.RUSSIAN) CURATED_SPLITS[folded] else null
        val points = token.codePointCount(0, token.length)
        val positions = if (curated != null) listOf(curated) else (3..points - 3).map {
            token.offsetByCodePoints(0, it)
        }
        val candidates = mutableListOf<TextToolSuggestion>()
        for (position in positions) {
            val left = token.substring(0, position)
            val right = token.substring(position)
            if (!contains(TextToolInput.fold(left)) || !contains(TextToolInput.fold(right))) continue
            candidates += TextToolSuggestion(token + trailing, "$left $right$trailing", TextToolKind.WORD_SPLIT)
            if (candidates.size == 2) break
        }
        return candidates
    }

    private fun join(body: String, tokenStart: Int, token: String, tokenKnown: Boolean, trailing: String,
        language: KeyboardLanguage, contains: (String) -> Boolean): TextToolSuggestion? {
        if (tokenStart == 0 || body[tokenStart - 1] != ' ' || token != TextToolInput.fold(token)) return null
        val previousEnd = tokenStart - 1
        val previousStart = body.lastIndexOfAny(charArrayOf(' ', '\n'), previousEnd - 1) + 1
        val previous = body.substring(previousStart, previousEnd)
        if (!TextToolInput.word(previous, language) ||
            previous.codePointCount(0, previous.length) < 2 || token.codePointCount(0, token.length) < 2) return null
        val joined = previous + token
        if (!TextToolInput.word(joined, language)) return null
        if (tokenKnown && contains(TextToolInput.fold(previous))) return null
        if (!contains(TextToolInput.fold(joined))) return null
        return TextToolSuggestion("$previous $token$trailing", joined + trailing, TextToolKind.WORD_JOIN)
    }

    private val CURATED_SPLITS = mapOf("незнаю" to 2, "потомучто" to 6)
}
