package io.github.mesteriis.rune.keyboard.settings

import android.app.AlertDialog
import android.content.Intent
import android.content.Context
import android.text.Editable
import android.text.TextWatcher
import android.widget.EditText
import android.view.inputmethod.InputMethodManager
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingStore
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.intelligence.ui.ModelSettingsActivity
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.readiness.DiskModelReadinessProbe
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ModelRuntimeQualification
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsSettingsProvider
import java.io.File
import java.util.concurrent.atomic.AtomicInteger

/**
 * Rune's configuration screen, built from plain framework views to keep the app dependency-free.
 * Every change is written immediately; a running keyboard picks it up through its preference
 * listener.
 */
class SettingsActivity : ThemedActivity() {
    companion object {
        const val EXTRA_PAGE = "settings_page"
        fun intent(context: Context, page: SettingsPage?): Intent = Intent(context, SettingsActivity::class.java).apply {
            page?.let { putExtra(EXTRA_PAGE, it.name) }
        }
    }

    private lateinit var ui: MenuUi
    private lateinit var shell: MenuUi.Shell
    private var page: SettingsPage? = null
    private var searchQuery = ""
    private var currentSection = 0
    private var requestedRow = 0
    private val rows = mutableListOf<SettingRow>()
    private data class SettingRow(val view: View, val title: Int, val section: Int, val page: SettingsPage)
    private lateinit var preferences: KeyboardPreferences
    private lateinit var container: LinearLayout
    private lateinit var inflater: LayoutInflater
    private var settings = KeyboardSettings.DEFAULT
    private var appliedTheme = ThemePreference.SYSTEM
    private var contextualModelReady = false
    private val readinessGeneration = AtomicInteger()
    private var diagnosticsContribution: AutoCloseable? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ui = MenuUi(this)
        shell = ui.shell(false, R.id.settings_scroll, R.id.settings_container) { home ->
            val destination = if (home) Intent(this, SetupActivity::class.java) else intent(this, null)
            startActivity(destination.apply {
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            })
        }
        setContentView(shell.root)
        page = SettingsPage.fromName(savedInstanceState?.getString("page") ?: intent.getStringExtra(EXTRA_PAGE))
        searchQuery = savedInstanceState?.getString("search").orEmpty()
        requestedRow = savedInstanceState?.getInt("row") ?: 0
        setTitle(R.string.menu_settings)
        preferences = KeyboardPreferences(this)
        inflater = LayoutInflater.from(this)
        container = findViewById(R.id.settings_container)
        applySystemBarInsets(shell.root, includeIme = true)
        appliedTheme = themePreference()
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT) {
                navigateBack()
            }
        }
        PersonalTypingResources.get(this)
    }

    override fun onResume() {
        super.onResume()
        if (themePreference() != appliedTheme) {
            recreate()
            return
        }
        reload()
        refreshModelReadiness()
    }

    override fun onPause() {
        diagnosticsContribution?.close(); diagnosticsContribution = null
        readinessGeneration.incrementAndGet()
        super.onPause()
    }

    private fun refreshModelReadiness() {
        val generation = readinessGeneration.incrementAndGet()
        Thread({
            val hint = DiskModelReadinessProbe { File(noBackupFilesDir, "model-delivery") }
                .read { readinessGeneration.get() != generation }
            runOnUiThread {
                if (readinessGeneration.get() == generation && !isFinishing && !isDestroyed) {
                    val ready = hint == ModelReadinessHint.READY && ModelRuntimeQualification.CURRENT
                    if (contextualModelReady != ready) {
                        contextualModelReady = ready
                        buildRows()
                    }
                }
            }
        }, "Rune-settings-readiness").apply { isDaemon = true }.start()
    }

    @Deprecated("Framework activity result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != PERSONAL_PROFILE_REQUEST || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        PersonalTypingResources.get(this).personal.importProfile(
            { contentResolver.openInputStream(uri) ?: throw java.io.IOException("Profile unavailable") },
        ) { result -> runOnUiThread {
            preferences.notifyPersonalProfileChanged()
            if (!isFinishing && !isDestroyed) Toast.makeText(this, when (result) {
                PersonalTypingStore.ImportResult.IMPORTED -> R.string.settings_personal_imported
                PersonalTypingStore.ImportResult.EMPTY -> R.string.settings_personal_empty
                else -> R.string.settings_personal_failed
            }, Toast.LENGTH_LONG).show()
        } }
    }

    private fun reload() {
        settings = preferences.readSettings()
        buildRows()
    }

    private fun buildRows() {
        diagnosticsContribution?.close()
        container.removeAllViews()
        rows.clear()

        addSection(R.string.settings_section_languages)
        addNavigationRow(
            titleRes = R.string.settings_languages_row,
            summary = languagesSummary(),
        ) {
            startActivity(Intent(this, LanguageSettingsActivity::class.java))
        }

        addSection(R.string.settings_section_smart_typing)
        addChoiceRow(
            titleRes = R.string.settings_autocorrection,
            values = AutocorrectionMode.entries,
            labels = AutocorrectionMode.entries.map { getString(autocorrectionLabel(it)) },
            selected = settings.autocorrectionMode,
            summary = autocorrectionSummary(),
        ) { preferences.writeAutocorrectionMode(it) }
        addToggleRow(
            titleRes = R.string.settings_mechanical_punctuation,
            summaryRes = R.string.settings_mechanical_punctuation_summary,
            checked = settings.mechanicalPunctuation,
        ) { preferences.writeMechanicalPunctuation(it) }
        addChoiceRow(
            titleRes = R.string.settings_contextual_punctuation,
            values = ContextualPunctuationMode.entries,
            labels = ContextualPunctuationMode.entries.map { getString(contextualLabel(it)) },
            selected = settings.contextualPunctuationMode,
            summary = ContextualAvailability.summaryResource(settings.contextualPunctuationMode, contextualModelReady)
                ?.let(::getString),
        ) { preferences.writeContextualPunctuationMode(it) }
        addToggleRow(
            titleRes = R.string.settings_candidate_strip,
            summaryRes = R.string.settings_candidate_strip_summary,
            checked = settings.candidateStrip,
        ) { preferences.writeCandidateStrip(it) }
        addToggleRow(
            titleRes = R.string.settings_double_space,
            summaryRes = R.string.settings_double_space_summary,
            checked = settings.doubleSpacePeriod,
        ) { enabled ->
            preferences.writeDoubleSpacePeriod(enabled)
        }
        addSection(R.string.settings_section_tools)
        addNavigationRow(R.string.controls_disable_all, getString(R.string.controls_disable_all_summary)) {
            preferences.disableAdditionalTyping()
            reload()
        }
        addToggleRow(R.string.settings_quality_metrics, R.string.settings_quality_metrics_summary,
            settings.qualityMetrics) { preferences.writeQualityMetrics(it) }
        addToggleRow(R.string.settings_shadow_comparison, R.string.settings_shadow_comparison_summary,
            settings.shadowComparison) { preferences.writeShadowComparison(it) }
        addNavigationRow(R.string.quality_dashboard_title, getString(R.string.settings_quality_dashboard_summary)) {
            startActivity(Intent(this, io.github.mesteriis.rune.keyboard.settings.quality.QualityDashboardActivity::class.java))
        }
        addToggleRow(R.string.settings_word_boundaries, R.string.settings_word_boundaries_summary,
            settings.wordBoundarySuggestions) { preferences.writeWordBoundarySuggestions(it) }
        addToggleRow(R.string.settings_abbreviations, R.string.settings_abbreviations_summary,
            settings.abbreviations) { preferences.writeAbbreviations(it) }
        addNavigationRow(R.string.abbreviations_title, getString(R.string.settings_abbreviations_manage_summary)) {
            startActivity(Intent(this, AbbreviationSettingsActivity::class.java))
        }
        addToggleRow(R.string.settings_phrase_review, R.string.settings_phrase_review_summary,
            settings.phraseReview) { preferences.writePhraseReview(it) }
        addToggleRow(R.string.settings_visible_undo, R.string.settings_visible_undo_summary,
            settings.visibleUndo) { preferences.writeVisibleUndo(it) }
        addToggleRow(R.string.settings_protected_words, R.string.settings_protected_words_summary,
            settings.protectedWords) { preferences.writeProtectedWords(it) }
        addNavigationRow(R.string.controls_words_title, getString(R.string.controls_words_intro)) {
            startActivity(Intent(this, ProtectedWordsActivity::class.java))
        }
        addToggleRow(R.string.settings_app_profiles, R.string.settings_app_profiles_summary,
            settings.appProfiles) { preferences.writeAppProfiles(it) }
        addNavigationRow(R.string.controls_apps_title, getString(R.string.controls_apps_intro)) {
            startActivity(Intent(this, AppProfilesActivity::class.java))
        }
        addToggleRow(R.string.settings_collect_examples, R.string.settings_collect_examples_summary,
            settings.collectExamples) { preferences.writeCollectExamples(it) }
        addToggleRow(R.string.settings_learned_ranking, R.string.settings_learned_ranking_summary,
            settings.learnedRanking) { preferences.writeLearnedRanking(it) }
        addToggleRow(R.string.settings_compact_context, R.string.settings_compact_context_summary,
            settings.compactContext) { preferences.writeCompactContext(it) }
        addToggleRow(R.string.settings_dynamic_touch, R.string.settings_dynamic_touch_summary,
            settings.dynamicTouch) { preferences.writeDynamicTouch(it) }
        addToggleRow(R.string.settings_dynamic_touch_apply, R.string.settings_dynamic_touch_apply_summary,
            settings.dynamicTouchApply) { preferences.writeDynamicTouchApply(it) }
        addToggleRow(R.string.settings_typo_patterns, R.string.settings_typo_patterns_summary,
            settings.typoPatterns) { preferences.writeTypoPatterns(it) }
        addNavigationRow(R.string.learning_title, getString(R.string.settings_collect_examples_summary)) {
            startActivity(Intent(this, LearningLabActivity::class.java))
        }
        addToggleRow(R.string.settings_manual_candidate_expansion, R.string.settings_manual_candidate_expansion_summary,
            settings.manualCandidateExpansion) { preferences.writeManualCandidateExpansion(it) }
        addSection(R.string.settings_section_personal)
        addToggleRow(R.string.settings_personal_learning, R.string.settings_personal_learning_summary,
            settings.personalLearning) { preferences.writePersonalLearning(it) }
        addToggleRow(R.string.settings_touch_personalization, R.string.settings_touch_personalization_summary,
            settings.touchPersonalization) { preferences.writeTouchPersonalization(it) }
        addToggleRow(R.string.settings_phrase_suggestions, R.string.settings_phrase_suggestions_summary,
            settings.phraseSuggestions) { preferences.writePhraseSuggestions(it) }
        addNavigationRow(R.string.settings_import_phrases, getString(R.string.settings_import_phrases_summary)) {
            val resources = PersonalTypingResources.get(this)
            if (!resources.dictionaryLoaded || !resources.personal.isReady) {
                Toast.makeText(this, R.string.settings_personal_not_ready, Toast.LENGTH_LONG).show()
            } else {
                @Suppress("DEPRECATION")
                startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                }, PERSONAL_PROFILE_REQUEST)
            }
        }
        addNavigationRow(R.string.settings_reset_personal, getString(R.string.settings_reset_personal_summary)) {
            AlertDialog.Builder(this).setTitle(R.string.settings_reset_personal)
                .setMessage(R.string.settings_reset_personal_summary)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.settings_reset_personal) { _, _ ->
                    val resources = PersonalTypingResources.get(this)
                    resources.touch.reset { touchSuccess ->
                        resources.personal.reset { personalSuccess -> runOnUiThread {
                            preferences.notifyPersonalProfileChanged()
                            if (!isFinishing && !isDestroyed) Toast.makeText(this,
                                if (touchSuccess && personalSuccess) R.string.settings_personal_reset_done else
                                    R.string.settings_personal_failed, Toast.LENGTH_LONG).show()
                        } }
                    }
                }.show()
        }
        addSection(R.string.settings_section_typing)
        addToggleRow(R.string.settings_key_flicks, R.string.settings_key_flicks_summary,
            settings.keyFlicks) { preferences.writeKeyFlicks(it) }
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
            titleRes = R.string.settings_keyboard_theme,
            values = KeyboardTheme.entries,
            labels = KeyboardTheme.entries.map { getString(keyboardThemeLabel(it)) },
            selected = settings.keyboardTheme,
        ) { preferences.writeKeyboardTheme(it) }
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
        addNavigationRow(
            titleRes = R.string.settings_local_intelligence,
            summary = getString(R.string.settings_local_intelligence_summary),
        ) {
            startActivity(Intent(this, ModelSettingsActivity::class.java))
        }
        addInfoRow(
            title = getString(R.string.settings_section_privacy),
            summary = getString(R.string.settings_privacy_summary),
        )


        addSection(R.string.settings_section_about)
        addInfoRow(title = getString(R.string.settings_version), summary = versionName())
        addNavigationRow(titleRes = R.string.settings_setup_guide, summary = null) {
            startActivity(Intent(this, KeyboardSetupActivity::class.java))
        }
        renderPage()
    }

    private fun addSection(titleRes: Int) {
        currentSection = titleRes
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        page = SettingsPage.fromName(intent.getStringExtra(EXTRA_PAGE))
        searchQuery = ""
        requestedRow = 0
        reload()
        shell.scroll.scrollTo(0, 0)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("page", page?.name)
        outState.putString("search", searchQuery)
        outState.putInt("row", requestedRow)
        super.onSaveInstanceState(outState)
    }

    @Deprecated("Framework back callback")
    @android.annotation.SuppressLint("GestureBackNavigation") // API 33+ uses the registered platform callback.
    override fun onBackPressed() = navigateBack()

    private fun navigateBack() {
        if (page != null) {
            page = null
            requestedRow = 0
            buildRows()
            shell.scroll.scrollTo(0, 0)
        } else {
            finish()
        }
    }

    private fun record(view: View, title: Int) {
        view.tag = title
        rows += SettingRow(view, title, currentSection, SettingsPage.forRow(currentSection, title))
    }

    private fun openPage(destination: SettingsPage, targetRow: Int = 0) {
        getSystemService(InputMethodManager::class.java).hideSoftInputFromWindow(shell.root.windowToken, 0)
        when (destination) {
            SettingsPage.LANGUAGES -> startActivity(Intent(this, LanguageSettingsActivity::class.java))
            SettingsPage.MODEL -> startActivity(Intent(this, ModelSettingsActivity::class.java))
            else -> {
                page = destination
                requestedRow = targetRow
                buildRows()
                shell.scroll.scrollTo(0, 0)
            }
        }
    }

    private fun renderPage() {
        val destination = page
        shell.bottom.visibility = if (destination == null) View.VISIBLE else View.GONE
        if (destination == null) {
            ui.heading(container, getString(R.string.menu_settings))
            val search = EditText(this).apply {
                id = R.id.menu_search
                hint = getString(R.string.menu_search)
                contentDescription = hint
                textSize = 16f
                setTextColor(ui.color(R.color.setup_text_primary))
                setHintTextColor(ui.color(R.color.setup_text_secondary))
                background = ui.surface()
                setSingleLine(true)
                inputType = android.text.InputType.TYPE_CLASS_TEXT
                imeOptions = android.view.inputmethod.EditorInfo.IME_ACTION_SEARCH
                setPadding(ui.dp(14), ui.dp(14), ui.dp(14), ui.dp(14))
                val searchIcon = getDrawable(R.drawable.ic_key_search)!!.mutate().apply {
                    setTint(ui.color(R.color.setup_text_secondary))
                    setBounds(0, 0, ui.dp(22), ui.dp(22))
                }
                setCompoundDrawablesRelative(searchIcon, null, null, null)
                compoundDrawablePadding = ui.dp(12)
                setText(searchQuery)
            }
            container.addView(search, LinearLayout.LayoutParams(-1, -2).apply { topMargin = ui.dp(8) })
            val results = ui.column()
            container.addView(results)
            renderResults(results)
            search.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                    searchQuery = s?.toString().orEmpty()
                    renderResults(results)
                }
                override fun afterTextChanged(s: Editable?) = Unit
            })
            search.setOnEditorActionListener { _, _, _ ->
                getSystemService(InputMethodManager::class.java).hideSoftInputFromWindow(search.windowToken, 0)
                search.clearFocus()
                true
            }
            container.isFocusableInTouchMode = true
            container.requestFocus()
            return
        }
        ui.heading(container, getString(destination.title)) { navigateBack() }
        var previousSection = 0
        val visible = rows.filter { it.page == destination }.let { entries ->
            if (destination == SettingsPage.APPEARANCE) entries.sortedBy { if (it.section == R.string.settings_section_appearance) 0 else 1 }
            else entries
        }
        visible.forEach { entry ->
            if (entry.section != previousSection) {
                ui.section(container, entry.section)
                previousSection = entry.section
            }
            container.addView(entry.view)
            ui.divider(container)
        }
        if (destination == SettingsPage.ADVANCED) {
            diagnosticsContribution = DiagnosticsSettingsProvider.contribute(this, container)
        }
        if (requestedRow != 0) container.post {
            visible.firstOrNull { it.title == requestedRow }?.view?.let { target ->
                shell.scroll.smoothScrollTo(0, (target.top - ui.dp(16)).coerceAtLeast(0))
                target.requestFocus()
            }
            requestedRow = 0
        }
    }

    private fun renderResults(results: LinearLayout) {
        results.removeAllViews()
        if (searchQuery.isBlank()) {
            var group = 0
            SettingsPage.entries.forEach { destination ->
                if (destination.group != group) { ui.section(results, destination.group); group = destination.group }
                val summary = if (destination == SettingsPage.LANGUAGES)
                    settings.enabledLanguages.joinToString(" · ") { it.compactLabel }
                    else getString(destination.summary)
                ui.row(results, getString(destination.title), summary, destination.icon) { openPage(destination) }
            }
            return
        }
        var count = 0
        SettingsPage.entries.filter { SettingsSearch.matches(searchQuery, getString(it.title), getString(it.summary)) }.forEach { destination ->
            ui.row(results, getString(destination.title), getString(destination.summary), destination.icon) { openPage(destination) }
            count++
        }
        rows.filter { entry ->
            SettingsSearch.matches(searchQuery, entry.view.findViewById<TextView>(R.id.row_title).text.toString(),
                entry.view.findViewById<TextView>(R.id.row_summary).text.toString())
        }.forEach { entry ->
            ui.row(results, entry.view.findViewById<TextView>(R.id.row_title).text.toString(), getString(entry.page.title), entry.page.icon) {
                openPage(entry.page, entry.title)
            }
            count++
        }
        if (count == 0) {
            results.addView(ui.text(getString(R.string.menu_empty), 18f).apply {
                setPadding(0, ui.dp(24), 0, ui.dp(10))
            })
            results.addView(ui.text(getString(R.string.menu_empty_hint), 14f, true))
        }
    }

    private fun keyboardThemeLabel(theme: KeyboardTheme): Int = when (theme) {
        KeyboardTheme.AIR -> R.string.keyboard_theme_air
        KeyboardTheme.SOFT -> R.string.keyboard_theme_soft
        KeyboardTheme.OUTLINE -> R.string.keyboard_theme_outline
        KeyboardTheme.MONOLITH -> R.string.keyboard_theme_monolith
        KeyboardTheme.SILENT -> R.string.keyboard_theme_silent
    }

    private fun addInfoRow(title: String, summary: String?) {
        val row = newRow(title, summary)
        row.isClickable = false
        row.foreground = null
        record(row, currentSection)
    }

    private fun addNavigationRow(titleRes: Int, summary: String?, onClick: () -> Unit) {
        val row = newRow(getString(titleRes), summary)
        row.setOnClickListener { onClick() }
        record(row, titleRes)
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
        record(row, titleRes)
    }

    private fun <T> addChoiceRow(
        titleRes: Int,
        values: List<T>,
        labels: List<String>,
        selected: T,
        summary: String? = null,
        onSelected: (T) -> Unit,
    ) {
        val selectedIndex = values.indexOf(selected).coerceAtLeast(0)
        val row = newRow(getString(titleRes), listOfNotNull(labels[selectedIndex], summary).joinToString("\n"))
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
        record(row, titleRes)
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

    private fun autocorrectionLabel(mode: AutocorrectionMode): Int = when (mode) {
        AutocorrectionMode.OFF -> R.string.smart_typing_off
        AutocorrectionMode.SUGGESTIONS -> R.string.smart_typing_suggestions
        AutocorrectionMode.HIGH_CONFIDENCE -> R.string.smart_typing_high_confidence
    }

    private fun contextualLabel(mode: ContextualPunctuationMode): Int = when (mode) {
        ContextualPunctuationMode.OFF -> R.string.smart_typing_off
        ContextualPunctuationMode.SUGGESTIONS -> R.string.smart_typing_suggestions
    }

    private fun autocorrectionSummary(): String {
        val summary = getString(when (settings.autocorrectionMode) {
            AutocorrectionMode.OFF -> R.string.settings_autocorrection_off_summary
            AutocorrectionMode.SUGGESTIONS -> R.string.settings_autocorrection_suggestions_summary
            AutocorrectionMode.HIGH_CONFIDENCE -> R.string.settings_autocorrection_high_confidence_summary
        })
        return if (settings.candidateStrip) summary
        else summary + "\n" + getString(R.string.settings_suggestions_hidden)
    }

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

private const val PERSONAL_PROFILE_REQUEST = 803
