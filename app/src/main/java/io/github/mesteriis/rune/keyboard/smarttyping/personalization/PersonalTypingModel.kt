package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.text.Normalizer
import java.util.Locale

/** Explicit feedback is separate from phrase frequency. None of this model grants auto admission. */
class PersonalTypingModel(
    private val dictionaryContains: (String, KeyboardLanguage) -> Boolean,
) {
    private val feedback = linkedMapOf<FeedbackKey, PersonalFeedback>()
    private val confirmed = linkedSetOf<PersonalWord>()
    private val phrases = linkedMapOf<PhraseKey, PersonalPhrase>()

    @Synchronized fun recordAccepted(original: String, replacement: String, language: KeyboardLanguage) {
        val key = feedbackKey(original, replacement, language) ?: return
        val old = feedback[key]
        if (old == null && feedback.size >= MAX_FEEDBACK) return
        feedback[key] = PersonalFeedback(language, key.original, key.replacement,
            ((old?.accepted ?: 0) + 1).coerceAtMost(MAX_COUNT), old?.rejected ?: false)
        recordConfirmedWord(replacement, language)
    }

    /** Call only after an acknowledged manual retype, never from a guessed correction. */
    @Synchronized fun recordManualRetype(original: String, replacement: String, language: KeyboardLanguage) =
        recordAccepted(original, replacement, language)

    @Synchronized fun recordRejected(original: String, replacement: String, language: KeyboardLanguage) {
        val key = feedbackKey(original, replacement, language) ?: return
        val old = feedback[key]
        if (old == null && feedback.size >= MAX_FEEDBACK) {
            // Rejections take precedence over positive-only pairs when capacity is exhausted.
            feedback.entries.firstOrNull { !it.value.rejected }?.let { feedback.remove(it.key) }
            if (feedback.size >= MAX_FEEDBACK) return
        }
        feedback[key] = PersonalFeedback(language, key.original, key.replacement, old?.accepted ?: 0, true)
    }

    @Synchronized fun recordConfirmedWord(word: String, language: KeyboardLanguage) {
        val normalized = normalizeWord(word) ?: return
        if (confirmed.size < MAX_CONFIRMED) confirmed.add(PersonalWord(language, normalized))
    }

    @Synchronized fun rejects(original: String, replacement: String, language: KeyboardLanguage): Boolean {
        val key = feedbackKey(original, replacement, language) ?: return false
        return feedback[key]?.rejected ?: rejectionTableFull()
    }

    // Never silently re-enable automatic changes after running out of room for rejection evidence.
    // A saturated rejection-only table vetoes unknown pairs until the user resets the profile.
    private fun rejectionTableFull() = feedback.size >= MAX_FEEDBACK && feedback.values.all { it.rejected }

    @Synchronized fun protectsOriginal(word: String, language: KeyboardLanguage): Boolean =
        normalizeWord(word)?.let { PersonalWord(language, it) in confirmed } == true

    /** A manual-suggestion sorting hint only; rejection always dominates any accepted count. */
    @Synchronized fun preference(original: String, replacement: String, language: KeyboardLanguage): Int {
        val entry = feedbackKey(original, replacement, language)?.let(feedback::get) ?: return 0
        return if (entry.rejected) -MAX_COUNT else entry.accepted
    }

    /**
     * Caller supplies only acknowledged, learning-eligible text from the current message.
     * Boundaries in prefix discard all preceding context; punctuation in a continuation is rejected.
     * Repeated raw observations never enter [confirmed] or [feedback].
     */
    @Synchronized fun recordPhrase(prefix: String, continuation: String, language: KeyboardLanguage) {
        val context = contextWords(prefix)
        val targets = phraseWords(continuation) ?: return
        if (context.isEmpty() || !(context + targets).all { validSpelling(it, language) }) return
        for (width in 1..context.size) {
            val before = context.takeLast(width).joinToString(" ")
            addPhrase(PersonalPhrase(language, before, targets.joinToString(" "), 1), accumulate = true)
        }
    }

    @Synchronized fun suggestions(context: String, language: KeyboardLanguage): List<PersonalPhraseSuggestion> {
        val words = contextWords(context)
        if (words.isEmpty()) return emptyList()
        val prefixes = (1..words.size).map { words.takeLast(it).joinToString(" ") }
        return phrases.values.asSequence()
            .filter { it.language == language && it.prefix in prefixes && it.support >= MIN_PHRASE_SUPPORT }
            .filter { (it.prefix.split(' ') + it.continuation.split(' ')).all { word -> validSpelling(word, language) } }
            .sortedWith(compareByDescending<PersonalPhrase> { it.prefix.count { char -> char == ' ' } }
                .thenByDescending { it.support }.thenBy { it.continuation })
            .distinctBy { it.continuation }.take(MAX_SUGGESTIONS)
            .map { PersonalPhraseSuggestion(it.continuation, it.support) }.toList()
    }

    @Synchronized fun snapshot(): PersonalTypingSnapshot =
        PersonalTypingSnapshot(feedback.values.toList(), confirmed.toList(), phrases.values.toList())

    /** All-or-nothing validation; persisted explicit confirmations may validate local phrase words. */
    @Synchronized fun restore(snapshot: PersonalTypingSnapshot) {
        PersonalTypingCodec.validate(snapshot)
        reset()
        snapshot.confirmed.forEach { confirmed.add(it) }
        snapshot.feedback.forEach { feedback[FeedbackKey(it.language, it.original, it.replacement)] = it }
        // Dictionary assets may still be loading. Keep structurally valid private entries; suggestions
        // recheck spelling at query time so unavailable dictionaries never destroy saved evidence.
        snapshot.phrases.forEach { addPhrase(it, accumulate = false) }
    }

    /** External profiles contain dictionary-validated phrase support only, never spelling approval. */
    @Synchronized fun importPhrases(imported: List<PersonalPhrase>): Int {
        require(imported.size <= MAX_PHRASES) { "Invalid personal profile" }
        imported.forEach { require(PersonalTypingCodec.validPhrase(it) &&
            it.support >= MIN_PHRASE_SUPPORT) { "Invalid personal profile" } }
        var added = 0
        imported.forEach { phrase ->
            if ((phrase.prefix.split(' ') + phrase.continuation.split(' ')).all { dictionaryContains(it, phrase.language) }) {
                if (addPhrase(phrase, accumulate = false)) added++
            }
        }
        return added
    }

    @Synchronized fun reset() { feedback.clear(); confirmed.clear(); phrases.clear() }

    private fun validSpelling(word: String, language: KeyboardLanguage): Boolean =
        PersonalWord(language, word) in confirmed || dictionaryContains(word, language)

    private fun addPhrase(phrase: PersonalPhrase, accumulate: Boolean): Boolean {
        val key = PhraseKey(phrase.language, phrase.prefix, phrase.continuation)
        val old = phrases[key]
        if (old == null && phrases.size >= MAX_PHRASES) return false
        val count = if (accumulate) (old?.support ?: 0) + phrase.support else maxOf(old?.support ?: 0, phrase.support)
        phrases[key] = phrase.copy(support = count.coerceAtMost(MAX_COUNT))
        return true
    }

    private fun feedbackKey(original: String, replacement: String, language: KeyboardLanguage): FeedbackKey? {
        val from = normalizeWord(original) ?: return null
        val to = normalizeWord(replacement) ?: return null
        return if (from == to) null else FeedbackKey(language, from, to)
    }

    private data class FeedbackKey(val language: KeyboardLanguage, val original: String, val replacement: String)
    private data class PhraseKey(val language: KeyboardLanguage, val prefix: String, val continuation: String)

    companion object {
        const val MAX_FEEDBACK = 512
        const val MAX_CONFIRMED = 512
        const val MAX_PHRASES = 1024
        const val MAX_COUNT = 255
        const val MAX_WORD_CHARS = 48
        const val MAX_CONTEXT_CHARS = 512
        const val MAX_SUGGESTIONS = 3
        const val MIN_PHRASE_SUPPORT = 3

        internal fun normalizeWord(value: String): String? {
            if (value.isEmpty() || value.length > MAX_WORD_CHARS) return null
            val word = Normalizer.normalize(value, Normalizer.Form.NFC).lowercase(Locale.ROOT)
            return word.takeIf { it.length <= MAX_WORD_CHARS && it.all(Char::isLetter) }
        }

        internal fun phraseWords(value: String): List<String>? {
            if (value.length > MAX_WORD_CHARS * 2 + 1) return null
            val words = value.split(' ')
            if (words.size !in 1..2) return null
            return words.map { normalizeWord(it) ?: return null }
        }

        internal fun contextWords(value: String): List<String> {
            if (value.length > MAX_CONTEXT_CHARS) return emptyList()
            // Every punctuation/symbol/control/digit is a boundary, including newline/message separators.
            val boundary = value.indexOfLast { !it.isLetter() && it != ' ' }
            val tail = value.substring(boundary + 1).trim(' ')
            if (tail.isEmpty()) return emptyList()
            return tail.split(' ').filter(String::isNotEmpty).takeLast(2).map {
                normalizeWord(it) ?: return emptyList()
            }
        }
    }
}

data class PersonalFeedback(val language: KeyboardLanguage, val original: String, val replacement: String,
    val accepted: Int, val rejected: Boolean) {
    override fun toString() = "PersonalFeedback(accepted=$accepted, rejected=$rejected)"
}
data class PersonalWord(val language: KeyboardLanguage, val word: String) {
    override fun toString() = "PersonalWord(language=$language)"
}
data class PersonalPhrase(val language: KeyboardLanguage, val prefix: String, val continuation: String, val support: Int) {
    override fun toString() = "PersonalPhrase(language=$language, support=$support)"
}
data class PersonalPhraseSuggestion(val text: String, val support: Int) {
    override fun toString() = "PersonalPhraseSuggestion(support=$support)"
}
data class PersonalTypingSnapshot(val feedback: List<PersonalFeedback> = emptyList(),
    val confirmed: List<PersonalWord> = emptyList(), val phrases: List<PersonalPhrase> = emptyList()) {
    override fun toString() = "PersonalTypingSnapshot(feedback=${feedback.size}, confirmed=${confirmed.size}, phrases=${phrases.size})"
}
