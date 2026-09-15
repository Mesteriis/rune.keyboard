package io.github.mesteriis.rune.keyboard.smarttyping.touch

import kotlin.math.abs

/** Exact rendered geometry, including the current display configuration on folding devices. */
data class TouchLayoutProfile(
    val language: String,
    val layer: String,
    val widthPx: Int,
    val heightPx: Int,
    val orientation: Int,
    val screenWidthDp: Int,
    val screenHeightDp: Int,
    val densityDpi: Int,
    val displayId: Int,
    val geometrySignature: String,
) {
    internal fun valid(): Boolean = language in setOf("ENGLISH", "RUSSIAN", "SPANISH") &&
        layer == "LETTERS" && widthPx in 1..8192 && heightPx in 1..8192 &&
        orientation in 1..2 && screenWidthDp in 1..8192 && screenHeightDp in 1..8192 &&
        densityDpi in 1..1280 && displayId >= 0 && geometrySignature.matches(Regex("[a-f0-9]{64}"))
}

/** Offset of a physical tap from a possible intended key's centre, in that key's width/height. */
data class TouchKeyOffset(val key: Char, val x: Double, val y: Double)

data class PhysicalTouchSample(
    val profile: TouchLayoutProfile,
    val observedKey: Char,
    val offsets: List<TouchKeyOffset>,
)

/**
 * Stores aggregate offsets, never word history or absolute touch coordinates. The caller owns
 * editor acknowledgement and must clear pending samples on failed edits and session boundaries.
 * Only confirmWord trains; observing and ranking cannot change the calibration.
 */
class TouchCalibrationModel {
    private data class Mean(val count: Int, val x: Double, val y: Double)
    private val profiles = linkedMapOf<TouchLayoutProfile, LinkedHashMap<Char, Mean>>()
    private val pending = ArrayList<PhysicalTouchSample>()
    private var enabled = false
    private var overflowed = false

    @Synchronized
    fun setEnabled(enabled: Boolean) {
        this.enabled = enabled
        if (!enabled) clearPending()
    }

    @Synchronized
    fun observe(sample: PhysicalTouchSample) {
        if (!enabled) return
        if (!valid(sample)) {
            clearPending()
            return
        }
        if (pending.firstOrNull()?.profile?.let { it != sample.profile } == true) clearPending()
        if (overflowed) return
        if (pending.size >= MAX_WORD_LENGTH) {
            clearPending()
            overflowed = true
            return
        }
        pending += sample.copy(offsets = sample.offsets.toList())
    }

    @Synchronized
    fun clearPending() {
        pending.clear()
        overflowed = false
    }

    /** Same-length words only: ambiguous insertion/deletion alignments provide no supervision. */
    @Synchronized
    fun confirmWord(observed: String, intended: String): Boolean {
        val trace = matchingTrace(observed, intended) ?: run {
            clearPending()
            return false
        }
        clearPending()
        val targets = intended.map { it.lowercaseChar() }
        // Require the whole confirmed pair to fit the captured local neighbourhood.
        val offsets = trace.mapIndexed { index, sample ->
            sample.offsets.firstOrNull { it.key == targets[index] } ?: return false
        }
        val profile = trace.first().profile
        val means = profiles[profile] ?: linkedMapOf<Char, Mean>().also {
            if (profiles.size >= MAX_PROFILES) profiles.remove(profiles.keys.first())
            profiles[profile] = it
        }
        var changed = false
        offsets.forEach { offset ->
            if (abs(offset.x) > MAX_OFFSET || abs(offset.y) > MAX_OFFSET) return@forEach
            val old = means[offset.key]
            if (old != null && old.count >= MIN_SAMPLES &&
                (abs(offset.x - old.x) > MAX_RESIDUAL || abs(offset.y - old.y) > MAX_RESIDUAL)
            ) return@forEach
            if (old == null && means.size >= MAX_KEYS) return@forEach
            val count = ((old?.count ?: 0) + 1).coerceAtMost(MAX_SAMPLES)
            means[offset.key] = Mean(
                count,
                (old?.x ?: 0.0) + (offset.x - (old?.x ?: 0.0)) / count,
                (old?.y ?: 0.0) + (offset.y - (old?.y ?: 0.0)) / count,
            )
            changed = true
        }
        return changed
    }

    /** Bounded manual ranking evidence; this must never admit an automatic replacement. */
    @Synchronized
    fun candidateBonus(observed: String, candidate: String): Double {
        val trace = matchingTrace(observed, candidate) ?: return 0.0
        val means = profiles[trace.first().profile] ?: return 0.0
        if (observed.indices.none { index ->
                observed[index].lowercaseChar() != candidate[index].lowercaseChar() &&
                    ((means[observed[index].lowercaseChar()]?.count ?: 0) >= MIN_SAMPLES ||
                        (means[candidate[index].lowercaseChar()]?.count ?: 0) >= MIN_SAMPLES)
            }
        ) return 0.0
        fun cost(word: String): Double? {
            var sum = 0.0
            word.forEachIndexed { index, key ->
                val offset = trace[index].offsets.firstOrNull { it.key == key.lowercaseChar() } ?: return null
                val mean = means[key.lowercaseChar()]?.takeIf { it.count >= MIN_SAMPLES }
                val shrinkage = mean?.let { it.count.toDouble() / (it.count + PRIOR_SAMPLES) } ?: 0.0
                val dx = offset.x - (mean?.x ?: 0.0) * shrinkage
                val dy = offset.y - (mean?.y ?: 0.0) * shrinkage
                sum += dx * dx + dy * dy
            }
            return sum / word.length
        }
        val originalCost = cost(observed) ?: return 0.0
        val candidateCost = cost(candidate) ?: return 0.0
        return ((originalCost - candidateCost) * 0.25).coerceIn(-0.5, 0.5)
    }

    @Synchronized
    fun reset() {
        profiles.clear()
        clearPending()
    }

    /** Versioned, bounded aggregate codec. No pending sample or word can be serialized. */
    @Synchronized
    fun encodeSnapshot(): String = buildString {
        append("RUNE_TOUCH_1\n")
        profiles.forEach { (profile, means) ->
            means.forEach { (key, mean) ->
                append(listOf(profile.language, profile.layer, profile.widthPx, profile.heightPx,
                    profile.orientation, profile.screenWidthDp, profile.screenHeightDp,
                    profile.densityDpi, profile.displayId, profile.geometrySignature,
                    key.code, mean.count, mean.x, mean.y).joinToString("\t"))
                append('\n')
            }
        }
    }

    /** Rejects a malformed snapshot atomically, preserving the current calibration. */
    @Synchronized
    fun restoreSnapshot(snapshot: String): Boolean {
        if (snapshot.length > MAX_SNAPSHOT_BYTES || !snapshot.startsWith("RUNE_TOUCH_1\n")) return false
        val decoded = linkedMapOf<TouchLayoutProfile, LinkedHashMap<Char, Mean>>()
        val lines = snapshot.lineSequence().drop(1).filter { it.isNotEmpty() }.iterator()
        var records = 0
        try {
            while (lines.hasNext()) {
                if (++records > MAX_PROFILES * MAX_KEYS) return false
                val cells = lines.next().split('\t')
                if (cells.size != 14) return false
                val profile = TouchLayoutProfile(cells[0], cells[1], cells[2].toInt(), cells[3].toInt(),
                    cells[4].toInt(), cells[5].toInt(), cells[6].toInt(), cells[7].toInt(),
                    cells[8].toInt(), cells[9])
                if (!profile.valid()) return false
                val code = cells[10].toInt()
                if (code !in 0..Char.MAX_VALUE.code) return false
                val key = code.toChar()
                val mean = Mean(cells[11].toInt(), cells[12].toDouble(), cells[13].toDouble())
                if (!key.isLetter() || key != key.lowercaseChar() || mean.count !in 1..MAX_SAMPLES ||
                    !mean.x.isFinite() || !mean.y.isFinite() || abs(mean.x) > MAX_OFFSET ||
                    abs(mean.y) > MAX_OFFSET
                ) return false
                val means = decoded.getOrPut(profile) { linkedMapOf() }
                if (means.put(key, mean) != null || means.size > MAX_KEYS || decoded.size > MAX_PROFILES) return false
            }
        } catch (_: NumberFormatException) {
            return false
        }
        profiles.clear()
        profiles.putAll(decoded)
        clearPending()
        return true
    }

    private fun matchingTrace(observed: String, intended: String): List<PhysicalTouchSample>? {
        if (!enabled || overflowed || observed.isEmpty() || observed.length != intended.length ||
            observed.length != pending.size || !intended.all(Char::isLetter) ||
            observed.indices.any { observed[it].lowercaseChar() != pending[it].observedKey }
        ) return null
        return pending.toList()
    }

    private fun valid(sample: PhysicalTouchSample): Boolean = sample.profile.valid() &&
        sample.observedKey.isLetter() && sample.observedKey == sample.observedKey.lowercaseChar() &&
        sample.offsets.size in 1..MAX_NEIGHBOURS &&
        sample.offsets.map { it.key }.distinct().size == sample.offsets.size &&
        sample.offsets.any { it.key == sample.observedKey } && sample.offsets.all {
            it.key.isLetter() && it.key == it.key.lowercaseChar() && it.x.isFinite() &&
                it.y.isFinite() && abs(it.x) <= 2.0 && abs(it.y) <= 2.0
        }

    companion object {
        const val MAX_WORD_LENGTH = 48
        const val MAX_PROFILES = 12
        const val MAX_KEYS = 64
        const val MAX_NEIGHBOURS = 12
        const val MAX_SAMPLES = 64
        const val MIN_SAMPLES = 6
        const val MAX_SNAPSHOT_BYTES = 256 * 1024
        private const val PRIOR_SAMPLES = 8
        private const val MAX_OFFSET = 1.25
        private const val MAX_RESIDUAL = 0.75
    }
}
