package io.github.mesteriis.rune.keyboard.smarttyping.correction

import java.text.Normalizer
import java.util.Locale

/** Bounds apply before and after normalization; no truncation of an owned token. */
internal object TokenUnicode {
    const val MAX_CODE_POINTS = 32

    fun bounded(text: String): Boolean {
        if (text.length > MAX_CODE_POINTS * 2) return false
        var offset = 0
        var count = 0
        while (offset < text.length) {
            val first = text[offset]
            if (Character.isLowSurrogate(first)) return false
            if (Character.isHighSurrogate(first) &&
                (offset + 1 == text.length || !Character.isLowSurrogate(text[offset + 1]))) return false
            offset += Character.charCount(text.codePointAt(offset))
            if (++count > MAX_CODE_POINTS) return false
        }
        return true
    }

    fun nfc(text: String): String {
        return requireNotNull(nfcOrNull(text)) { "Token must contain at most 32 valid Unicode code points before and after NFC" }
    }

    fun nfcOrNull(text: String): String? {
        if (!bounded(text)) return null
        val normalized = Normalizer.normalize(text, Normalizer.Form.NFC)
        return if (bounded(normalized)) normalized else null
    }

    fun folded(text: String): String = nfc(nfc(text).lowercase(Locale.ROOT))

    fun isMark(codePoint: Int): Boolean = when (Character.getType(codePoint)) {
        Character.NON_SPACING_MARK.toInt(),
        Character.COMBINING_SPACING_MARK.toInt(),
        Character.ENCLOSING_MARK.toInt(), -> true
        else -> false
    }
}
