package io.github.mesteriis.rune.keyboard.smarttyping.texttools

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Finite Russian rules for a completed Rune-owned sentence; not a general grammar checker. */
object PhraseReviewPolicy {
    fun suggest(context: String, language: KeyboardLanguage): TextToolSuggestion? {
        if (language != KeyboardLanguage.RUSSIAN || !TextToolInput.valid(context)) return null
        val trailing = if (context.endsWith(' ')) " " else ""
        val body = context.removeSuffix(trailing)
        if (body.isEmpty() || body.last() !in TERMINATORS) return null
        val contentEnd = body.lastIndex
        if (contentEnd == 0 || body[contentEnd - 1] in TERMINATORS) return null
        val previousEnd = body.lastIndexOfAny(TERMINATORS + '\n', contentEnd - 1)
        if (previousEnd >= 0 && body[previousEnd] != '\n' &&
            (previousEnd + 1 == contentEnd || body[previousEnd + 1] != ' ')) return null
        val start = (previousEnd + 1 until contentEnd).firstOrNull { body[it] != ' ' } ?: return null
        val sentence = body.substring(start, contentEnd)
        if (sentence.any { it != ' ' && it != ',' && it !in 'а'..'я' && it !in 'А'..'Я' && it != 'ё' && it != 'Ё' }) return null
        val words = WORD.findAll(sentence).toList()
        if (words.size !in 2..40 || words.first().range.first != 0 ||
            words.any { !TextToolInput.word(it.value, language) }) return null
        val clause = clause(words, 0, sentence) ?: return null
        val edits = mutableListOf<Edit>()
        val verb = words[clause.verbIndex]
        if (verb.value != clause.expectedVerb) {
            // Only a lowercase predicate immediately after the sentence's explicit personal subject.
            if (verb.value != TextToolInput.fold(verb.value)) return null
            edits += Edit(verb.range.first, verb.range.last + 1, clause.expectedVerb)
        }
        comma(words, sentence, clause)?.let(edits::add)
        if (edits.isEmpty()) return null
        var replacement = sentence
        for (edit in edits.sortedByDescending { it.start }) {
            replacement = replacement.replaceRange(edit.start, edit.end, edit.value)
        }
        val source = body.substring(start) + trailing
        val result = replacement + body.last() + trailing
        if (result.length > TextToolInput.MAX_CONTEXT_UTF16) return null
        return TextToolSuggestion(source, result, TextToolKind.PHRASE_REVIEW)
    }

    private data class Clause(val verbIndex: Int, val expectedVerb: String)
    private data class Edit(val start: Int, val end: Int, val value: String)

    private fun clause(words: List<MatchResult>, start: Int, sentence: String): Clause? {
        val subject = words.getOrNull(start) ?: return null
        val person = PERSON[TextToolInput.fold(subject.value)] ?: return null
        var index = start + 1
        if (words.getOrNull(index)?.value == "не") index++
        val verb = words.getOrNull(index) ?: return null
        for (i in start until index) {
            if (sentence.substring(words[i].range.last + 1, words[i + 1].range.first).any { it != ' ' }) return null
        }
        val forms = VERBS.firstOrNull { TextToolInput.fold(verb.value) in it } ?: return null
        return Clause(index, forms[person])
    }

    private fun comma(words: List<MatchResult>, sentence: String, main: Clause): Edit? {
        // A single subordinate clause; existing commas and multiple conjunctions are left intact.
        if (',' in sentence) return null
        val conjunctions = words.indices.filter { words[it].value == "что" }
        if (conjunctions.size != 1) return null
        val what = conjunctions.single()
        val because = what > 0 && words[what - 1].value == "потому"
        val boundary = if (because) what - 1 else what
        if (boundary <= main.verbIndex) return null
        if (because) {
            if (words.subList(0, boundary).any { it.value in CAUSAL_FOCUS }) return null
        } else if (main.expectedVerb !in COMPLEMENT_VERBS || boundary != main.verbIndex + 1) return null
        val subordinate = clause(words, what + 1, sentence) ?: return null
        if (words[subordinate.verbIndex].value != subordinate.expectedVerb) return null
        val insertion = words[boundary - 1].range.last + 1
        return Edit(insertion, insertion, ",")
    }

    private val TERMINATORS = charArrayOf('.', '!', '?')
    private val WORD = Regex("[А-Яа-яЁё]+")
    private val PERSON = mapOf("я" to 0, "ты" to 1, "он" to 2, "она" to 2, "оно" to 2,
        "мы" to 3, "вы" to 4, "они" to 5)
    private val VERBS = listOf(
        listOf("иду", "идешь", "идет", "идем", "идете", "идут"),
        listOf("иду", "идёшь", "идёт", "идём", "идёте", "идут"),
        listOf("знаю", "знаешь", "знает", "знаем", "знаете", "знают"),
        listOf("думаю", "думаешь", "думает", "думаем", "думаете", "думают"),
        listOf("понимаю", "понимаешь", "понимает", "понимаем", "понимаете", "понимают"),
        listOf("хочу", "хочешь", "хочет", "хотим", "хотите", "хотят"),
        listOf("могу", "можешь", "может", "можем", "можете", "могут"),
    )
    private val COMPLEMENT_VERBS = VERBS.filter { it.first() in setOf("знаю", "думаю", "понимаю") }.flatten().toSet()
    private val CAUSAL_FOCUS = setOf("не", "только", "лишь", "именно", "особенно", "даже")
}
