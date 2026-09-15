package io.github.mesteriis.rune.keyboard.smarttyping.touch

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.session.ExperimentalTypingInput

/** Session-owned bounded cache. It cannot acquire text or change the editor itself. */
class DynamicTouchContext {
    private class Stamp(val session: Long, val revision: Long, val language: KeyboardLanguage,
        val context: String, val word: String, val apply: Boolean) {
        fun matches(other: Stamp) = session == other.session && revision == other.revision &&
            language == other.language && context == other.context && word == other.word && apply == other.apply
        override fun toString() = "DynamicTouchStamp(redacted)"
    }
    private var stamp: Stamp? = null
    private var generation = 0L
    private var lastSession: Long? = null
    private var suppressed = false
    private var cached: Map<Char, Double>? = null
    val applies: Boolean get() = stamp?.apply == true

    fun reset() { invalidate(); suppressed = false; lastSession = null }
    fun afterDelete() { invalidate(); suppressed = true }
    fun afterBoundary() { invalidate(); suppressed = false }
    fun invalidate() { stamp = null; cached = null; generation++ }

    fun update(session: Long, revision: Long, language: KeyboardLanguage,
        input: ExperimentalTypingInput?, enabled: Boolean, apply: Boolean): Long {
        if (lastSession != session) { reset(); lastSession = session }
        if (!enabled || suppressed || language != KeyboardLanguage.RUSSIAN || input == null ||
            input.word.isEmpty() || input.word.length > 48 || input.context.length > 128) {
            if (stamp != null) invalidate()
            return 0L
        }
        val next = Stamp(session, revision, language, input.context, input.word, apply)
        if (stamp?.matches(next) != true) {
            invalidate()
            stamp = next
        }
        return generation
    }

    fun probabilities(predict: (String, String, KeyboardLanguage) -> Map<Char, Double>): Map<Char, Double> {
        val current = stamp ?: return emptyMap()
        cached?.let { return it }
        val values = predict(current.context, current.word, current.language)
        // Bound and copy once: neither a malformed model nor a mutable map may influence later taps.
        val safe = if (values.size in 1..33 && values.all { (key, _) ->
                key in 'а'..'я' || key == 'ё'
            } && values.values.all { it.isFinite() && it in 0.0..1.0 }) values.toMap() else emptyMap()
        cached = safe
        return safe
    }
}
