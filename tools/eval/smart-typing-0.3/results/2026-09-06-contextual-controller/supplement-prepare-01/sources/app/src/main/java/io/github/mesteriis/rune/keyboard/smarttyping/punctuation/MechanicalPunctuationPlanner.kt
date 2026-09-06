package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.ime.editor.DoubleSpacePeriod
import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy

/** Stateless, bounded rule proposals. No InputConnection, model, normalization or editor reads. */
object MechanicalPunctuationPlanner {
    fun plan(
        owned: OwnedPunctuationSuffix,
        action: PunctuationAction,
        policy: MechanicalPunctuationPolicy,
    ): MechanicalPunctuationPlan {
        if (policy.inputPolicy != InputPolicy.NORMAL) return keep(UnchangedPunctuationReason.INPUT_POLICY)
        if (policy.mode != EditorMode.TEXT) return keep(UnchangedPunctuationReason.NON_TEXT_MODE)
        if (policy.requiresRawKeyEvents) return keep(UnchangedPunctuationReason.RAW_EDITOR)
        if (action == PunctuationAction.Send) return keep(UnchangedPunctuationReason.SEND)
        if (action == PunctuationAction.Other) return keep(UnchangedPunctuationReason.NON_TEXT_ACTION)
        val incoming = if (action is PunctuationAction.Text) action.value else " "
        if (!bounded(owned.text, 256) || !bounded(incoming, 32) ||
            owned.composingText?.let { !bounded(it, 128) || it.length > 256 } == true ||
            owned.sessionId <= 0 || owned.revision < 0
        ) return keep(UnchangedPunctuationReason.INVALID_BOUNDS)
        val composing = owned.composingText.orEmpty()
        if (!owned.text.endsWith(composing)) return keep(UnchangedPunctuationReason.OWNERSHIP_MISMATCH)
        if (protectedLine(owned.text + incoming)) return keep(UnchangedPunctuationReason.PROTECTED_TOKEN)

        // Gesture priority is independent of the mechanical cleanup toggle, as in the reducer.
        if (action == PunctuationAction.DoubleSpaceGesture && policy.doubleSpaceEnabled) {
            if (!DoubleSpacePeriod.canConvert(owned.text)) return keep(UnchangedPunctuationReason.DOUBLE_SPACE_INELIGIBLE)
            val word = wordEnding(owned.text, owned.text.length - 1)
                ?: return keep(UnchangedPunctuationReason.DOUBLE_SPACE_INELIGIBLE)
            ordinaryFailure(owned, owned.text, word)?.let { return keep(it) }
            return replace(owned, " ", owned.text.dropLast(1) + ". ", MechanicalEditKind.DOUBLE_SPACE_PERIOD,
                undo = composing)
        }
        if (!policy.enabled) return keep(UnchangedPunctuationReason.DISABLED)
        if (incoming.isEmpty()) return keep(UnchangedPunctuationReason.NO_CHANGE)
        val raw = owned.text + incoming

        if (incoming == " ") {
            val start = skipSpaces(raw, raw.length)
            if (raw.length - start < 2) return keep(UnchangedPunctuationReason.NO_CHANGE)
            val word = wordEnding(raw, start) ?: return keep(UnchangedPunctuationReason.PROTECTED_TOKEN)
            ordinaryFailure(owned, raw, word)?.let { return keep(it) }
            return replace(owned, incoming, raw.substring(0, start) + " ", MechanicalEditKind.REPEATED_SPACE)
        }

        if (incoming.length == 1 && incoming[0] in PUNCTUATION) {
            val punctuation = incoming[0]
            if (owned.text.lastOrNull() == punctuation) {
                // Dots may be ellipsis; colons IPv6; !/?? may be intentional emphasis.
                if (punctuation != ',' && punctuation != ';') return keep(UnchangedPunctuationReason.PROTECTED_PUNCTUATION)
                val word = wordEnding(owned.text, owned.text.length - 1)
                    ?: return keep(UnchangedPunctuationReason.PROTECTED_PUNCTUATION)
                ordinaryFailure(owned, owned.text, word)?.let { return keep(it) }
                return replace(owned, incoming, owned.text, MechanicalEditKind.DUPLICATE_PUNCTUATION)
            }
            val start = skipSpaces(owned.text, owned.text.length)
            if (start == owned.text.length) return keep(UnchangedPunctuationReason.NO_CHANGE)
            val word = wordEnding(owned.text, start) ?: return keep(UnchangedPunctuationReason.PROTECTED_TOKEN)
            ordinaryFailure(owned, owned.text, word)?.let { return keep(it) }
            return replace(owned, incoming, owned.text.substring(0, start) + incoming, MechanicalEditKind.SPACE_BEFORE)
        }

        val right = wordEnding(raw, raw.length) ?: return keep(UnchangedPunctuationReason.UNSUPPORTED_ACTION)
        if (right.start > owned.text.length || !ordinaryWord(incoming)) return keep(UnchangedPunctuationReason.UNSUPPORTED_ACTION)
        if (!ordinaryWord(raw.substring(right.start, right.end))) return keep(UnchangedPunctuationReason.PROTECTED_TOKEN)
        val separator = skipSpaces(raw, right.start)
        val punctuation = raw.getOrNull(separator - 1)
        if (punctuation in PUNCTUATION) {
            // Delay a pair of dots until explicit owned whitespace and a new ordinary word.
            // A third dot, numeric action, hostname-shaped continuation, or old first dot cannot
            // authorize rewriting the pair. replace() still enforces the exact live suffix.
            if (punctuation == '.' && raw.getOrNull(separator - 2) == '.') {
                if (raw.getOrNull(separator - 3) == '.' || right.start == separator ||
                    right.start != owned.text.length
                ) return keep(UnchangedPunctuationReason.PROTECTED_PUNCTUATION)
                if (separator - 2 < owned.text.length - composing.length) {
                    return keep(UnchangedPunctuationReason.OUTSIDE_COMPOSING_SPAN)
                }
                val left = wordEnding(raw, separator - 2)
                    ?: return keep(UnchangedPunctuationReason.PROTECTED_PUNCTUATION)
                ordinaryFailure(owned, raw, left)?.let { return keep(it) }
                val desired = raw.substring(0, separator - 2) + ". " + incoming
                return replace(owned, incoming, desired, MechanicalEditKind.DUPLICATE_PUNCTUATION,
                    capsAt = desired.length - incoming.length)
            }
            val leftEnd = skipSpaces(raw, separator - 1)
            val left = wordEnding(raw, leftEnd) ?: return keep(UnchangedPunctuationReason.PROTECTED_PUNCTUATION)
            ordinaryFailure(owned, raw, left)?.let { return keep(it) }
            val spaceAfter = right.start - separator
            if (punctuation == '.' && spaceAfter == 0) return keep(UnchangedPunctuationReason.AMBIGUOUS_DOT)
            // An ASCII word followed immediately by ':' can still be a URI scheme or IPv6 fragment.
            if (punctuation == ':' && spaceAfter == 0 && raw.substring(left.start, left.end).all { it.code < 128 }) {
                return keep(UnchangedPunctuationReason.AMBIGUOUS_COLON)
            }
            if (spaceAfter == 1 && leftEnd == separator - 1) {
                if (punctuation in SENTENCE_END && right.start == owned.text.length) {
                    // Hint only; the consumer creates a transaction only if rendering changes case.
                    return replace(owned, incoming, raw, MechanicalEditKind.SENTENCE_CASE, capsAt = right.start)
                }
                return keep(UnchangedPunctuationReason.NO_CHANGE)
            }
            val desired = raw.substring(0, leftEnd) + punctuation + " " + raw.substring(right.start)
            val caps = if (punctuation in SENTENCE_END && right.start == owned.text.length) desired.length - incoming.length else null
            return replace(owned, incoming, desired, MechanicalEditKind.SPACE_AFTER, capsAt = caps)
        }
        if (right.start - separator > 1) {
            val left = wordEnding(raw, separator) ?: return keep(UnchangedPunctuationReason.PROTECTED_TOKEN)
            ordinaryFailure(owned, raw, left)?.let { return keep(it) }
            return replace(owned, incoming, raw.substring(0, separator) + " " + raw.substring(right.start), MechanicalEditKind.REPEATED_SPACE)
        }
        return keep(UnchangedPunctuationReason.NO_CHANGE)
    }

    private fun replace(
        owned: OwnedPunctuationSuffix,
        incoming: String,
        desired: String,
        kind: MechanicalEditKind,
        undo: String = owned.composingText.orEmpty() + incoming,
        capsAt: Int? = null,
    ): MechanicalPunctuationPlan {
        val readOnlyLength = owned.text.length - owned.composingText.orEmpty().length
        val readOnly = owned.text.substring(0, readOnlyLength)
        if (!desired.startsWith(readOnly)) return keep(UnchangedPunctuationReason.OUTSIDE_COMPOSING_SPAN)
        val replacement = desired.substring(readOnlyLength)
        // A zero-width suppression needs a different acknowledgement/Undo contract; do not invent one.
        if (replacement.isEmpty()) return keep(UnchangedPunctuationReason.OUTSIDE_COMPOSING_SPAN)
        if (replacement.length > 256 || !bounded(replacement, 128) || undo.length > 256 || !bounded(undo, 128)) {
            return keep(UnchangedPunctuationReason.INVALID_BOUNDS)
        }
        return MechanicalPunctuationPlan.Replace(owned.sessionId, owned.revision, owned.composingText,
            replacement, undo, kind, capsAt?.minus(readOnlyLength))
    }

    private data class Word(val start: Int, val end: Int)

    private fun wordEnding(text: String, end: Int): Word? {
        var start = end
        while (start > 0) {
            val cp = text.codePointBefore(start)
            if (!Character.isLetter(cp) && !isMark(cp)) break
            start -= Character.charCount(cp)
        }
        return if (start < end) Word(start, end) else null
    }

    private fun ordinaryFailure(owned: OwnedPunctuationSuffix, text: String, word: Word): UnchangedPunctuationReason? {
        if (word.start == 0 && !owned.startsAtTokenBoundary) return UnchangedPunctuationReason.TRUNCATED_CONTEXT
        // No detached fragment after a slash, at-sign, digit, dot, bracket, quote or code operator.
        if (word.start > 0 && !text[word.start - 1].isWhitespace()) return UnchangedPunctuationReason.PROTECTED_TOKEN
        return if (ordinaryWord(text.substring(word.start, word.end))) null else UnchangedPunctuationReason.PROTECTED_TOKEN
    }

    private fun ordinaryWord(text: String): Boolean {
        if (text.isEmpty() || !bounded(text, 32)) return false
        var script: Character.UnicodeScript? = null
        var letters = 0
        var uppercase = 0
        var firstUpper = false
        var offset = 0
        while (offset < text.length) {
            val cp = text.codePointAt(offset)
            val current = Character.UnicodeScript.of(cp)
            if (current != Character.UnicodeScript.INHERITED) {
                if (current != Character.UnicodeScript.LATIN && current != Character.UnicodeScript.CYRILLIC) return false
                if (script != null && script != current) return false
                script = current
            }
            if (Character.isLetter(cp)) {
                val upper = Character.isUpperCase(cp) || Character.isTitleCase(cp)
                if (letters == 0) firstUpper = upper
                letters++
                if (upper) uppercase++
            } else if (!isMark(cp) || letters == 0) return false
            offset += Character.charCount(cp)
        }
        return letters > 0 && (uppercase == 0 || uppercase == 1 && (letters == 1 || firstUpper))
    }

    private fun skipSpaces(text: String, end: Int): Int {
        var index = end
        while (index > 0 && text[index - 1] == ' ') index--
        return index
    }

    private fun isMark(cp: Int) = Character.getType(cp) in MARK_TYPES

    private fun protectedLine(text: String): Boolean {
        var offset = text.lastIndexOf('\n') + 1
        // A standalone dot can be a command's current-directory argument or literal output.
        // Keep its separator as soon as the dot is typed, including inside quoted-in-prose
        // command fragments. Waiting for a later slash/flag would already have damaged it.
        if (DOT_ARGUMENT.containsMatchIn(text.substring(offset))) return true
        while (offset < text.length) {
            val cp = text.codePointAt(offset)
            if (!Character.isLetterOrDigit(cp) && !isMark(cp) && cp != ' '.code &&
                (cp > Char.MAX_VALUE.code || cp.toChar() !in PUNCTUATION)) return true
            offset += Character.charCount(cp)
        }
        return false
    }

    private fun bounded(text: String, maxCodePoints: Int): Boolean {
        if (text.length > maxCodePoints * 2) return false
        var offset = 0
        var count = 0
        while (offset < text.length) {
            val char = text[offset]
            if (Character.isLowSurrogate(char) || Character.isHighSurrogate(char) &&
                (offset + 1 == text.length || !Character.isLowSurrogate(text[offset + 1]))) return false
            offset += Character.charCount(text.codePointAt(offset))
            if (++count > maxCodePoints) return false
        }
        return true
    }

    private fun keep(reason: UnchangedPunctuationReason) = MechanicalPunctuationPlan.Unchanged(reason)
    private val PUNCTUATION = setOf(',', '.', '?', '!', ':', ';')
    private val SENTENCE_END = setOf('.', '?', '!')
    private val DOT_ARGUMENT = Regex("(?:^|\\s)(?:cd|cp|mv|rm|ls|du|stat|find|chmod|chown|git|rg|grep|echo|printf) +\\.(?=$|[\\s.])")
    private val MARK_TYPES = setOf(Character.NON_SPACING_MARK.toInt(), Character.COMBINING_SPACING_MARK.toInt(), Character.ENCLOSING_MARK.toInt())
}
