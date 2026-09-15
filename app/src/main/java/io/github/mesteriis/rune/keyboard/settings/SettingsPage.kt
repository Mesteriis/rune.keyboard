package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.R
import java.text.Normalizer
import java.util.Locale

/** Stable destinations shared by quick links, the settings directory and search. */
enum class SettingsPage(val title: Int, val summary: Int, val icon: Int, val group: Int) {
    APPEARANCE(R.string.menu_appearance, R.string.menu_appearance_summary, R.drawable.ic_menu_palette, R.string.menu_keyboard_group),
    LANGUAGES(R.string.menu_languages, R.string.settings_languages_row, R.drawable.ic_menu_language, R.string.menu_keyboard_group),
    FEEDBACK(R.string.menu_feedback, R.string.menu_feedback_summary, R.drawable.ic_menu_volume, R.string.menu_keyboard_group),
    TYPING(R.string.menu_typing, R.string.menu_typing_summary, R.drawable.ic_menu_typing, R.string.menu_input_group),
    DICTIONARY(R.string.menu_dictionary, R.string.menu_dictionary_summary, R.drawable.ic_menu_book, R.string.menu_input_group),
    MODEL(R.string.menu_model, R.string.menu_model_summary, R.drawable.ic_menu_model, R.string.menu_input_group),
    PRIVACY(R.string.menu_privacy, R.string.menu_privacy_summary, R.drawable.ic_menu_privacy, R.string.menu_app_group),
    ADVANCED(R.string.menu_advanced, R.string.menu_advanced_summary, R.drawable.ic_menu_info, R.string.menu_app_group);

    companion object {
        fun fromName(name: String?): SettingsPage? = entries.firstOrNull { it.name == name }

        fun forRow(section: Int, title: Int): SettingsPage = when (title) {
            R.string.settings_local_intelligence -> MODEL
            R.string.settings_key_preview -> APPEARANCE
            R.string.settings_word_boundaries, R.string.settings_phrase_review,
            R.string.settings_visible_undo, R.string.settings_manual_candidate_expansion -> TYPING
            R.string.settings_abbreviations, R.string.abbreviations_title,
            R.string.settings_protected_words, R.string.controls_words_title,
            R.string.settings_collect_examples, R.string.settings_learned_ranking,
            R.string.settings_compact_context, R.string.settings_dynamic_touch,
            R.string.settings_dynamic_touch_apply, R.string.settings_typo_patterns,
            R.string.learning_title -> DICTIONARY
            else -> when (section) {
                R.string.settings_section_languages -> LANGUAGES
                R.string.settings_section_smart_typing -> TYPING
                R.string.settings_section_personal -> DICTIONARY
                R.string.settings_section_typing, R.string.settings_section_layout,
                R.string.settings_section_appearance -> APPEARANCE
                R.string.settings_section_feedback -> FEEDBACK
                R.string.settings_section_privacy -> PRIVACY
                else -> ADVANCED
            }
        }
    }
}

internal object SettingsSearch {
    fun matches(query: String, vararg labels: String): Boolean {
        val words = normalize(query).split(Regex("\\s+")).filter(String::isNotEmpty)
        val target = normalize(labels.joinToString(" "))
        return words.all { it in target }
    }
    private fun normalize(value: String): String = Normalizer.normalize(value.lowercase(Locale.ROOT).replace('ё', 'е'), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")
}
