package io.github.mesteriis.rune.keyboard.smarttyping.controls

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import java.text.Normalizer
import java.util.Locale

/** Profile IDs are fixed diagnostic values; do not reorder. Presets only restrict global settings. */
enum class TypingProfile(val code: Int) {
    DEFAULT(0), CONVERSATION(1), FORMAL(2);

    fun apply(settings: KeyboardSettings): KeyboardSettings = when (this) {
        DEFAULT -> settings
        CONVERSATION -> settings.copy(
            autocorrectionMode = if (settings.autocorrectionMode == AutocorrectionMode.HIGH_CONFIDENCE)
                AutocorrectionMode.SUGGESTIONS else settings.autocorrectionMode,
            mechanicalPunctuation = false, doubleSpacePeriod = false, contextualPunctuationMode = ContextualPunctuationMode.OFF,
            phraseReview = false,
        )
        FORMAL -> settings.copy(phraseSuggestions = false, abbreviations = false)
    }
}

data class ProtectedWord(val language: KeyboardLanguage, val word: String) {
    override fun toString() = "ProtectedWord($language,[redacted])"
}
data class AppProfileBinding(val packageName: String, val profile: TypingProfile) {
    override fun toString() = "AppProfileBinding([redacted],$profile)"
}
data class TypingControlSnapshot(
    val words: List<ProtectedWord> = emptyList(), val apps: List<AppProfileBinding> = emptyList(),
) {
    fun contains(word: String, language: KeyboardLanguage): Boolean =
        TypingControlModel.normalize(word)?.let { key -> words.any { it.language == language && it.word == key } } == true
    fun profile(packageName: String?): TypingProfile = apps.firstOrNull { it.packageName == packageName }?.profile ?: TypingProfile.DEFAULT
    override fun toString() = "TypingControlSnapshot(words=${words.size},apps=${apps.size})"
}

object TypingControlModel {
    const val MAX_WORDS = 1024
    const val MAX_APPS = 64
    const val MAX_WORD_CODE_POINTS = 48
    private val packagePattern = Regex("[A-Za-z][A-Za-z0-9_]*(?:\\.[A-Za-z][A-Za-z0-9_]*)+")
    fun validPackage(value: String) = value.length in 3..255 && packagePattern.matches(value)
    fun normalize(word: String): String? {
        if (word.isEmpty() || word.length > MAX_WORD_CODE_POINTS * 2) return null
        val value = Normalizer.normalize(word, Normalizer.Form.NFC).lowercase(Locale.ROOT)
        val points = value.codePoints().toArray()
        if (points.size !in 1..MAX_WORD_CODE_POINTS || !Character.isLetter(points.first()) ||
            !Character.isLetter(points.last()) || points.any {
                !Character.isLetter(it) && Character.getType(it) != Character.NON_SPACING_MARK.toInt() &&
                    it != '-'.code && it != '\''.code && it != '’'.code
            }) return null
        return value
    }
    fun validate(snapshot: TypingControlSnapshot) {
        require(snapshot.words.size <= MAX_WORDS && snapshot.apps.size <= MAX_APPS)
        require(snapshot.words.distinct().size == snapshot.words.size)
        require(snapshot.apps.map { it.packageName }.distinct().size == snapshot.apps.size)
        require(snapshot.words.all { normalize(it.word) == it.word })
        require(snapshot.apps.all { validPackage(it.packageName) })
    }
    fun addWord(snapshot: TypingControlSnapshot, word: String, language: KeyboardLanguage): TypingControlSnapshot? {
        val entry = ProtectedWord(language, normalize(word) ?: return null)
        if (entry in snapshot.words) return snapshot
        if (snapshot.words.size >= MAX_WORDS) return null
        return snapshot.copy(words = snapshot.words + entry)
    }
    fun observePackage(snapshot: TypingControlSnapshot, packageName: String): TypingControlSnapshot? {
        if (!validPackage(packageName)) return null
        if (snapshot.apps.any { it.packageName == packageName }) return snapshot
        val retained = if (snapshot.apps.size == MAX_APPS) {
            val removable = snapshot.apps.firstOrNull { it.profile == TypingProfile.DEFAULT } ?: return null
            snapshot.apps - removable
        } else snapshot.apps
        return snapshot.copy(apps = retained + AppProfileBinding(packageName, TypingProfile.DEFAULT))
    }
    fun assign(snapshot: TypingControlSnapshot, packageName: String, profile: TypingProfile): TypingControlSnapshot? {
        if (!snapshot.apps.any { it.packageName == packageName }) return null
        return snapshot.copy(apps = snapshot.apps.map { if (it.packageName == packageName) it.copy(profile = profile) else it })
    }
}

/** Missing/unreadable assignments cannot temporarily enable edits that a saved profile forbids. */
object TypingProfileResolver {
    fun resolve(settings: KeyboardSettings, packageName: String?, snapshot: TypingControlSnapshot?): Pair<TypingProfile, KeyboardSettings> {
        if (!settings.appProfiles) return TypingProfile.DEFAULT to settings
        if (snapshot == null) return TypingProfile.DEFAULT to settings.copy(
            autocorrectionMode = AutocorrectionMode.OFF, mechanicalPunctuation = false, doubleSpacePeriod = false,
            contextualPunctuationMode = ContextualPunctuationMode.OFF, phraseReview = false,
            phraseSuggestions = false, abbreviations = false,
        )
        val profile = snapshot.profile(packageName)
        return profile to profile.apply(settings)
    }
}
