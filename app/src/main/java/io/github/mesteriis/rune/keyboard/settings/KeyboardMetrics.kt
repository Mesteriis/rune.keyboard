package io.github.mesteriis.rune.keyboard.settings

/** Resolved pixel metrics handed to the keyboard view at construction time. */
data class KeyboardViewMetrics(
    val keyHeightPx: Int,
    val keyGapPx: Int,
) {
    init {
        require(keyHeightPx > 0) { "Key height must be positive" }
        require(keyGapPx >= 0) { "Key gap must not be negative" }
    }
}

object KeyboardMetrics {
    private const val MIN_KEY_HEIGHT_PX = 1

    /** Applies the user's height preset on top of the qualifier-selected base dimension. */
    fun keyHeightPx(baseHeightPx: Int, preset: HeightPreset): Int {
        val scaled = Math.round(baseHeightPx * preset.multiplier)
        return if (scaled < MIN_KEY_HEIGHT_PX) MIN_KEY_HEIGHT_PX else scaled
    }
}
