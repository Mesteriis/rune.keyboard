package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

/** Observer vocabulary only. Persistence, serialization, consent and UI exist only in debug. */
enum class DiagnosticKind { SESSION, INPUT, CANDIDATES, RANKING, BOUNDARY, MANUAL, UNDO, EDITOR }
enum class DiagnosticReason {
    START, NONE, ACCEPTED, STALE, INVALID, MODEL_ERROR, ABSTAINED,
    INELIGIBLE, PROTECTED_FORM, NO_CANDIDATES, NO_RANKING, POLICY_REJECTED,
    OWNERSHIP_REJECTED, LIMIT, AUTO_REPLACE, ORIGINAL, CORRECTION, CONTEXTUAL,
    EDITOR_ACCEPTED, EDITOR_REJECTED,
}
data class DiagnosticEvent(
    val kind: DiagnosticKind,
    val reason: DiagnosticReason,
    val session: Long,
    val revision: Long,
    val candidateCount: Int = 0,
    val selectedIndex: Int = -1,
    val modelUsed: Boolean = false,
)

/** Constructed only inside an admitted lazy callback; no editor read or arbitrary metadata. */
data class DiagnosticText(
    val input: String = "",
    val context: String = "",
    val original: String = "",
    val candidates: List<String> = emptyList(),
    val result: String = "",
)

interface TypingDiagnostics {
    fun startSession(session: Long, eligible: Boolean, fresh: Boolean)
    fun invalidate()
    fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)? = null)
}

object NoTypingDiagnostics : TypingDiagnostics {
    override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
    override fun invalidate() = Unit
    override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) = Unit
}
