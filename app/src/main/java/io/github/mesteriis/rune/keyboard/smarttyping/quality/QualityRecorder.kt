package io.github.mesteriis.rune.keyboard.smarttyping.quality

/** Only acknowledged editor actions belong here. Automatic application is not a correctness label. */
enum class QualityEvent {
    AUTOMATIC_APPLIED, EXPLICIT_UNDO, CORRECTION_PICKED, KEPT_ORIGINAL,
    WORD_BOUNDARY_PICKED, ABBREVIATION_PICKED, PHRASE_REVIEW_PICKED,
}

enum class ShadowResult {
    AGREEMENT, DISAGREEMENT, EXPLICIT_PRIMARY, EXPLICIT_EXPERIMENTAL, EXPLICIT_BOTH, EXPLICIT_NEITHER,
}

/** No Android dependencies. Callers must supply current ownership revisions and privacy admission. */
interface QualityRecorder {
    fun configure(metricsEnabled: Boolean, shadowEnabled: Boolean, eligible: Boolean) = Unit
    fun record(event: QualityEvent) = Unit
    /** Candidate computation/response time, never advertised as end-to-end keystroke latency. */
    fun candidateResponseNanos(durationNanos: Long) = Unit
    /** Refresh an unlabelled decision at the same revision; count each decision once. */
    fun compare(revision: Long, source: String, primaryChoice: String, experimentalChoice: String) = Unit
    /** Only call after an explicit, acknowledged choice or undo, never from lack of an undo. */
    fun explicitChoice(revision: Long, chosen: String) = Unit
    fun invalidatePending() = Unit
}

object NoQualityRecorder : QualityRecorder
