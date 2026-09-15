package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.AbbreviationStore
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import io.github.mesteriis.rune.keyboard.smarttyping.texttools.PhraseReviewPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.texttools.WordBoundaryPolicy

class AndroidTypingTools(
    private val resources: PersonalTypingResources,
    private val abbreviations: AbbreviationStore,
) : TypingTools {
    var boundariesEnabled = false
    var abbreviationsEnabled = false
    var reviewEnabled = false

    override fun suggestions(context: String, word: String, language: KeyboardLanguage): List<TypingToolSuggestion> = buildList {
        if (abbreviationsEnabled && abbreviations.isReady && word.isNotEmpty()) {
            abbreviations.model.expansion(word, language)?.let {
                add(TypingToolSuggestion(word, it, TypingToolKind.ABBREVIATION))
            }
        }
        if (reviewEnabled) PhraseReviewPolicy.suggest(context, language)?.let {
            add(TypingToolSuggestion(it.sourceSuffix, it.replacementSuffix, TypingToolKind.PHRASE_REVIEW))
        }
        if (boundariesEnabled && resources.dictionaryLoaded) {
            WordBoundaryPolicy.suggest(context, language) { token ->
                val membership = resources.lexicon.lookup(language, token)
                check(membership.available) { "Dictionary unavailable" }
                membership.present
            }?.let { add(TypingToolSuggestion(it.sourceSuffix, it.replacementSuffix, TypingToolKind.WORD_BOUNDARY)) }
        }
    }
}
