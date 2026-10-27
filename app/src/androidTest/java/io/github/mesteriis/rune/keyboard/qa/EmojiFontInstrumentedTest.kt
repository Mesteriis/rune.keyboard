package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Paint
import android.os.Build
import android.os.Bundle
import android.util.TypedValue
import android.view.View
import android.view.ViewGroup
import android.widget.GridView
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiCatalog
import io.github.mesteriis.rune.keyboard.ime.emoji.EmojiEntry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.ui.EmojiPanelView
import io.github.mesteriis.rune.keyboard.ime.ui.KeyboardAppearance
import io.github.mesteriis.rune.keyboard.settings.KeyboardTheme
import io.github.mesteriis.rune.keyboard.settings.SetupActivity
import org.junit.Assert.*
import org.junit.Test

/** Exact device-font membership, localized adapter binding and recycling; no font fallback claims. */
class EmojiFontInstrumentedTest {
    @Test fun everyCategoryMatchesActualFontSupportAndRecycledCellsUseCurrentLanguage() {
        check(Build.HARDWARE in setOf("ranchu", "goldfish"))
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
            var result: Result<Bundle>? = null
            scenario.onActivity { activity ->
                result = runCatching {
                    val catalog = EmojiCatalog.read(activity.assets.open(EmojiCatalog.ASSET_PATH))
                    val paint = Paint().apply {
                        textSize = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 28f, activity.resources.displayMetrics)
                    }
                    val expected = catalog.categories.associate { it.id to it.entries.filter { item -> paint.hasGlyph(item.glyph) } }
                    val panel = EmojiPanelView(activity, (48 * activity.resources.displayMetrics.density).toInt(),
                        KeyboardAppearance(activity, KeyboardTheme.AIR)) { }
                    val host = activity.findViewById<ViewGroup>(R.id.menu_preview)
                    host.removeAllViews()
                    host.addView(panel)
                    for (language in KeyboardLanguage.entries) {
                        panel.render(language, recentsAllowed = false)
                        for (category in catalog.categories) {
                            val tab = descendants(panel).single { it.contentDescription?.toString() == category.names.inLanguage(language) }
                            assertTrue(tab.performClick())
                            val grid = descendants(panel).filterIsInstance<GridView>().single()
                            val items = (0 until grid.adapter.count).map { grid.adapter.getItem(it) as EmojiEntry }
                            assertEquals(expected.getValue(category.id), items)
                            if (items.size >= 2) {
                                val first = grid.adapter.getView(0, null, grid)
                                val recycled = grid.adapter.getView(1, first, grid) as TextView
                                assertSame(first, recycled)
                                assertEquals(items[1].glyph, recycled.text.toString())
                                assertEquals(items[1].names.inLanguage(language), recycled.contentDescription.toString())
                            }
                        }
                    }
                    val total = catalog.categories.sumOf { it.entries.size }
                    val supported = expected.values.sumOf { it.size }
                    assertEquals(1898, total)
                    if (Build.VERSION.SDK_INT == 26) {
                        assertTrue("The pinned API 26 system font must exclude modern sequences", supported < total)
                        assertFalse(paint.hasGlyph("🙂‍↔️"))
                        assertTrue(expected.values.flatten().none { it.glyph == "🙂‍↔️" })
                    }
                    Bundle().apply {
                        putInt("emoji_font_api", Build.VERSION.SDK_INT)
                        putInt("emoji_catalog_count", total)
                        putInt("emoji_font_supported_count", supported)
                        putInt("emoji_font_unsupported_count", total - supported)
                        putInt("emoji_locales_checked", KeyboardLanguage.entries.size)
                        putInt("emoji_categories_checked", catalog.categories.size)
                    }
                }
            }
            instrumentation.sendStatus(2, checkNotNull(result).getOrThrow())
        }
    }

    private fun descendants(view: View): List<View> = listOf(view) + if (view is ViewGroup)
        (0 until view.childCount).flatMap { descendants(view.getChildAt(it)) } else emptyList()
}
