package io.github.mesteriis.rune.keyboard.ime.editor

import android.icu.text.BreakIterator
import android.view.inputmethod.InputConnection
import java.util.Locale

/** Bounded grapheme lookup used only during a non-sensitive Backspace command. */
internal object GraphemeDeletion {
    private const val MAX_UTF16_UNITS = 64
    private const val ZERO_WIDTH_JOINER = 0x200D

    fun deletePrevious(inputConnection: InputConnection): Boolean {
        val beforeCursor = inputConnection.getTextBeforeCursor(MAX_UTF16_UNITS, 0)
            ?.toString()
            .orEmpty()
        if (beforeCursor.isEmpty()) return false

        val start = previousBoundary(beforeCursor)
        val codePointCount = beforeCursor.codePointCount(start, beforeCursor.length)
        return codePointCount > 0 &&
            inputConnection.deleteSurroundingTextInCodePoints(codePointCount, 0)
    }

    internal fun previousBoundary(text: String): Int {
        require(text.isNotEmpty())
        val iterator = BreakIterator.getCharacterInstance(Locale.ROOT).apply { setText(text) }
        val icuBoundary = iterator.preceding(text.length).takeIf { it != BreakIterator.DONE }
            ?: previousCodePointStart(text, text.length)
        return minOf(icuBoundary, compatibilityBoundary(text))
    }

    /**
     * Older ICU releases may split emoji ZWJ sequences, modifiers, flags, keycaps, or combining
     * marks. This backwards-only scan covers those cases without widening the 64-unit read.
     */
    private fun compatibilityBoundary(text: String): Int {
        var start = previousCodePointStart(text, text.length)
        start = includeExtendersAndBase(text, start)

        while (start > 0) {
            val previousStart = previousCodePointStart(text, start)
            if (text.codePointAt(previousStart) != ZERO_WIDTH_JOINER) break
            start = previousStart
            if (start == 0) break
            start = includeExtendersAndBase(text, previousCodePointStart(text, start))
        }

        val last = text.codePointAt(start)
        if (isRegionalIndicator(last) && start > 0) {
            var precedingRegionalIndicators = 0
            var cursor = start
            while (cursor > 0) {
                val previousStart = previousCodePointStart(text, cursor)
                if (!isRegionalIndicator(text.codePointAt(previousStart))) break
                precedingRegionalIndicators++
                cursor = previousStart
            }
            if (precedingRegionalIndicators % 2 == 1) start = previousCodePointStart(text, start)
        }
        return start
    }

    private fun includeExtendersAndBase(text: String, initialStart: Int): Int {
        var start = initialStart
        while (isExtender(text.codePointAt(start)) && start > 0) {
            start = previousCodePointStart(text, start)
        }
        return start
    }

    private fun previousCodePointStart(text: String, end: Int): Int =
        end - Character.charCount(text.codePointBefore(end))

    private fun isExtender(codePoint: Int): Boolean {
        val type = Character.getType(codePoint)
        return type == Character.NON_SPACING_MARK.toInt() ||
            type == Character.COMBINING_SPACING_MARK.toInt() ||
            type == Character.ENCLOSING_MARK.toInt() ||
            codePoint in 0xFE00..0xFE0F ||
            codePoint in 0xE0100..0xE01EF ||
            codePoint in 0x1F3FB..0x1F3FF ||
            codePoint in 0xE0020..0xE007F
    }

    private fun isRegionalIndicator(codePoint: Int): Boolean = codePoint in 0x1F1E6..0x1F1FF
}
