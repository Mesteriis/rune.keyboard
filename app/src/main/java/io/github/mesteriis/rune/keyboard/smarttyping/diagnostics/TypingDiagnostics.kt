package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

/** Observer vocabulary only. Persistence, serialization, consent and UI exist only in debug. */
enum class DiagnosticKind { SESSION, INPUT, BACKSPACE, CANDIDATES, RANKING, BOUNDARY, MANUAL, UNDO, EDITOR, REQUEST, MECHANICAL }
enum class DiagnosticSource { NONE, LOCAL_POLICY, MODEL, CANONICAL_CASE, MECHANICAL, CONTEXTUAL }
enum class DiagnosticCompletion {
    NONE, COMPLETE, PROTECTED, VALID_WORD, STATES_EXHAUSTED, VERIFIED_EXHAUSTED,
    CANCELLED, UNAVAILABLE, READER_FAILURE,
}
enum class DiagnosticReason {
    START, NONE, ACCEPTED, STALE, INVALID, MODEL_ERROR, ABSTAINED,
    INELIGIBLE, PROTECTED_FORM, NO_CANDIDATES, NO_RANKING, POLICY_REJECTED,
    OWNERSHIP_REJECTED, LIMIT, AUTO_REPLACE, ORIGINAL, CORRECTION, CONTEXTUAL,
    EDITOR_ACCEPTED, EDITOR_REJECTED,
    SCHEDULED, SUBMITTED, CANCELLED, RESULT_NOT_READY, SERVICE_REFUSED,
    VALID_WORD, SCORING_FAILED,
}
data class DiagnosticEvent(
    val kind: DiagnosticKind,
    val reason: DiagnosticReason,
    val session: Long,
    val revision: Long,
    val candidateCount: Int = 0,
    val selectedIndex: Int = -1,
    val modelUsed: Boolean = false,
    val completion: DiagnosticCompletion = DiagnosticCompletion.NONE,
    val source: DiagnosticSource = DiagnosticSource.NONE,
    val scoringCode: Int = -1,
    val elapsedMs: Long = 0,
    val requestId: Long = 0,
    val operationId: Long = 0,
    val localCompletion: DiagnosticCompletion = DiagnosticCompletion.NONE,
    val localInspectedStates: Int = 0,
    val localVerifiedTerminals: Int = 0,
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
    /** Optional one-shot, content-free refusal callback for this admitted editor operation. */
    fun editorOperation(session: Long, revision: Long): (() -> Unit)? = null
    /** One-shot content-free final response, bound to the admitted attempt and consent. */
    fun editorOutcome(event: DiagnosticEvent): ((Boolean) -> Unit)? = null
}

object NoTypingDiagnostics : TypingDiagnostics {
    override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
    override fun invalidate() = Unit
    override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) = Unit
}
