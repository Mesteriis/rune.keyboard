package io.github.mesteriis.rune.keyboard.ime.ui

import io.github.mesteriis.rune.keyboard.settings.KeyboardTheme

/** Immutable keyboard-only colors; no Android resources or user state are retained. */
internal data class KeyboardPaletteColors(
    val background: Int,
    val bottomBackground: Int,
    val text: Int,
    val secondaryText: Int,
    val selectedText: Int,
    val enter: Int,
    val softAction: Int,
    val softSpace: Int,
    val airSpace: Int,
    val pressed: Int,
    val selected: Int,
    val outline: Int,
    val enterOutline: Int,
    val selectedOutline: Int,
    val popup: Int,
    val popupStroke: Int,
    val popupSelection: Int,
) {
    companion object {
        private fun grey(value: Int): Int = (0xff000000L or (value.toLong() shl 16) or
            (value.toLong() shl 8) or value.toLong()).toInt()

        fun create(theme: KeyboardTheme, light: Boolean): KeyboardPaletteColors {
            val background = if (light) when (theme) {
                KeyboardTheme.AIR -> 0xf4
                KeyboardTheme.SOFT -> 0xf2
                KeyboardTheme.OUTLINE -> 0xfa
                KeyboardTheme.MONOLITH -> 0xe8
                KeyboardTheme.SILENT -> 0xf8
            } else when (theme) {
                KeyboardTheme.AIR -> 0x18
                KeyboardTheme.SOFT -> 0x14
                KeyboardTheme.OUTLINE -> 0x10
                KeyboardTheme.MONOLITH -> 0x20
                KeyboardTheme.SILENT -> 0x08
            }
            val enter = if (light) 0xd8 else when (theme) {
                KeyboardTheme.AIR -> 0x46
                KeyboardTheme.SILENT -> 0x36
                else -> 0x55
            }
            return KeyboardPaletteColors(
                grey(background), grey(if (theme == KeyboardTheme.MONOLITH) if (light) 0xe0 else 0x16 else background),
                grey(if (light) 0x1a else if (theme == KeyboardTheme.SILENT) 0xcf else 0xe0),
                grey(if (light) 0x48 else 0xb8), grey(if (light) 0x0a else 0xff),
                grey(enter), grey(if (light) 0xe0 else 0x2b), grey(if (light) 0xe7 else 0x25),
                grey(if (light) 0xe5 else 0x26), grey(if (light) 0xc8 else 0x48),
                grey(if (light) 0xd2 else 0x38), grey(if (light) 0x70 else 0x69),
                grey(if (light) 0x70 else 0x74), grey(if (light) 0x60 else 0x90),
                grey(if (light) 0xf2 else 0x2c), grey(if (light) 0x70 else 0x50),
                grey(if (light) 0xd0 else 0x50),
            )
        }
    }
}
