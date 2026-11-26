package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.InsetDrawable
import android.graphics.drawable.LayerDrawable
import android.graphics.drawable.StateListDrawable
import android.view.Gravity
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.settings.KeyboardTheme

/** Native, flat surfaces. Hidden key borders never change the full rectangular touch targets. */
internal class KeyboardAppearance(context: Context, val theme: KeyboardTheme, light: Boolean = false) {
    private val density = context.resources.displayMetrics.density
    private val colors = KeyboardPaletteColors.create(theme, light)
    val background = colors.background
    val text = colors.text
    val secondaryText = colors.secondaryText
    val bottomBackground = colors.bottomBackground
    val spaceIndicator = theme == KeyboardTheme.SILENT
    val textColors = ColorStateList(
        arrayOf(intArrayOf(android.R.attr.state_selected), intArrayOf()),
        intArrayOf(colors.selectedText, text),
    )

    fun keyBackground(spec: KeySpec, gapPx: Int, heightPx: Int): Drawable {
        val enter = spec.action == KeyboardAction.Enter
        val space = spec.style == KeyStyle.SPACE
        val utility = spec.style == KeyStyle.ACTION || space
        val outlined = theme == KeyboardTheme.OUTLINE && utility
        val fill = when {
            outlined -> Color.TRANSPARENT
            enter -> colors.enter
            theme == KeyboardTheme.SOFT && utility -> if (space) colors.softSpace else colors.softAction
            theme == KeyboardTheme.AIR && space -> colors.airSpace
            else -> Color.TRANSPARENT
        }
        val radius = when (theme) {
            KeyboardTheme.SOFT -> 100f
            KeyboardTheme.OUTLINE -> 5f
            KeyboardTheme.MONOLITH -> 6f
            KeyboardTheme.SILENT -> 12f
            KeyboardTheme.AIR -> if (enter) 10f else 8f
        }
        val normal = surface(fill, radius, if (outlined) if (enter) colors.enterOutline else colors.outline else null)
        val pressed = surface(colors.pressed, radius)
        val selected = surface(colors.selected, radius, if (outlined) colors.selectedOutline else null)
        val states = StateListDrawable().apply {
            addState(intArrayOf(android.R.attr.state_pressed), pressed)
            addState(intArrayOf(android.R.attr.state_selected), selected)
            addState(intArrayOf(android.R.attr.state_focused), selected)
            addState(intArrayOf(), normal)
        }
        if (theme == KeyboardTheme.SOFT && enter && spec.accessibilityLabel == null) {
            // A circle stays circular on both narrow phones and wide foldable screens.
            val diameter = (heightPx - dp(12f)).coerceAtLeast(1)
            return LayerDrawable(arrayOf<Drawable>(states)).apply {
                setLayerSize(0, diameter, diameter)
                setLayerGravity(0, Gravity.CENTER)
            }
        }
        return InsetDrawable(states, gapPx / 2 + dp(2f), dp(6f), gapPx / 2 + dp(2f), dp(6f))
    }

    fun candidateBackground(): Drawable = StateListDrawable().apply {
        addState(intArrayOf(android.R.attr.state_pressed), surface(colors.selected, 6f))
        addState(intArrayOf(android.R.attr.state_focused), surface(colors.selected, 6f))
        addState(intArrayOf(), surface(Color.TRANSPARENT, 6f))
    }

    fun popupBackground(): Drawable = surface(colors.popup, 10f, colors.popupStroke)
    fun popupSelection(): Drawable = surface(colors.popupSelection, 7f)

    private fun surface(fill: Int, radius: Float, stroke: Int? = null): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = radius * density
            if (stroke != null) setStroke(dp(1f).coerceAtLeast(1), stroke)
        }

    private fun dp(value: Float): Int = (value * density + 0.5f).toInt()
}
