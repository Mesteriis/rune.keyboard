package io.github.mesteriis.rune.keyboard.settings

import android.app.AlertDialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/**
 * Enables languages and fixes the order the space bar swipe cycles through (LANG-004).
 * Enabled languages come first, in cycle order; disabled ones follow and cannot be reordered.
 */
class LanguageSettingsActivity : ThemedActivity() {
    private lateinit var preferences: KeyboardPreferences
    private lateinit var container: LinearLayout
    private lateinit var inflater: LayoutInflater
    private var enabledLanguages: List<KeyboardLanguage> = KeyboardSettings.DEFAULT.enabledLanguages
    private var startingLanguage: StartingLanguage = StartingLanguage.LastUsed

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_languages)
        setTitle(R.string.settings_languages_title)
        preferences = KeyboardPreferences(this)
        inflater = LayoutInflater.from(this)
        container = findViewById(R.id.languages_container)
        applySystemBarInsets(findViewById<View>(R.id.languages_scroll))
    }

    override fun onResume() {
        super.onResume()
        val settings = preferences.readSettings()
        enabledLanguages = settings.enabledLanguages
        startingLanguage = settings.startingLanguage
        buildRows()
    }

    private fun buildRows() {
        container.removeAllViews()
        displayOrder().forEach { language -> container.addView(languageRow(language)) }
        container.addView(startingLanguageRow())
    }

    private fun displayOrder(): List<KeyboardLanguage> =
        enabledLanguages + KeyboardLanguage.entries.filterNot { it in enabledLanguages }

    private fun languageRow(language: KeyboardLanguage): View {
        val row = inflater.inflate(R.layout.view_language_row, container, false) as LinearLayout
        val isEnabled = language in enabledLanguages
        val index = enabledLanguages.indexOf(language)

        row.findViewById<TextView>(R.id.language_name).text = language.displayLabel
        row.findViewById<CheckBox>(R.id.language_enabled).apply {
            isChecked = isEnabled
            contentDescription = language.displayLabel
            setOnClickListener { toggle(language) }
        }
        row.findViewById<Button>(R.id.language_move_up).apply {
            this.isEnabled = isEnabled && index > 0
            setOnClickListener { move(language, -1) }
        }
        row.findViewById<Button>(R.id.language_move_down).apply {
            this.isEnabled = isEnabled && index >= 0 && index < enabledLanguages.lastIndex
            setOnClickListener { move(language, 1) }
        }
        return row
    }

    private fun startingLanguageRow(): View {
        val row = inflater.inflate(R.layout.view_settings_row, container, false) as LinearLayout
        row.findViewById<TextView>(R.id.row_title).setText(R.string.settings_language_starting)
        row.findViewById<TextView>(R.id.row_summary).apply {
            visibility = View.VISIBLE
            text = startingLanguageLabel(startingLanguage)
        }
        row.setOnClickListener { showStartingLanguageDialog() }
        return row
    }

    private fun showStartingLanguageDialog() {
        val options = listOf(StartingLanguage.LastUsed) +
            enabledLanguages.map { StartingLanguage.Fixed(it) }
        val labels = options.map(::startingLanguageLabel).toTypedArray()
        val selectedIndex = options.indexOf(startingLanguage).coerceAtLeast(0)
        AlertDialog.Builder(this)
            .setTitle(R.string.settings_language_starting)
            .setSingleChoiceItems(labels, selectedIndex) { dialog, which ->
                dialog.dismiss()
                preferences.writeStartingLanguage(options[which])
                startingLanguage = options[which]
                buildRows()
            }
            .show()
    }

    private fun startingLanguageLabel(startingLanguage: StartingLanguage): String =
        when (startingLanguage) {
            StartingLanguage.LastUsed -> getString(R.string.settings_language_last_used)
            is StartingLanguage.Fixed -> startingLanguage.language.displayLabel
        }

    private fun toggle(language: KeyboardLanguage) {
        val updated = if (language in enabledLanguages) {
            enabledLanguages - language
        } else {
            enabledLanguages + language
        }
        if (updated.isEmpty()) {
            Toast.makeText(this, R.string.settings_language_min_warning, Toast.LENGTH_SHORT).show()
            buildRows()
            return
        }
        apply(updated)
    }

    private fun move(language: KeyboardLanguage, offset: Int) {
        val index = enabledLanguages.indexOf(language)
        val target = index + offset
        if (index < 0 || target < 0 || target > enabledLanguages.lastIndex) return
        val updated = enabledLanguages.toMutableList()
        updated[index] = updated[target]
        updated[target] = language
        apply(updated)
    }

    private fun apply(updated: List<KeyboardLanguage>) {
        preferences.writeEnabledLanguages(updated)
        enabledLanguages = updated
        val starting = startingLanguage
        if (starting is StartingLanguage.Fixed && starting.language !in updated) {
            preferences.writeStartingLanguage(StartingLanguage.LastUsed)
            startingLanguage = StartingLanguage.LastUsed
        }
        buildRows()
    }
}
