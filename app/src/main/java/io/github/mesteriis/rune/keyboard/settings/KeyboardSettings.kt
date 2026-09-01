package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState

enum class HeightPreset(val multiplier: Float) {
    COMPACT(0.85f),
    NORMAL(1.0f),
    LARGE(1.15f),
}

enum class GapPreset {
    TIGHT,
    NORMAL,
    WIDE,
}

enum class ThemePreference {
    SYSTEM,
    LIGHT,
    DARK,
}

enum class HapticMode {
    OFF,
    SYSTEM,
    LIGHT,
    NORMAL,
    STRONG,
}

enum class SoundMode {
    OFF,
    SYSTEM,
    QUIET,
    NORMAL,
}

enum class SizeBucket {
    COVER_PORTRAIT,
    COVER_LANDSCAPE,
    INNER_PORTRAIT,
    INNER_LANDSCAPE;

    companion object {
        /**
         * Mirrors the `sw600dp` resource qualifier boundary so the stored preset and the base
         * dimension resource always describe the same screen (FOLD-002, no vendor SDK needed).
         */
        const val INNER_SCREEN_MIN_WIDTH_DP = 600

        fun resolve(smallestScreenWidthDp: Int, isLandscape: Boolean): SizeBucket {
            val inner = smallestScreenWidthDp >= INNER_SCREEN_MIN_WIDTH_DP
            return when {
                inner && isLandscape -> INNER_LANDSCAPE
                inner -> INNER_PORTRAIT
                isLandscape -> COVER_LANDSCAPE
                else -> COVER_PORTRAIT
            }
        }
    }
}

sealed interface StartingLanguage {
    data object LastUsed : StartingLanguage
    data class Fixed(val language: KeyboardLanguage) : StartingLanguage
}

data class KeyboardSettings(
    val enabledLanguages: List<KeyboardLanguage>,
    val startingLanguage: StartingLanguage,
    val heightPresets: Map<SizeBucket, HeightPreset>,
    val keyGap: GapPreset,
    val numberRow: Boolean,
    val theme: ThemePreference,
    val hapticMode: HapticMode,
    val soundMode: SoundMode,
    val keyPreview: Boolean,
    val doubleSpacePeriod: Boolean,
) {
    init {
        require(enabledLanguages.isNotEmpty()) { "At least one language must stay enabled" }
    }

    fun heightPreset(bucket: SizeBucket): HeightPreset = heightPresets[bucket] ?: HeightPreset.NORMAL

    /** Settings whose change requires rebuilding the keyboard view. */
    fun affectsKeyboardView(other: KeyboardSettings): Boolean =
        theme != other.theme ||
            keyGap != other.keyGap ||
            numberRow != other.numberRow ||
            keyPreview != other.keyPreview ||
            heightPresets != other.heightPresets

    companion object {
        val DEFAULT = KeyboardSettings(
            enabledLanguages = KeyboardState.DEFAULT_LANGUAGES,
            startingLanguage = StartingLanguage.LastUsed,
            heightPresets = emptyMap(),
            keyGap = GapPreset.NORMAL,
            numberRow = false,
            theme = ThemePreference.SYSTEM,
            hapticMode = HapticMode.SYSTEM,
            soundMode = SoundMode.SYSTEM,
            keyPreview = true,
            doubleSpacePeriod = true,
        )
    }
}
