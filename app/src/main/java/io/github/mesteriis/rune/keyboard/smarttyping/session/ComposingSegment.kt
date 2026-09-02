package io.github.mesteriis.rune.keyboard.smarttyping.session

/** The boundary remains inside the owned span so later punctuation need not read old text. */
data class ComposingSegment(
    val leadingBoundary: String = "",
    val typedWord: String = "",
) {
    val text: String get() = leadingBoundary + typedWord

    override fun toString(): String = "ComposingSegment(redacted)"
}
