package io.github.mesteriis.rune.keyboard.settings

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

/**
 * Rune's configuration screen, built from plain framework views to keep the app dependency-free.
 * Every change is written immediately; a running keyboard picks it up through its preference
 * listener.
 */
class SettingsActivity : ThemedActivity() {
    private lateinit var preferences: KeyboardPreferences
    private lateinit var container: LinearLayout
    private lateinit var inflater: LayoutInflater
    private var settings = KeyboardSettings.DEFAULT
    private var appliedTheme = ThemePreference.SYSTEM

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        setTitle(R.string.settings_title)
        preferences = KeyboardPreferences(this)
        inflater = LayoutInflater.from(this)
        container = findViewById(R.id.settings_container)
        applySystemBarInsets(findViewById<View>(R.id.settings_scroll))
        appliedTheme = themePreference()
    }

    override fun onResume() {
        super.onResume()
        if (themePreference() != appliedTheme) {
            recreate()
            return
        }
        reload()
    }

    private fun reload() {
        settings = preferences.readSettings()
        buildRows()
    }

    private fun buildRows() {
        container.removeAllViews()

        addSection(R.string.settings_section_languages)
        addNavigationRow(
            titleRes = R.string.settings_languages_row,
            summary = languagesSummary(),
        ) {
            startActivity(Intent(this, LanguageSettingsActivity::class.java))
        }

        addSection(R.string.settings_section_typing)
        addToggleRow(
            titleRes = R.string.settings_double_space,
            summaryRes = R.string.settings_double_space_summary,
            checked = settings.doubleSpacePeriod,
        ) { enabled ->
            preferences.writeDoubleSpacePeriod(enabled)
        }
        addToggleRow(
            titleRes = R.string.settings_key_preview,
            summaryRes = R.string.settings_key_preview_summary,
            checked = settings.keyPreview,
        ) { enabled ->
            preferences.writeKeyPreview(enabled)
        }

        addSection(R.string.settings_section_layout)
        addToggleRow(
            titleRes = R.string.settings_number_row,
            summaryRes = R.string.settings_number_row_summary,
            checked = settings.numberRow,
        ) { enabled ->
            preferences.writeNumberRow(enabled)
        }
        addHeightRow(
            titleRes = R.string.settings_height_cover,
            portrait = SizeBucket.COVER_PORTRAIT,
            landscape = SizeBucket.COVER_LANDSCAPE,
        )
        addHeightRow(
            titleRes = R.string.settings_height_inner,
            portrait = SizeBucket.INNER_PORTRAIT,
            landscape = SizeBucket.INNER_LANDSCAPE,
        )
        addChoiceRow(
            titleRes = R.string.settings_key_gap,
            values = GapPreset.entries,
            labels = GapPreset.entries.map { getString(gapLabel(it)) },
            selected = settings.keyGap,
        ) { preset ->
            preferences.writeKeyGap(preset)
        }

        addSection(R.string.settings_section_appearance)
        addChoiceRow(
            titleRes = R.string.settings_theme,
            values = ThemePreference.entries,
            labels = ThemePreference.entries.map { getString(themeLabel(it)) },
            selected = settings.theme,
        ) { theme ->
            preferences.writeTheme(theme)
            recreate()
        }

        addSection(R.string.settings_section_feedback)
        addChoiceRow(
            titleRes = R.string.settings_haptic,
            values = HapticMode.entries,
            labels = HapticMode.entries.map { getString(hapticLabel(it)) },
            selected = settings.hapticMode,
        ) { mode ->
            preferences.writeHapticMode(mode)
        }
        addChoiceRow(
            titleRes = R.string.settings_sound,
            values = SoundMode.entries,
            labels = SoundMode.entries.map { getString(soundLabel(it)) },
            selected = settings.soundMode,
        ) { mode ->
            preferences.writeSoundMode(mode)
        }

        addSection(R.string.settings_section_privacy)
        addInfoRow(
            title = getString(R.string.settings_section_privacy),
            summary = getString(R.string.settings_privacy_summary),
        )

        addSection(R.string.settings_section_about)
        addInfoRow(title = getString(R.string.settings_version), summary = versionName())
        addNavigationRow(titleRes = R.string.settings_setup_guide, summary = null) {
            startActivity(Intent(this, SetupActivity::class.java))
        }
    }

    private fun addSection(titleRes: Int) {
        val header = inflater.inflate(R.layout.view_settings_section, container, false) as TextView
        header.setText(titleRes)
        container.addView(header)
    }

    private fun addInfoRow(title: String, summary: String?) {
        val row = newRow(title, summary)
        row.isClickable = false
        row.foreground = null
        container.addView(row)
    }

    private fun addNavigationRow(titleRes: Int, summary: String?, onClick: () -> Unit) {
        val row = newRow(getString(titleRes), summary)
        row.setOnClickListener { onClick() }
        container.addView(row)
    }

    private fun addToggleRow(
        titleRes: Int,
        summaryRes: Int,
        checked: Boolean,
        onChanged: (Boolean) -> Unit,
    ) {
        val row = newRow(getString(titleRes), getString(summaryRes))
        val checkBox = row.findViewById<CheckBox>(R.id.row_checkbox)
        checkBox.visibility = View.VISIBLE
        checkBox.isChecked = checked
        row.setOnClickListener {
            val updated = !checkBox.isChecked
            checkBox.isChecked = updated
            onChanged(updated)
            reload()
        }
        container.addView(row)
    }

    private fun <T> addChoiceRow(
        titleRes: Int,
        values: List<T>,
        labels: List<String>,
        selected: T,
        onSelected: (T) -> Unit,
    ) {
        val selectedIndex = values.indexOf(selected).coerceAtLeast(0)
        val row = newRow(getString(titleRes), labels[selectedIndex])
        row.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle(titleRes)
                .setSingleChoiceItems(labels.toTypedArray(), selectedIndex) { dialog, which ->
                    dialog.dismiss()
                    onSelected(values[which])
                    reload()
                }
                .show()
        }
        container.addView(row)
    }

    /**
     * One row per screen writes both orientations of that screen; the base height per orientation
     * comes from the qualifier-selected dimension resource.
     */
    private fun addHeightRow(titleRes: Int, portrait: SizeBucket, landscape: SizeBucket) {
        addChoiceRow(
            titleRes = titleRes,
            values = HeightPreset.entries,
            labels = HeightPreset.entries.map { getString(heightLabel(it)) },
            selected = settings.heightPreset(portrait),
        ) { preset ->
            preferences.writeHeightPreset(portrait, preset)
            preferences.writeHeightPreset(landscape, preset)
        }
    }

    private fun newRow(title: String, summary: String?): LinearLayout {
        val row = inflater.inflate(R.layout.view_settings_row, container, false) as LinearLayout
        row.findViewById<TextView>(R.id.row_title).text = title
        val summaryView = row.findViewById<TextView>(R.id.row_summary)
        if (summary.isNullOrEmpty()) {
            summaryView.visibility = View.GONE
        } else {
            summaryView.visibility = View.VISIBLE
            summaryView.text = summary
        }
        return row
    }

    private fun languagesSummary(): String {
        val order = settings.enabledLanguages.joinToString(" → ") { it.compactLabel }
        val starting = when (val startingLanguage = settings.startingLanguage) {
            StartingLanguage.LastUsed -> getString(R.string.settings_language_last_used)
            is StartingLanguage.Fixed -> startingLanguage.language.displayLabel
        }
        return "$order · ${getString(R.string.settings_language_starting)}: $starting"
    }

    private fun versionName(): String = runCatching {
        packageManager.getPackageInfo(packageName, 0).versionName
    }.getOrNull().orEmpty()

    private fun heightLabel(preset: HeightPreset): Int = when (preset) {
        HeightPreset.COMPACT -> R.string.height_compact
        HeightPreset.NORMAL -> R.string.height_normal
        HeightPreset.LARGE -> R.string.height_large
    }

    private fun gapLabel(preset: GapPreset): Int = when (preset) {
        GapPreset.TIGHT -> R.string.gap_tight
        GapPreset.NORMAL -> R.string.gap_normal
        GapPreset.WIDE -> R.string.gap_wide
    }

    private fun themeLabel(theme: ThemePreference): Int = when (theme) {
        ThemePreference.SYSTEM -> R.string.theme_system
        ThemePreference.LIGHT -> R.string.theme_light
        ThemePreference.DARK -> R.string.theme_dark
    }

    private fun hapticLabel(mode: HapticMode): Int = when (mode) {
        HapticMode.OFF -> R.string.haptic_off
        HapticMode.SYSTEM -> R.string.haptic_system
        HapticMode.LIGHT -> R.string.haptic_light
        HapticMode.NORMAL -> R.string.haptic_normal
        HapticMode.STRONG -> R.string.haptic_strong
    }

    private fun soundLabel(mode: SoundMode): Int = when (mode) {
        SoundMode.OFF -> R.string.sound_off
        SoundMode.SYSTEM -> R.string.sound_system
        SoundMode.QUIET -> R.string.sound_quiet
        SoundMode.NORMAL -> R.string.sound_normal
    }
}
