package io.github.mesteriis.rune.keyboard.settings

import android.view.View
import android.widget.Switch
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

/** One native, named, checkable accessibility target; the full row remains touch-clickable. */
@Suppress("DEPRECATION") // Framework Switch intentionally avoids adding a UI dependency.
object SettingsToggleRow {
    fun bind(row: View, checked: Boolean, enabled: Boolean = true) {
        val toggle = row.findViewById<Switch>(R.id.row_checkbox)
        row.isEnabled = enabled
        row.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        val labels = listOf(R.id.row_title, R.id.row_badge, R.id.row_summary).map { id ->
            row.findViewById<TextView>(id).apply {
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }
        }
        toggle.apply {
            visibility = View.VISIBLE
            isChecked = checked
            isEnabled = enabled
            isClickable = true
            isFocusable = true
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            contentDescription = labels.filter { it.visibility == View.VISIBLE }.joinToString("\n") { it.text }
            setOnClickListener {
                // A consent dialog or async write must not optimistically display an unsaved value.
                isChecked = checked
                if (row.isEnabled) row.performClick()
            }
        }
    }
}
