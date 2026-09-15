package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Only suggestions. The controller validates the entire current owned suffix before writing. */
enum class TypingToolKind { WORD_BOUNDARY, ABBREVIATION, PHRASE_REVIEW }
class TypingToolSuggestion(val sourceSuffix: String, val replacementSuffix: String, val kind: TypingToolKind) {
    override fun toString() = "TypingToolSuggestion(kind=$kind, redacted)"
}
fun interface TypingTools {
    fun suggestions(context: String, word: String, language: KeyboardLanguage): List<TypingToolSuggestion>
}
object NoTypingTools : TypingTools {
    override fun suggestions(context: String, word: String, language: KeyboardLanguage) = emptyList<TypingToolSuggestion>()
}
