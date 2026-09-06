package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.util.Arrays

enum class EditCostProfile(val adjacentSubstitution: Int, val transposition: Int) {
    /** Quarter-unit costs: insertion/deletion/substitution/transposition all equal one. */
    UNIT(4, 4),
    /** Fixed initial features, not calibrated AutoReplace confidence or acceptance thresholds. */
    INITIAL(3, 5),

    ;

    init {
        require(adjacentSubstitution in 2..4 && transposition in 4..8)
        require(2 * transposition >= 8 && transposition + adjacentSubstitution >= 8)
    }
}

data class EditFeatures(
    val editCost: Double,
    val repeatedCharacterEdits: Int,
    /** Separate ranking feature: never subtracted from the distance inside this algorithm. */
    val repetitionBonus: Double,
)

/**
 * Unrestricted last-occurrence DL, not OSA. Canonical NFC and ROOT lowercase keep accents.
 * Fixed profiles enforce 2*T >= I+D and T+min(S) >= I+D; substitution costs obey the
 * triangle inequality. The latter bound avoids discounted substitution after transposition.
 * Each instance belongs to one worker: reusable primitive scratch is not thread-safe.
 */
class WeightedDamerauLevenshtein(private val profile: EditCostProfile = EditCostProfile.INITIAL) {
    private val left = IntArray(TokenUnicode.MAX_CODE_POINTS)
    private val right = IntArray(TokenUnicode.MAX_CODE_POINTS)
    private val lastSourceForTarget = IntArray(TokenUnicode.MAX_CODE_POINTS)
    private val distance = IntArray(STRIDE * STRIDE)

    fun features(source: String, target: String, language: KeyboardLanguage): EditFeatures {
        try {
            val m = copy(TokenUnicode.folded(source), left)
            val n = copy(TokenUnicode.folded(target), right)
            for (i in 0..m) {
                distance[(i + 1) * STRIDE] = INFINITY
                distance[(i + 1) * STRIDE + 1] = i * UNIT_COST
            }
            for (j in 0..n) {
                distance[j + 1] = INFINITY
                distance[STRIDE + j + 1] = j * UNIT_COST
            }
            distance[0] = INFINITY
            for (i in 1..m) {
                var lastMatchingColumn = 0
                for (j in 1..n) {
                    val priorRow = lastSourceForTarget[j - 1]
                    val priorColumn = lastMatchingColumn
                    val same = left[i - 1] == right[j - 1]
                    val substitution = if (same) 0 else if (
                        KeyboardDistance.areAdjacent(left[i - 1], right[j - 1], language)
                    ) profile.adjacentSubstitution else UNIT_COST
                    if (same) lastMatchingColumn = j
                    val replace = distance[i * STRIDE + j] + substitution
                    val insert = distance[(i + 1) * STRIDE + j] + UNIT_COST
                    val delete = distance[i * STRIDE + j + 1] + UNIT_COST
                    val transpose = distance[priorRow * STRIDE + priorColumn] +
                        (i - priorRow - 1) * UNIT_COST + profile.transposition +
                        (j - priorColumn - 1) * UNIT_COST
                    distance[(i + 1) * STRIDE + j + 1] = minOf(minOf(replace, insert), minOf(delete, transpose))
                }
                for (j in 0 until n) if (left[i - 1] == right[j]) lastSourceForTarget[j] = i
            }
            val repeats = repetitionEdits(m, n)
            return EditFeatures(distance[(m + 1) * STRIDE + n + 1] / 4.0, repeats, repeats * 0.25)
        } finally {
            // The instance retains capacity, never the previous token's numeric code points.
            Arrays.fill(left, 0)
            Arrays.fill(right, 0)
            Arrays.fill(lastSourceForTarget, 0)
            Arrays.fill(distance, 0)
        }
    }

    private fun copy(text: String, destination: IntArray): Int {
        var offset = 0
        var count = 0
        while (offset < text.length) {
            val cp = text.codePointAt(offset)
            destination[count++] = cp
            offset += Character.charCount(cp)
        }
        return count
    }

    /** Only pure changes to existing repeated runs qualify; unrelated edits earn no bonus. */
    private fun repetitionEdits(m: Int, n: Int): Int {
        var i = 0
        var j = 0
        var changes = 0
        while (i < m && j < n) {
            val cp = left[i]
            if (cp != right[j]) return 0
            val startI = i
            val startJ = j
            while (i < m && left[i] == cp) i++
            while (j < n && right[j] == cp) j++
            changes += kotlin.math.abs((i - startI) - (j - startJ))
        }
        return if (i == m && j == n) changes else 0
    }

    companion object {
        private const val STRIDE = TokenUnicode.MAX_CODE_POINTS + 2
        private const val UNIT_COST = 4
        private const val INFINITY = 1_024
    }
}
