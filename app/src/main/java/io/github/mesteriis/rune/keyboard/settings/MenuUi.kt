package io.github.mesteriis.rune.keyboard.settings

import android.app.Activity
import android.content.res.ColorStateList
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.view.Gravity
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

/** Shared framework controls for the home, directory and settings detail screens. */
internal class MenuUi(private val activity: Activity) {
    fun dp(value: Int): Int = (value * activity.resources.displayMetrics.density + .5f).toInt()
    fun color(id: Int): Int = activity.getColor(id)
    fun column(): LinearLayout = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
    fun text(value: CharSequence, size: Float = 16f, secondary: Boolean = false): TextView =
        TextView(activity).apply {
            text = value
            textSize = size
            setTextColor(color(if (secondary) R.color.setup_text_secondary else R.color.setup_text_primary))
            includeFontPadding = false
        }
    fun surface(): GradientDrawable = GradientDrawable().apply {
        setColor(color(R.color.setup_surface))
        cornerRadius = dp(12).toFloat()
        setStroke(dp(1), color(R.color.setup_border))
    }
    fun interactive(view: View) {
        view.isFocusable = true
        view.foreground = RippleDrawable(ColorStateList.valueOf(color(R.color.setup_border)), null, null)
    }
    fun icon(resource: Int, secondary: Boolean = false): ImageView = ImageView(activity).apply {
        setImageResource(resource)
        imageTintList = ColorStateList.valueOf(color(if (secondary) R.color.setup_text_secondary else R.color.setup_text_primary))
        importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
    }
    fun divider(parent: LinearLayout) {
        parent.addView(View(activity).apply { setBackgroundColor(color(R.color.setup_border)) },
            LinearLayout.LayoutParams(-1, dp(1)))
    }
    fun section(parent: LinearLayout, title: Int) {
        parent.addView(text(activity.getString(title).uppercase(activity.resources.configuration.locales[0]), 12f, true).apply {
            letterSpacing = .04f
            setPadding(0, dp(26), 0, dp(10))
        })
        divider(parent)
    }
    fun row(parent: LinearLayout, title: String, summary: String?, iconRes: Int, click: () -> Unit): LinearLayout {
        val row = LinearLayout(activity).apply {
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(65)
            setPadding(0, dp(12), 0, dp(12))
        }
        row.addView(icon(iconRes), LinearLayout.LayoutParams(dp(26), dp(26)).apply { marginEnd = dp(18) })
        val labels = column()
        labels.addView(text(title))
        if (!summary.isNullOrBlank()) labels.addView(text(summary, 12.5f, true).apply {
            setPadding(0, dp(4), 0, 0)
        })
        row.addView(labels, LinearLayout.LayoutParams(0, -2, 1f))
        row.addView(icon(R.drawable.ic_menu_chevron, true), LinearLayout.LayoutParams(dp(20), dp(20)).apply { marginStart = dp(8) })
        interactive(row)
        row.setOnClickListener { click() }
        parent.addView(row, LinearLayout.LayoutParams(-1, -2))
        divider(parent)
        return row
    }
    fun shell(home: Boolean, scrollId: Int, contentId: Int, navigate: (Boolean) -> Unit): Shell {
        val root = column().apply {
            id = R.id.menu_root
            setBackgroundColor(color(R.color.setup_background))
        }
        val content = column().apply {
            id = contentId
            val pagePadding = maxOf(22, (activity.resources.configuration.screenWidthDp - 600) / 2)
            setPadding(dp(pagePadding), dp(14), dp(pagePadding), dp(20))
        }
        val scroll = ScrollView(activity).apply {
            id = scrollId
            isFillViewport = true
            isVerticalScrollBarEnabled = false
            addView(content)
        }
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        val bottom = column()
        divider(bottom)
        val tabs = LinearLayout(activity)
        listOf(true, false).forEach { isHome ->
            val tab = column().apply {
                id = if (isHome) R.id.menu_home_tab else R.id.menu_settings_tab
                gravity = Gravity.CENTER
                isSelected = isHome == home
                contentDescription = activity.getString(if (isHome) R.string.menu_home else R.string.menu_settings)
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
                descendantFocusability = android.view.ViewGroup.FOCUS_BLOCK_DESCENDANTS
            }
            tab.addView(icon(if (isHome) R.drawable.ic_menu_home else R.drawable.ic_menu_settings, isHome != home),
                LinearLayout.LayoutParams(dp(24), dp(24)))
            tab.addView(text(tab.contentDescription, 12f, isHome != home).apply { gravity = Gravity.CENTER; setPadding(0, dp(5), 0, 0) })
            interactive(tab)
            tab.setOnClickListener { if (isHome != home || !isHome) navigate(isHome) }
            tabs.addView(tab, LinearLayout.LayoutParams(0, dp(68), 1f))
        }
        bottom.addView(tabs)
        root.addView(bottom)
        return Shell(root, content, scroll, bottom)
    }
    fun heading(parent: LinearLayout, title: String, back: (() -> Unit)? = null) {
        val line = LinearLayout(activity).apply { gravity = Gravity.CENTER_VERTICAL }
        if (back != null) {
            val button = icon(R.drawable.ic_menu_back).apply {
                id = R.id.menu_back
                contentDescription = activity.getString(R.string.menu_back_label)
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
                setPadding(dp(10), dp(10), dp(10), dp(10))
                setOnClickListener { back() }
            }
            interactive(button)
            line.addView(button, LinearLayout.LayoutParams(dp(48), dp(48)).apply { marginEnd = dp(6) })
        }
        line.addView(text(title, if (back == null) 28f else 23f).apply {
            id = R.id.menu_detail_title
            setTypeface(typeface, Typeface.BOLD)
            setPadding(0, dp(12), 0, dp(12))
            if (android.os.Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
        }, LinearLayout.LayoutParams(0, -2, 1f))
        parent.addView(line)
    }
    data class Shell(val root: LinearLayout, val content: LinearLayout, val scroll: ScrollView, val bottom: LinearLayout)
}
