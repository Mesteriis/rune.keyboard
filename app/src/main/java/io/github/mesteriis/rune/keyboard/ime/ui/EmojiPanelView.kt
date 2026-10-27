package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Paint
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.GridView
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiCatalog
import io.github.mesteriis.rune.keyboard.ime.RuneTrace
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiEntry
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiPalette
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Native, recycled cells; all data/font work starts only when this panel is opened. */
internal class EmojiPanelView(
    context: Context,
    private val rowHeight: Int,
    private val appearance: KeyboardAppearance,
    private val dispatch: (KeyboardAction) -> Unit,
) : LinearLayout(context) {
    private val glyphPaint = Paint().apply {
        textSize = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 28f, resources.displayMetrics)
    }
    private val palette = EmojiPalette({ RuneTrace.section("Rune#emojiCatalogRead") {
        EmojiCatalog.read(context.assets.open(EmojiCatalog.ASSET_PATH))
    } }, glyphPaint::hasGlyph)
    private var language = KeyboardLanguage.ENGLISH
    private var selectedCategory: String? = "smileys"
    private var recentsAllowed = true
    private var entries: List<EmojiEntry> = emptyList()
    private val tabs = LinearLayout(context).apply { orientation = HORIZONTAL }
    private val cells = object : BaseAdapter() {
        override fun getCount(): Int = entries.size
        override fun getItem(position: Int): EmojiEntry = entries[position]
        override fun getItemId(position: Int): Long = position.toLong()
        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View =
            ((convertView as? TextView) ?: TextView(context).apply {
                gravity = Gravity.CENTER
                includeFontPadding = false
                setTextSize(TypedValue.COMPLEX_UNIT_PX, glyphPaint.textSize)
                setTextColor(appearance.text)
                background = appearance.candidateBackground()
                layoutParams = android.widget.AbsListView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, rowHeight)
            }).apply {
                val item = getItem(position)
                text = item.glyph
                contentDescription = item.names.inLanguage(language)
            }
    }
    private val grid = GridView(context).apply {
        numColumns = GridView.AUTO_FIT
        columnWidth = (48f * resources.displayMetrics.density + 0.5f).toInt()
        stretchMode = GridView.STRETCH_COLUMN_WIDTH
        adapter = cells
        setOnItemClickListener { _, _, position, _ -> dispatch(KeyboardAction.CommitText(entries[position].glyph)) }
    }
    private val empty = TextView(context).apply {
        gravity = Gravity.CENTER
        setTextColor(appearance.secondaryText)
    }

    init {
        orientation = VERTICAL
        layoutDirection = LAYOUT_DIRECTION_LTR
        addView(HorizontalScrollView(context).apply {
            isHorizontalScrollBarEnabled = false
            addView(tabs)
        }, LayoutParams(LayoutParams.MATCH_PARENT, rowHeight))
        val body = android.widget.FrameLayout(context)
        body.addView(grid, android.widget.FrameLayout.LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        body.addView(empty, android.widget.FrameLayout.LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        grid.emptyView = empty
        addView(body, LayoutParams(LayoutParams.MATCH_PARENT, rowHeight * 2))
    }

    fun render(language: KeyboardLanguage, recentsAllowed: Boolean) {
        this.language = language
        this.recentsAllowed = recentsAllowed
        if (!recentsAllowed && selectedCategory == null) selectedCategory = "smileys"
        tabs.removeAllViews()
        fun tab(id: String?, icon: String, description: String) {
            tabs.addView(TextView(context).apply {
                text = icon
                contentDescription = description
                gravity = Gravity.CENTER
                setTextSize(TypedValue.COMPLEX_UNIT_SP, 22f)
                setTextColor(appearance.textColors)
                background = appearance.candidateBackground()
                isSelected = selectedCategory == id
                isFocusable = true
                setOnClickListener { selectedCategory = id; render(language, recentsAllowed) }
            }, LayoutParams((48f * resources.displayMetrics.density + 0.5f).toInt(), rowHeight))
        }
        RuneTrace.section("Rune#emojiTabs") {
            if (recentsAllowed) tab(null, "◷", localized("Recent emoji", "Недавние эмодзи", "Emojis recientes"))
            palette.categories.forEach { category -> tab(category.id, category.icon, category.names.inLanguage(language)) }
        }
        entries = RuneTrace.section("Rune#emojiGlyphFilter") {
            selectedCategory?.let(palette::entries) ?: palette.recents
        }
        empty.text = if (selectedCategory == null) localized("No recent emoji", "Нет недавних эмодзи", "No hay emojis recientes")
            else localized("No supported emoji", "Нет доступных эмодзи", "No hay emojis compatibles")
        cells.notifyDataSetChanged()
        grid.setSelection(0)
    }

    fun recordCommitted(glyph: String) {
        if (!recentsAllowed) return
        palette.recordCommitted(glyph)
        if (selectedCategory == null) {
            entries = palette.recents
            cells.notifyDataSetChanged()
        }
    }

    private fun localized(en: String, ru: String, es: String): String = when (language) {
        KeyboardLanguage.ENGLISH -> en
        KeyboardLanguage.RUSSIAN -> ru
        KeyboardLanguage.SPANISH -> es
    }
}
