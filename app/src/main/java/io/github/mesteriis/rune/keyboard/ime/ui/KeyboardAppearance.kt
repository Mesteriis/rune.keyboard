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
internal class KeyboardAppearance(context: Context, val theme: KeyboardTheme) {
    private val density = context.resources.displayMetrics.density
    val background: Int = grey(when (theme) {
        KeyboardTheme.AIR -> 0x18
        KeyboardTheme.SOFT -> 0x14
        KeyboardTheme.OUTLINE -> 0x10
        KeyboardTheme.MONOLITH -> 0x20
        KeyboardTheme.SILENT -> 0x08
    })
    val text = grey(if (theme == KeyboardTheme.SILENT) 0xCF else 0xE0)
    val secondaryText = grey(0xB8)
    val bottomBackground = if (theme == KeyboardTheme.MONOLITH) grey(0x16) else background
    val spaceIndicator = theme == KeyboardTheme.SILENT
    val textColors = ColorStateList(
        arrayOf(intArrayOf(android.R.attr.state_selected), intArrayOf()),
        intArrayOf(Color.WHITE, text),
    )

    fun keyBackground(spec: KeySpec, gapPx: Int, heightPx: Int): Drawable {
        val enter = spec.action == KeyboardAction.Enter
        val space = spec.style == KeyStyle.SPACE
        val utility = spec.style == KeyStyle.ACTION || space
        val outlined = theme == KeyboardTheme.OUTLINE && utility
        val fill = when {
            outlined -> Color.TRANSPARENT
            enter -> grey(when (theme) {
                KeyboardTheme.AIR -> 0x46
                KeyboardTheme.SILENT -> 0x36
                else -> 0x55
            })
            theme == KeyboardTheme.SOFT && utility -> grey(if (space) 0x25 else 0x2B)
            theme == KeyboardTheme.AIR && space -> grey(0x26)
            else -> Color.TRANSPARENT
        }
        val radius = when (theme) {
            KeyboardTheme.SOFT -> 100f
            KeyboardTheme.OUTLINE -> 5f
            KeyboardTheme.MONOLITH -> 6f
            KeyboardTheme.SILENT -> 12f
            KeyboardTheme.AIR -> if (enter) 10f else 8f
        }
        val normal = surface(fill, radius, if (outlined) grey(if (enter) 0x74 else 0x43) else null)
        val pressed = surface(grey(0x48), radius)
        val selected = surface(grey(0x38), radius, if (outlined) grey(0x90) else null)
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
        addState(intArrayOf(android.R.attr.state_pressed), surface(grey(0x38), 6f))
        addState(intArrayOf(android.R.attr.state_focused), surface(grey(0x38), 6f))
        addState(intArrayOf(), surface(Color.TRANSPARENT, 6f))
    }

    fun popupBackground(): Drawable = surface(grey(0x2C), 10f, grey(0x50))
    fun popupSelection(): Drawable = surface(grey(0x50), 7f)

    private fun surface(fill: Int, radius: Float, stroke: Int? = null): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = radius * density
            if (stroke != null) setStroke(dp(1f).coerceAtLeast(1), stroke)
        }

    private fun dp(value: Float): Int = (value * density + 0.5f).toInt()
    private fun grey(value: Int): Int = Color.rgb(value, value, value)
}
