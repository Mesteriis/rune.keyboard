package io.github.mesteriis.rune.keyboard.ime.ui

import io.github.mesteriis.rune.keyboard.settings.KeyboardTheme
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import org.junit.Assert.assertTrue
import org.junit.Test

class KeyboardPaletteColorsTest {
    private fun luminance(color: Int): Double {
        fun channel(shift: Int): Double {
            val value = ((color ushr shift) and 255) / 255.0
            return if (value <= .04045) value / 12.92 else ((value + .055) / 1.055).pow(2.4)
        }
        return .2126 * channel(16) + .7152 * channel(8) + .0722 * channel(0)
    }

    private fun contrast(a: Int, b: Int): Double {
        val x = luminance(a); val y = luminance(b)
        return (max(x, y) + .05) / (min(x, y) + .05)
    }

    @Test fun `text and outline contrast hold for each shape and palette`() {
        for (theme in KeyboardTheme.entries) for (light in listOf(false, true)) {
            val colors = KeyboardPaletteColors.create(theme, light)
            val surfaces = listOf(colors.background, colors.bottomBackground, colors.enter,
                colors.softAction, colors.softSpace, colors.airSpace, colors.pressed,
                colors.selected, colors.popup, colors.popupSelection)
            for (surface in surfaces) {
                assertTrue("$theme light=$light text contrast ${contrast(colors.text, surface)}",
                    contrast(colors.text, surface) >= 4.5)
                assertTrue("$theme light=$light secondary contrast ${contrast(colors.secondaryText, surface)}",
                    contrast(colors.secondaryText, surface) >= 3.0)
                assertTrue("$theme light=$light selected text contrast ${contrast(colors.selectedText, surface)}",
                    contrast(colors.selectedText, surface) >= 4.5)
            }
            if (theme == KeyboardTheme.OUTLINE) {
                assertTrue(contrast(colors.outline, colors.background) >= 3.0)
                assertTrue(contrast(colors.enterOutline, colors.background) >= 3.0)
                assertTrue(contrast(colors.selectedOutline, colors.selected) >= 3.0)
            }
        }
    }
}
