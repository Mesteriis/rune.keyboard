package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Typeface
import android.util.TypedValue
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeyAlternate

/** The mini row shown above a key while its long-press alternates are being chosen. */
internal class AlternatesRowView(context: Context) : LinearLayout(context) {
    private val cellWidth = resources.getDimensionPixelSize(R.dimen.keyboard_popup_cell_width)
    private val rowHeight = resources.getDimensionPixelSize(R.dimen.keyboard_popup_row_height)
    private val textSizePx = resources.getDimension(R.dimen.keyboard_popup_text_size)

    private var selected = 0

    init {
        orientation = HORIZONTAL
        layoutDirection = LAYOUT_DIRECTION_LTR
        gravity = Gravity.CENTER
        isBaselineAligned = false
        background = context.getDrawable(R.drawable.key_popup_background)
    }

    fun setAlternates(alternates: List<KeyAlternate>) {
        removeAllViews()
        alternates.forEach { alternate ->
            addView(createCell(alternate))
        }
        selected = 0
        applySelection()
    }

    /** A negative index means the gesture is currently cancelled: nothing is highlighted. */
    var selectedIndex: Int
        get() = selected
        set(value) {
            if (selected == value) return
            selected = value
            applySelection()
        }

    private fun createCell(alternate: KeyAlternate): TextView = TextView(context).apply {
        text = alternate.label
        gravity = Gravity.CENTER
        includeFontPadding = false
        maxLines = 1
        setPadding(0, 0, 0, 0)
        setTextSize(TypedValue.COMPLEX_UNIT_PX, textSizePx)
        typeface = Typeface.DEFAULT
        setTextColor(context.getColor(R.color.key_text))
        contentDescription = alternate.label
        layoutParams = LayoutParams(cellWidth, rowHeight)
    }

    private fun applySelection() {
        for (index in 0 until childCount) {
            val cell = getChildAt(index) as? TextView ?: continue
            val isSelected = index == selected
            cell.background = if (isSelected) {
                context.getDrawable(R.drawable.key_popup_cell_selected)
            } else {
                null
            }
            cell.setTextColor(
                context.getColor(if (isSelected) R.color.key_text_accent else R.color.key_text),
            )
        }
    }
}
