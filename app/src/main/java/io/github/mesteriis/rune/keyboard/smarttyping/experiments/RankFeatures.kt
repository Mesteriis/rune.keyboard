package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.util.Locale
import kotlin.math.abs
import kotlin.math.ln
import kotlin.math.max

/** RET2 feature order is frozen by tools/typing_experiments/rank_refinement.py. */
internal object RankFeatures {
    const val COUNT = 95
    private val endings = listOf("ть", "ти", "ет", "ют", "ут", "ит", "ат", "ят", "ла", "ли", "ый", "ий", "ая", "яя", "ое", "ее", "ые", "ие", "ого", "ему", "ому", "ой", "ей", "ам", "ям", "ах", "ях", "ом", "ем", "ов", "ев", "а", "я", "ы", "и", "у", "ю", "о", "е", "ь")
    private val prepositions = listOf("в", "на", "с", "к", "по", "из", "от", "до", "для", "у", "о", "об", "без", "за", "под", "над", "перед", "при", "через", "между")

    fun extract(context: String, original: String, candidate: String, distance: Int,
        frequency: Int, editCost: Double, fallback: Boolean): DoubleArray {
        val a = original.lowercase(Locale.ROOT)
        val b = candidate.lowercase(Locale.ROOT)
        val previous = context.takeLast(128).lowercase(Locale.ROOT).trimEnd().takeLastWhile { !it.isWhitespace() }
        val suffixKey = previous.takeLast(2) + ":" + b.takeLast(2)
        val bucket = suffixKey.mapIndexed { i, c -> (i + 1) * c.code }.sum() % 16
        val size = max(max(a.length, b.length), 1).toDouble()
        fun flag(value: Boolean) = if (value) 1.0 else 0.0
        fun overlap(k: Int): Double {
            val left = a.windowed(k).toSet()
            val right = b.windowed(k).toSet()
            return left.intersect(right).size.toDouble() / max(1, left.union(right).size)
        }
        val extra = a.length == b.length + 1 && a.indices.any { a.removeRange(it, it + 1) == b }
        return DoubleArray(COUNT).apply {
            this[0] = distance.coerceIn(0, 3) / 3.0
            this[1] = ln(1.0 + frequency.coerceIn(1, 1_000_000)) / ln(1_000_001.0)
            this[2] = abs(original.length - b.length).coerceAtMost(6) / 6.0
            this[3] = if (editCost.isFinite()) editCost.coerceIn(0.0, 4.0) / 4.0 else 1.0
            this[4] = flag(fallback)
            this[5] = flag(a.takeLast(2) == b.takeLast(2))
            this[6 + bucket] = 1.0
            this[22] = a.commonPrefixWith(b).length / size
            this[23] = a.commonSuffixWith(b).length / size
            this[24] = (b.length - a.length) / size
            this[25] = overlap(2)
            this[26] = overlap(3)
            this[27] = flag(a.length == b.length && a.indices.count { a[it] != b[it] } == 1)
            this[28] = flag(a.length == b.length && (0 until a.length - 1).any {
                a.substring(0, it) + a[it + 1] + a[it] + a.substring(it + 2) == b
            })
            this[29] = flag(b.length == a.length + 1 && b.indices.any { b.removeRange(it, it + 1) == a })
            this[30] = flag(extra)
            this[31] = flag(extra && (0 until a.length - 1).any { a[it] == a[it + 1] && a.removeRange(it, it + 1) == b })
            this[32] = a.length.coerceAtMost(32) / 32.0
            this[33] = b.length.coerceAtMost(32) / 32.0
            this[34] = flag(a.take(1) == b.take(1))
            endings.forEachIndexed { i, ending -> this[35 + i] = flag(b.endsWith(ending)) }
            prepositions.forEachIndexed { i, preposition -> this[35 + endings.size + i] = flag(previous == preposition) }
        }
    }
}
