package io.github.mesteriis.rune.keyboard.smarttyping.ui

/** Display data only. Selection sends an opaque ID back to the session owner, never raw text. */
sealed interface CandidateUiItem {
    val id: String
    val text: String

    data class Original(override val id: String, override val text: String) : CandidateUiItem {
        init { validateCandidate(id, text) }
        override fun toString(): String = "Original(redacted)"
    }

    data class Correction(override val id: String, override val text: String) : CandidateUiItem {
        init { validateCandidate(id, text) }
        override fun toString(): String = "Correction(redacted)"
    }

    data class Punctuation(override val id: String, override val text: String) : CandidateUiItem {
        init { validateCandidate(id, text) }
        override fun toString(): String = "Punctuation(redacted)"
    }

    data class Continuation(override val id: String, override val text: String) : CandidateUiItem {
        init { validateCandidate(id, text) }
        override fun toString(): String = "Continuation(redacted)"
    }

    data class Tool(override val id: String, override val text: String,
        val kind: io.github.mesteriis.rune.keyboard.smarttyping.session.TypingToolKind) : CandidateUiItem {
        init { validateCandidate(id, text) }
        override fun toString() = "Tool(kind=$kind, redacted)"
    }
    data class Undo(override val id: String, override val text: String) : CandidateUiItem {
        init { validateCandidate(id, text) }
        override fun toString() = "Undo(redacted)"
    }

    companion object {
        const val MAX_ID_LENGTH = 96
        const val MAX_TEXT_UTF16 = 256
    }
}

private fun validateCandidate(id: String, text: String) {
    require(id.isNotBlank() && id.length <= CandidateUiItem.MAX_ID_LENGTH) {
        "Candidate ID must be nonblank and bounded"
    }
    require(text.isNotBlank() && text.length <= CandidateUiItem.MAX_TEXT_UTF16) {
        "Candidate text must be nonblank and bounded"
    }
}
