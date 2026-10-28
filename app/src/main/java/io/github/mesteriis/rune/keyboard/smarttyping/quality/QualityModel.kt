package io.github.mesteriis.rune.keyboard.smarttyping.quality

data class QualitySnapshot(
    val events: List<Long> = List(QualityEvent.entries.size) { 0L },
    val candidateResponseBuckets: List<Long> = List(QualityModel.LATENCY_BUCKET_COUNT) { 0L },
    val shadow: List<Long> = List(ShadowResult.entries.size) { 0L },
    val automaticSources: List<Long> = List(QualityModel.SOURCE_COUNTER_COUNT) { 0L },
    val modelResponseBuckets: List<Long> = List(QualityModel.MODEL_RESPONSE_BUCKET_COUNT) { 0L },
) {
    init {
        require(events.size == QualityEvent.entries.size)
        require(candidateResponseBuckets.size == QualityModel.LATENCY_BUCKET_COUNT)
        require(shadow.size == ShadowResult.entries.size)
        require(automaticSources.size == QualityModel.SOURCE_COUNTER_COUNT)
        require(modelResponseBuckets.size == QualityModel.MODEL_RESPONSE_BUCKET_COUNT)
        require((events + candidateResponseBuckets + shadow + automaticSources + modelResponseBuckets)
            .all { it in 0..QualityModel.MAX_COUNT })
    }

    operator fun get(event: QualityEvent): Long = events[event.ordinal]
    operator fun get(result: ShadowResult): Long = shadow[result.ordinal]
    operator fun get(source: AutomaticQualitySource, outcome: AutomaticQualityOutcome): Long =
        automaticSources[source.ordinal * AutomaticQualityOutcome.entries.size + outcome.ordinal]

    /** Observed explicit undo fraction since reset, never a correctness label or admission grant. */
    fun explicitUndoFraction(source: AutomaticQualitySource): Double? {
        val applied = this[source, AutomaticQualityOutcome.APPLIED]
        val undone = this[source, AutomaticQualityOutcome.EXPLICIT_UNDO]
        if (applied < QualityModel.MIN_SOURCE_APPLICATIONS || undone > applied) return null
        return undone.toDouble() / applied
    }
}

/** Bounded numeric aggregates and one ephemeral comparison. Its owner serializes access. */
class QualityModel {
    private var metricsEnabled = false
    private var shadowEnabled = false
    private var eligible = false
    private var collectionPeriod = QualityCollectionPeriod()
    private val events = LongArray(QualityEvent.entries.size)
    private val latency = LongArray(LATENCY_BUCKET_COUNT)
    private val shadow = LongArray(ShadowResult.entries.size)
    private val automaticSources = LongArray(SOURCE_COUNTER_COUNT)
    private val modelResponse = LongArray(MODEL_RESPONSE_BUCKET_COUNT)
    private data class Pending(val revision: Long, val source: String, val primary: String, val experimental: String, val counted: Boolean)
    private var pending: Pending? = null
    private var lastComparedRevision: Long? = null

    fun configure(metricsEnabled: Boolean, shadowEnabled: Boolean, eligible: Boolean) {
        if (this.metricsEnabled != metricsEnabled || this.eligible != eligible)
            collectionPeriod = QualityCollectionPeriod()
        if (this.metricsEnabled != metricsEnabled || this.shadowEnabled != shadowEnabled ||
            this.eligible != eligible || !eligible || !shadowEnabled
        ) invalidatePending()
        this.metricsEnabled = metricsEnabled
        this.shadowEnabled = shadowEnabled
        this.eligible = eligible
    }

    fun record(event: QualityEvent): Boolean =
        if (metricsEnabled && eligible) increment(events, event.ordinal) else false

    fun recordAutomatic(source: AutomaticQualitySource, outcome: AutomaticQualityOutcome): Boolean =
        if (metricsEnabled && eligible)
            increment(automaticSources, source.ordinal * AutomaticQualityOutcome.entries.size + outcome.ordinal)
        else false

    fun recordAutomaticApplication(source: AutomaticQualitySource): AutomaticQualityApplication? =
        if (recordAutomatic(source, AutomaticQualityOutcome.APPLIED)) AutomaticQualityApplication(source, collectionPeriod)
        else null

    fun recordAutomaticUndo(application: AutomaticQualityApplication): Boolean {
        if (application.period !== collectionPeriod || application.consumed) return false
        application.consumed = true
        return recordAutomatic(application.source, AutomaticQualityOutcome.EXPLICIT_UNDO)
    }

    fun modelResponseMillis(durationMillis: Long): Boolean {
        if (!metricsEnabled || !eligible || durationMillis < 0L) return false
        val bucket = MODEL_RESPONSE_UPPER_MILLIS.indexOfFirst { durationMillis < it }
            .let { if (it < 0) MODEL_RESPONSE_BUCKET_COUNT - 1 else it }
        return increment(modelResponse, bucket)
    }

    fun candidateResponseNanos(durationNanos: Long): Boolean {
        if (!metricsEnabled || !eligible || durationNanos < 0L) return false
        val bucket = LATENCY_UPPER_NANOS.indexOfFirst { durationNanos < it }
            .let { if (it < 0) LATENCY_BUCKET_COUNT - 1 else it }
        return increment(latency, bucket)
    }

    fun compare(revision: Long, source: String, primaryChoice: String, experimentalChoice: String): Boolean {
        val previous = pending
        if (lastComparedRevision == revision && previous?.revision != revision) return false
        pending = null
        if (!shadowEnabled || !eligible || revision < 0L ||
            listOf(source, primaryChoice, experimentalChoice).any { it.isEmpty() || it.length > MAX_TEXT_LENGTH }
        ) return false
        val result = if (primaryChoice == experimentalChoice) ShadowResult.AGREEMENT else ShadowResult.DISAGREEMENT
        if (previous?.revision == revision) {
            if (previous.source != source) return false
            val oldResult = if (previous.primary == previous.experimental) ShadowResult.AGREEMENT else ShadowResult.DISAGREEMENT
            if (oldResult == result) {
                pending = Pending(revision, source, primaryChoice, experimentalChoice, previous.counted)
                return false
            }
            if (previous.counted) shadow[oldResult.ordinal]--
        }
        val counted = increment(shadow, result.ordinal)
        pending = Pending(revision, source, primaryChoice, experimentalChoice, counted)
        lastComparedRevision = revision
        return counted || previous?.let { it.revision == revision && it.counted } == true
    }

    fun explicitChoice(revision: Long, chosen: String): Boolean {
        val comparison = pending ?: return false
        pending = null
        if (!shadowEnabled || !eligible || revision != comparison.revision || chosen.length > MAX_TEXT_LENGTH) return false
        val primary = chosen == comparison.primary
        val experimental = chosen == comparison.experimental
        val result = when {
            primary && experimental -> ShadowResult.EXPLICIT_BOTH
            primary -> ShadowResult.EXPLICIT_PRIMARY
            experimental -> ShadowResult.EXPLICIT_EXPERIMENTAL
            else -> ShadowResult.EXPLICIT_NEITHER
        }
        return increment(shadow, result.ordinal)
    }

    fun invalidatePending() { pending = null }

    fun snapshot() = QualitySnapshot(events.toList(), latency.toList(), shadow.toList(),
        automaticSources.toList(), modelResponse.toList())

    fun restore(snapshot: QualitySnapshot) {
        collectionPeriod = QualityCollectionPeriod()
        snapshot.events.toLongArray().copyInto(events)
        snapshot.candidateResponseBuckets.toLongArray().copyInto(latency)
        snapshot.shadow.toLongArray().copyInto(shadow)
        snapshot.automaticSources.toLongArray().copyInto(automaticSources)
        snapshot.modelResponseBuckets.toLongArray().copyInto(modelResponse)
        invalidatePending()
    }

    fun reset() = restore(QualitySnapshot())

    private fun increment(values: LongArray, index: Int): Boolean {
        if (values[index] >= MAX_COUNT) return false
        values[index]++
        return true
    }

    companion object {
        const val MAX_COUNT = 1_000_000_000_000L
        const val MAX_TEXT_LENGTH = 128
        const val LATENCY_BUCKET_COUNT = 6
        const val MODEL_RESPONSE_BUCKET_COUNT = 5
        const val MIN_SOURCE_APPLICATIONS = 100L
        val SOURCE_COUNTER_COUNT = AutomaticQualitySource.entries.size * AutomaticQualityOutcome.entries.size
        private val MODEL_RESPONSE_UPPER_MILLIS = longArrayOf(50, 100, 250, 500)
        // <5ms, 5–<10ms, 10–<25ms, 25–<50ms, 50–<100ms, >=100ms.
        private val LATENCY_UPPER_NANOS = longArrayOf(5_000_000, 10_000_000, 25_000_000, 50_000_000, 100_000_000)
    }
}

/** A strict, fixed-size numeric schema; no arbitrary keys or text-bearing fields. */
object QualityCodec {
    const val MAX_BYTES = 2048
    private const val HEADER = "RUNE_QUALITY_3"
    private const val V2_HEADER = "RUNE_QUALITY_2"
    private const val LEGACY_HEADER = "RUNE_QUALITY_1"
    private const val LEGACY_EVENT_COUNT = 7
    private const val V2_EVENT_COUNT = 8

    fun encode(snapshot: QualitySnapshot): ByteArray =
        (HEADER + "\n" + (snapshot.events + snapshot.candidateResponseBuckets + snapshot.shadow +
            snapshot.automaticSources + snapshot.modelResponseBuckets).joinToString("\n") + "\n")
            .toByteArray(Charsets.US_ASCII)

    fun decode(bytes: ByteArray): QualitySnapshot {
        require(bytes.size <= MAX_BYTES)
        val lines = bytes.toString(Charsets.US_ASCII).split('\n')
        val current = lines.firstOrNull() == HEADER
        val eventCount = when (lines.firstOrNull()) {
            HEADER -> QualityEvent.entries.size
            V2_HEADER -> V2_EVENT_COUNT
            LEGACY_HEADER -> LEGACY_EVENT_COUNT
            else -> throw IllegalArgumentException("QUALITY_HEADER")
        }
        require(eventCount <= QualityEvent.entries.size)
        val count = eventCount + QualityModel.LATENCY_BUCKET_COUNT + ShadowResult.entries.size +
            if (current) QualityModel.SOURCE_COUNTER_COUNT + QualityModel.MODEL_RESPONSE_BUCKET_COUNT else 0
        require(lines.size == count + 2 && lines.last().isEmpty())
        val values = lines.drop(1).dropLast(1).map { line ->
            require(line.isNotEmpty() && line.length <= 13 && line.all { it in '0'..'9' })
            requireNotNull(line.toLongOrNull()).also { require(it <= QualityModel.MAX_COUNT) }
        }
        val eventsEnd = eventCount
        val latencyEnd = eventsEnd + QualityModel.LATENCY_BUCKET_COUNT
        val events = values.take(eventsEnd) + List(QualityEvent.entries.size - eventCount) { 0L }
        val shadowEnd = latencyEnd + ShadowResult.entries.size
        val shadow = values.subList(latencyEnd, shadowEnd)
        if (!current) return QualitySnapshot(events, values.subList(eventsEnd, latencyEnd), shadow)
        val sourcesEnd = shadowEnd + QualityModel.SOURCE_COUNTER_COUNT
        return QualitySnapshot(events, values.subList(eventsEnd, latencyEnd), shadow,
            values.subList(shadowEnd, sourcesEnd), values.drop(sourcesEnd))
    }
}
