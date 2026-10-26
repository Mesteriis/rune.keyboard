package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordContextPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenMorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenRareWordLexicon

internal data class WordContextFingerprint(val policyVersion: Int, val searchVersion: Int,
    val ruleIdentity: String, val morphologySha256: String, val rareWordsSha256: String, val lexiconSha256: String)

/** Finite reviewed rule, separate from statistical calibration. Changes require explicit review. */
internal object WordContextQualification {
    const val QUALIFIED = true
    fun fingerprint() = WordContextFingerprint(WordContextPolicy.VERSION, CandidateGenerator.SEARCH_VERSION,
        WordContextPolicy.RULE_IDENTITY, FrozenMorphologyLexicon.ASSET_SHA256, FrozenRareWordLexicon.ASSET_SHA256,
        QualificationArtifacts.compactPublic().lexicons[KeyboardLanguage.RUSSIAN].orEmpty())
    fun allows(f: WordContextFingerprint): Boolean = QUALIFIED && f == WordContextFingerprint(4, 1,
        "ru:нужен|новй|новый;встретимся|завтро|завтра;я уже|ддмой|домой:lowercase:whole-whitespace-suffix:v3",
        "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
        "434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e",
        "f08c2cccb75aeb1b7c80e0a06b5fc6befa8ed46e344004ed7bb1f63fc62ef632")
    fun enabled(language: KeyboardLanguage): Boolean = language == KeyboardLanguage.RUSSIAN && allows(fingerprint())
}
