package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.nio.BufferUnderflowException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs

/** CatBoost symmetric numeric trees; no executable model code or Android ML dependency. */
internal class ObliviousTreeRanker private constructor(
    private val featureCount: Int,
    private val scale: Float,
    private val bias: Float,
    private val trees: List<Tree>,
) {
    private class Tree(val features: IntArray, val borders: FloatArray, val leaves: FloatArray)

    fun score(features: DoubleArray): Double {
        if (features.size != featureCount || features.any { !it.isFinite() }) return Double.NaN
        var result = 0.0
        for (tree in trees) {
            var leaf = 0
            for (depth in tree.features.indices) {
                // CatBoost numeric input and borders are float32, strict greater-than split.
                if (features[tree.features[depth]].toFloat() > tree.borders[depth]) leaf = leaf or (1 shl depth)
            }
            result += tree.leaves[leaf]
        }
        return result * scale + bias
    }

    companion object {
        // Explicit numeric schema, without linking optional feature extractors into legacy replay tools.
        const val RIGHT_CONTEXT_FEATURES = 178
        fun decode(bytes: ByteArray, expectedFeatures: Int = ExperimentModels.RANK_FLOATS): ObliviousTreeRanker? {
            if (bytes.size !in 20..65_536) return null
            if (expectedFeatures != ExperimentModels.RANK_FLOATS && expectedFeatures != ContextualRanker.FEATURES &&
                expectedFeatures != RIGHT_CONTEXT_FEATURES) return null
            val input = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            return try {
                if ("RET2".any { input.get().toInt() != it.code } || input.int != expectedFeatures) return null
                val count = input.int
                if (count !in 1..128) return null
                val scale = input.float
                val bias = input.float
                if (!valid(scale) || !valid(bias)) return null
                val trees = ArrayList<Tree>(count)
                repeat(count) {
                    val depth = input.int
                    if (depth !in 1..6) return null
                    val features = IntArray(depth)
                    val borders = FloatArray(depth)
                    repeat(depth) { d ->
                        features[d] = input.int
                        borders[d] = input.float
                        if (features[d] !in 0 until expectedFeatures || !valid(borders[d])) return null
                    }
                    val leaves = FloatArray(1 shl depth) { input.float }
                    if (leaves.any { !valid(it) }) return null
                    trees.add(Tree(features, borders, leaves))
                }
                if (input.hasRemaining()) null else ObliviousTreeRanker(expectedFeatures, scale, bias, trees)
            } catch (_: BufferUnderflowException) { null }
        }

        private fun valid(value: Float): Boolean = value.isFinite() && abs(value) <= 32f
    }
}
