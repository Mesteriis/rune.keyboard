package io.github.mesteriis.rune.keyboard.settings

import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayoutProvider
import io.github.mesteriis.rune.keyboard.ime.layout.LayoutOptions
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView

/** Daily home. The sample editor is local and never enters the learning pipeline. */
class SetupActivity : ThemedActivity() {
    private lateinit var ui: MenuUi
    private lateinit var shell: MenuUi.Shell
    private lateinit var preferences: KeyboardPreferences
    private lateinit var status: TextView
    private lateinit var subtitle: TextView
    private lateinit var connect: TextView
    private lateinit var sample: EditText
    private lateinit var previewHost: FrameLayout
    private lateinit var themeName: TextView
    private lateinit var themeSummary: TextView
    private lateinit var choices: LinearLayout
    private lateinit var quickLinks: LinearLayout
    private var appliedTheme = ThemePreference.SYSTEM
    private var state = KeyboardState(KeyboardState.DEFAULT_LANGUAGES.first())
    private val editor = EditorContext.from(InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE, 0)
    private val layouts = KeyboardLayoutProvider()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = KeyboardPreferences(this)
        ui = MenuUi(this)
        shell = ui.shell(true, R.id.setup_scroll, View.generateViewId()) {
            startActivity(SettingsActivity.intent(this, null).apply {
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            })
        }
        setContentView(shell.root)
        applySystemBarInsets(shell.root)
        appliedTheme = themePreference()
        val top = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        top.addView(ui.text("RUNE", 16f).apply { letterSpacing = .28f; gravity = Gravity.CENTER_VERTICAL; setTypeface(typeface, android.graphics.Typeface.BOLD) }, LinearLayout.LayoutParams(0, ui.dp(48), 1f))
        top.addView(ui.icon(R.drawable.ic_menu_settings).apply {
            contentDescription = getString(R.string.menu_settings)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            setPadding(ui.dp(11), ui.dp(11), ui.dp(11), ui.dp(11))
            ui.interactive(this)
            setOnClickListener { openSettings() }
        }, LinearLayout.LayoutParams(ui.dp(48), ui.dp(48)))
        shell.content.addView(top)
        status = ui.text("", 30f).apply {
            id = R.id.keyboard_status
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setPadding(0, ui.dp(18), 0, ui.dp(9))
        }
        shell.content.addView(status)
        subtitle = ui.text("", 14f, true).apply { setPadding(0, 0, 0, ui.dp(18)) }
        shell.content.addView(subtitle)
        connect = ui.text(getString(R.string.menu_connect), 15f).apply {
            gravity = Gravity.CENTER
            background = ui.surface()
            ui.interactive(this)
            setOnClickListener { startActivity(Intent(this@SetupActivity, KeyboardSetupActivity::class.java)) }
            visibility = View.GONE
        }
        shell.content.addView(connect, LinearLayout.LayoutParams(-1, ui.dp(48)).apply { bottomMargin = ui.dp(14) })
        sample = EditText(this).apply {
            id = R.id.menu_try_input
            hint = getString(R.string.menu_try)
            textSize = 16f
            setTextColor(ui.color(R.color.setup_text_primary))
            setHintTextColor(ui.color(R.color.setup_text_secondary))
            background = ui.surface()
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            showSoftInputOnFocus = false
            setPadding(ui.dp(14), ui.dp(12), ui.dp(14), ui.dp(12))
            minHeight = ui.dp(52)
            maxLines = 3
            // Sample text intentionally does not survive recreating this screen.
            isSaveEnabled = false
        }
        shell.content.addView(sample, LinearLayout.LayoutParams(-1, -2))
        previewHost = FrameLayout(this).apply {
            id = R.id.menu_preview
            if (android.os.Build.VERSION.SDK_INT >= 28) accessibilityPaneTitle = getString(R.string.menu_preview)
            background = ui.surface()
            clipToOutline = true
            setPadding(ui.dp(1), ui.dp(1), ui.dp(1), ui.dp(1))
        }
        shell.content.addView(previewHost, LinearLayout.LayoutParams(-1, -2).apply { topMargin = ui.dp(14) })
        themeName = ui.text("", 13f).apply { id = R.id.menu_theme_name; gravity = Gravity.CENTER; setPadding(0, ui.dp(12), 0, ui.dp(4)) }
        themeSummary = ui.text("", 12f, true).apply { gravity = Gravity.CENTER }
        shell.content.addView(themeName)
        shell.content.addView(themeSummary)
        choices = LinearLayout(this).apply { id = R.id.menu_theme_choices; gravity = Gravity.CENTER }
        shell.content.addView(choices)
        quickLinks = ui.column()
        shell.content.addView(quickLinks)
    }

    override fun onResume() {
        super.onResume()
        if (themePreference() != appliedTheme) { recreate(); return }
        val settings = preferences.readSettings()
        state = state.copy(enabledLanguages = settings.enabledLanguages,
            language = state.language.takeIf { it in settings.enabledLanguages } ?: settings.enabledLanguages.first())
        showTheme()
        updateStatus()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && ::status.isInitialized) updateStatus()
    }

    private fun showTheme() {
        val settings = preferences.readSettings()
        val selected = settings.keyboardTheme
        themeName.setText(themeTitle(selected))
        themeSummary.setText(themeDescription(selected))
        previewHost.removeAllViews()
        val keyboard = RuneKeyboardView(this, KeyboardViewMetrics(ui.dp(46), ui.dp(3)), selected).apply {
            // The shell owns system insets; an embedded preview is not a docked IME window.
            setOnApplyWindowInsetsListener { _, insets -> insets }
        }
        fun render() { keyboard.render(layouts.layoutFor(state, editor, LayoutOptions(showNumberRow = settings.numberRow, keyFlicks = settings.keyFlicks)), state) }
        keyboard.setOnActionListener { action ->
            sample.requestFocus()
            state = PreviewEditor.apply(sample, state, action, editor)
            render()
        }
        render()
        previewHost.addView(keyboard)
        choices.removeAllViews()
        KeyboardTheme.entries.forEach { theme ->
            val button = FrameLayout(this).apply {
                contentDescription = getString(themeTitle(theme))
                isSelected = theme == selected
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
                ui.interactive(this)
                setOnClickListener {
                    preferences.writeKeyboardTheme(theme)
                    showTheme()
                }
            }
            // Small theme indicators retain a full 48dp touch target.
            button.addView(View(this).apply {
                background = android.graphics.drawable.GradientDrawable().apply {
                    shape = android.graphics.drawable.GradientDrawable.OVAL
                    setColor(ui.color(if (theme == selected) R.color.setup_text_primary else R.color.setup_border))
                }
            }, FrameLayout.LayoutParams(ui.dp(8), ui.dp(8), Gravity.CENTER))
            choices.addView(button, LinearLayout.LayoutParams(ui.dp(48), ui.dp(48)))
        }
        quickLinks.removeAllViews()
        ui.divider(quickLinks)
        ui.row(quickLinks, getString(R.string.menu_appearance), getString(themeTitle(selected)), R.drawable.ic_menu_palette) { openSettings(SettingsPage.APPEARANCE) }
        ui.row(quickLinks, getString(R.string.menu_languages_short), settings.enabledLanguages.joinToString(" · ") { it.compactLabel }, R.drawable.ic_menu_language) {
            startActivity(Intent(this, LanguageSettingsActivity::class.java))
        }
        ui.row(quickLinks, getString(R.string.menu_smart_input), getString(R.string.settings_autocorrection), R.drawable.ic_menu_typing) { openSettings(SettingsPage.TYPING) }
        ui.row(quickLinks, getString(R.string.menu_connect), null, R.drawable.ic_menu_link) {
            startActivity(Intent(this, KeyboardSetupActivity::class.java))
        }
    }

    private fun updateStatus() {
        val manager = getSystemService(InputMethodManager::class.java)
        val enabled = manager.enabledInputMethodList.any { it.packageName == packageName }
        val active = ComponentName.unflattenFromString(Settings.Secure.getString(contentResolver, Settings.Secure.DEFAULT_INPUT_METHOD).orEmpty())?.packageName == packageName
        connect.visibility = if (active) View.GONE else View.VISIBLE
        status.setText(if (active) R.string.menu_active else if (enabled) R.string.menu_enabled else R.string.menu_disabled)
        subtitle.setText(if (active) R.string.menu_tagline else R.string.menu_setup_hint)
    }

    private fun openSettings(page: SettingsPage? = null) = startActivity(SettingsActivity.intent(this, page))

    private fun themeTitle(theme: KeyboardTheme): Int = when (theme) {
        KeyboardTheme.AIR -> R.string.menu_air
        KeyboardTheme.SOFT -> R.string.menu_soft
        KeyboardTheme.OUTLINE -> R.string.menu_outline
        KeyboardTheme.MONOLITH -> R.string.menu_monolith
        KeyboardTheme.SILENT -> R.string.menu_silent
    }
    private fun themeDescription(theme: KeyboardTheme): Int = when (theme) {
        KeyboardTheme.AIR -> R.string.menu_air_summary
        KeyboardTheme.SOFT -> R.string.menu_soft_summary
        KeyboardTheme.OUTLINE -> R.string.menu_outline_summary
        KeyboardTheme.MONOLITH -> R.string.menu_monolith_summary
        KeyboardTheme.SILENT -> R.string.menu_silent_summary
    }
}
