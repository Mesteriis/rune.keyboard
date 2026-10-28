package io.github.mesteriis.rune.keyboard.smarttyping.quality

/** Only acknowledged editor actions belong here. Automatic application is not a correctness label. */
enum class QualityEvent {
    AUTOMATIC_APPLIED, EXPLICIT_UNDO, CORRECTION_PICKED, KEPT_ORIGINAL,
    WORD_BOUNDARY_PICKED, ABBREVIATION_PICKED, PHRASE_REVIEW_PICKED, MANUAL_RETYPE,
}

/** Fixed persisted dimensions of RUNE_QUALITY_3; changing their order requires a codec migration. */
enum class AutomaticQualitySource {
    COMMON_CONFUSION, GENERAL_LOCAL, COMPACT_PUBLIC, NEIGHBOR_RECOVERY,
    JOINT_SHORT, JOINT_LONG, JOINT_RESCUE, WORD_CONTEXT, CONTEXTUAL_RANKER,
    INFINITIVE_REVISION, NOUN_CASE_REVISION, MODEL, CONTEXTUAL, CANONICAL_CASE,
}

enum class AutomaticQualityOutcome { APPLIED, EXPLICIT_UNDO, KEPT_ORIGINAL, WINDOW_EXPIRED }

/** Opaque in-memory origin; it never enters a persisted quality snapshot. */
internal class QualityCollectionPeriod

/** A counted application, tied to one recorder/collection period and consumed at most once. */
class AutomaticQualityApplication internal constructor(
    val source: AutomaticQualitySource,
    internal val period: QualityCollectionPeriod,
) {
    internal var consumed = false
    override fun toString(): String = "AutomaticQualityApplication(redacted)"
}

enum class ShadowResult {
    AGREEMENT, DISAGREEMENT, EXPLICIT_PRIMARY, EXPLICIT_EXPERIMENTAL, EXPLICIT_BOTH, EXPLICIT_NEITHER,
}

/** No Android dependencies. Callers must supply current ownership revisions and privacy admission. */
interface QualityRecorder {
    fun configure(metricsEnabled: Boolean, shadowEnabled: Boolean, eligible: Boolean) = Unit
    fun record(event: QualityEvent) = Unit
    /** Numeric source accounting only; callers retain all admission and editor ownership checks. */
    fun recordAutomatic(source: AutomaticQualitySource, outcome: AutomaticQualityOutcome) = Unit
    fun recordAutomaticApplication(source: AutomaticQualitySource): AutomaticQualityApplication? = null
    fun recordAutomaticUndo(application: AutomaticQualityApplication) = Unit
    /** Engine-reported response time, separate from candidate request latency. */
    fun modelResponseMillis(durationMillis: Long) = Unit
    /** Candidate computation/response time, never advertised as end-to-end keystroke latency. */
    fun candidateResponseNanos(durationNanos: Long) = Unit
    /** Refresh an unlabelled decision at the same revision; count each decision once. */
    fun compare(revision: Long, source: String, primaryChoice: String, experimentalChoice: String) = Unit
    /** Only call after an explicit, acknowledged choice or undo, never from lack of an undo. */
    fun explicitChoice(revision: Long, chosen: String) = Unit
    fun invalidatePending() = Unit
}

object NoQualityRecorder : QualityRecorder
