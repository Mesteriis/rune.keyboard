package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.icu.text.BreakIterator
import java.util.Locale

/** Returns UTF-16 boundaries, including zero and the end, using a Unicode grapheme segmenter. */
internal fun interface GraphemeSegmenter {
    fun boundaries(text: String): List<Int>
}

internal object IcuGraphemeSegmenter : GraphemeSegmenter {
    override fun boundaries(text: String): List<Int> {
        val iterator = BreakIterator.getCharacterInstance(Locale.ROOT).apply { setText(text) }
        return buildList {
            var boundary = iterator.first()
            while (boundary != BreakIterator.DONE) {
                add(boundary)
                boundary = iterator.next()
            }
        }
    }
}

/** RAM-only text accepted from Rune commands. Never populated from editor reads. */
internal class SessionTextContext(
    private val graphemes: GraphemeSegmenter,
    private val maxUtf16: Int = 2_048,
    private val maxCodePoints: Int = 1_024,
) {
    var text: String = ""
        private set

    init {
        require(maxUtf16 > 0 && maxCodePoints > 0)
    }

    fun append(value: String) {
        val combined = text + value
        val codePoints = combined.codePointCount(0, combined.length)
        val minimumStart = maxOf(
            (combined.length - maxUtf16).coerceAtLeast(0),
            if (codePoints > maxCodePoints) {
                combined.offsetByCodePoints(0, codePoints - maxCodePoints)
            } else {
                0
            },
        )
        val start = if (minimumStart == 0) 0 else {
            graphemes.boundaries(combined).first { it >= minimumStart }
        }
        text = combined.substring(start)
    }

    fun removeLastGrapheme() {
        if (text.isEmpty()) return
        text = text.substring(0, graphemes.boundaries(text).dropLast(1).last())
    }

    fun clear() {
        text = ""
    }

    override fun toString(): String = "SessionTextContext(redacted)"
}
