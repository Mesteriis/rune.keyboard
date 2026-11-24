package io.github.mesteriis.rune.keyboard.smarttyping.session

/** Per-session Rune-owned prefix window. It never reads the editor or normalizes text. */
internal class ModelPrefixWindow(private val graphemes: GraphemeSegmenter) {
    private var previous = ""
    private var previousRetainedStartUtf16 = 0L
    private var start = 0

    fun clear() {
        previous = ""
        previousRetainedStartUtf16 = 0L
        start = 0
    }

    /** The final ASCII separator is outside the 256-byte corpus prefix budget. */
    fun bound(prefix: String, retainedStartUtf16: Long = 0L): String? {
        val separator = if (prefix.endsWith(' ')) " " else ""
        val body = if (separator.isEmpty()) prefix else prefix.dropLast(1)
        if (body.isBlank() || !wellFormed(body)) {
            clear()
            return null
        }
        val dropped = retainedStartUtf16 - previousRetainedStartUtf16
        val shift = if (dropped in 0L..start.toLong()) dropped.toInt() else null
        // A capped context may lose its head while the scored suffix still extends unchanged.
        start = if (shift != null && body.regionMatches(0, previous, shift, previous.length - shift)) {
            start - shift
        } else {
            0
        }
        val candidate = body.substring(start)
        if (bytes(candidate) > MAX_BYTES) {
            val boundaries = graphemes.boundaries(body).toHashSet()
            val suffixBytes = IntArray(body.length + 1)
            var index = body.length
            while (index > 0) {
                val codePoint = body.codePointBefore(index)
                val width = Character.charCount(codePoint)
                val encoded = when {
                    codePoint <= 0x7f -> 1
                    codePoint <= 0x7ff -> 2
                    codePoint <= 0xffff -> 3
                    else -> 4
                }
                suffixBytes[index - width] = suffixBytes[index] + encoded
                index -= width
            }
            fun choose(limit: Int): Int? = (1 until body.length).firstOrNull { offset ->
                offset in boundaries && Character.isWhitespace(body.codePointBefore(offset)) &&
                    suffixBytes[offset] <= limit && body.substring(offset).isNotBlank()
            }
            start = choose(TARGET_BYTES) ?: choose(MAX_BYTES) ?: run {
                clear()
                return null
            }
        }
        previous = body
        previousRetainedStartUtf16 = retainedStartUtf16
        return body.substring(start) + separator
    }

    private fun bytes(value: String): Int = value.toByteArray(Charsets.UTF_8).size

    private fun wellFormed(value: String): Boolean {
        var index = 0
        while (index < value.length) {
            val char = value[index]
            if (Character.isHighSurrogate(char)) {
                if (index + 1 >= value.length || !Character.isLowSurrogate(value[index + 1])) return false
                index += 2
            } else {
                if (Character.isLowSurrogate(char)) return false
                index++
            }
        }
        return true
    }

    companion object {
        const val MAX_BYTES = 256
        const val TARGET_BYTES = 160
    }
}
