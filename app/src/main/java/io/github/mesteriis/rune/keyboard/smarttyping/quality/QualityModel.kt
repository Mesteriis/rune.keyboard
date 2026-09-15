package io.github.mesteriis.rune.keyboard.smarttyping.quality

data class QualitySnapshot(
    val events: List<Long> = List(QualityEvent.entries.size) { 0L },
    val candidateResponseBuckets: List<Long> = List(QualityModel.LATENCY_BUCKET_COUNT) { 0L },
    val shadow: List<Long> = List(ShadowResult.entries.size) { 0L },
) {
    init {
        require(events.size == QualityEvent.entries.size)
        require(candidateResponseBuckets.size == QualityModel.LATENCY_BUCKET_COUNT)
        require(shadow.size == ShadowResult.entries.size)
        require((events + candidateResponseBuckets + shadow).all { it in 0..QualityModel.MAX_COUNT })
    }

    operator fun get(event: QualityEvent): Long = events[event.ordinal]
    operator fun get(result: ShadowResult): Long = shadow[result.ordinal]
}

/** Bounded numeric aggregates and one ephemeral comparison. Its owner serializes access. */
class QualityModel {
    private var metricsEnabled = false
    private var shadowEnabled = false
    private var eligible = false
    private val events = LongArray(QualityEvent.entries.size)
    private val latency = LongArray(LATENCY_BUCKET_COUNT)
    private val shadow = LongArray(ShadowResult.entries.size)
    private data class Pending(val revision: Long, val source: String, val primary: String, val experimental: String, val counted: Boolean)
    private var pending: Pending? = null
    private var lastComparedRevision: Long? = null

    fun configure(metricsEnabled: Boolean, shadowEnabled: Boolean, eligible: Boolean) {
        if (this.metricsEnabled != metricsEnabled || this.shadowEnabled != shadowEnabled ||
            this.eligible != eligible || !eligible || !shadowEnabled
        ) invalidatePending()
        this.metricsEnabled = metricsEnabled
        this.shadowEnabled = shadowEnabled
        this.eligible = eligible
    }

    fun record(event: QualityEvent): Boolean =
        if (metricsEnabled && eligible) increment(events, event.ordinal) else false

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

    fun snapshot() = QualitySnapshot(events.toList(), latency.toList(), shadow.toList())

    fun restore(snapshot: QualitySnapshot) {
        snapshot.events.toLongArray().copyInto(events)
        snapshot.candidateResponseBuckets.toLongArray().copyInto(latency)
        snapshot.shadow.toLongArray().copyInto(shadow)
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
        // <5ms, 5–<10ms, 10–<25ms, 25–<50ms, 50–<100ms, >=100ms.
        private val LATENCY_UPPER_NANOS = longArrayOf(5_000_000, 10_000_000, 25_000_000, 50_000_000, 100_000_000)
    }
}

/** A strict, fixed-size numeric schema; no arbitrary keys or text-bearing fields. */
object QualityCodec {
    const val MAX_BYTES = 1024
    private const val HEADER = "RUNE_QUALITY_1"

    fun encode(snapshot: QualitySnapshot): ByteArray =
        (HEADER + "\n" + (snapshot.events + snapshot.candidateResponseBuckets + snapshot.shadow).joinToString("\n") + "\n")
            .toByteArray(Charsets.US_ASCII)

    fun decode(bytes: ByteArray): QualitySnapshot {
        require(bytes.size <= MAX_BYTES)
        val lines = bytes.toString(Charsets.US_ASCII).split('\n')
        val count = QualityEvent.entries.size + QualityModel.LATENCY_BUCKET_COUNT + ShadowResult.entries.size
        require(lines.size == count + 2 && lines.first() == HEADER && lines.last().isEmpty())
        val values = lines.drop(1).dropLast(1).map { line ->
            require(line.isNotEmpty() && line.length <= 13 && line.all { it in '0'..'9' })
            requireNotNull(line.toLongOrNull()).also { require(it <= QualityModel.MAX_COUNT) }
        }
        val eventsEnd = QualityEvent.entries.size
        val latencyEnd = eventsEnd + QualityModel.LATENCY_BUCKET_COUNT
        return QualitySnapshot(values.take(eventsEnd), values.subList(eventsEnd, latencyEnd), values.drop(latencyEnd))
    }
}
