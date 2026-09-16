package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import android.content.Context
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.AndroidExperimentResources
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ExperimentModels
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlStore
import io.github.mesteriis.rune.keyboard.smarttyping.learning.LearningStore
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutoCorrectionAdmissionGuard
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditCostProfile
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidMorphologyLexiconLoader
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingPersonalization
import io.github.mesteriis.rune.keyboard.smarttyping.session.AutomaticTypingDecision
import io.github.mesteriis.rune.keyboard.smarttyping.touch.TouchCalibrationStore

/** Shared dictionaries/stores; session eligibility remains owned by the IME, never by this singleton. */
class PersonalTypingResources private constructor(context: Context) {
    @Volatile var lexicon: MorphologyLexicon = MorphologyLexicon.UNAVAILABLE
        private set
    @Volatile var dictionaryLoaded = false
        private set
    val personal = PersonalTypingStore.get(context) { word, language -> lexicon.lookup(language, word).present }
    val touch = TouchCalibrationStore.get(context)
    val experiments: ExperimentModels = AndroidExperimentResources.get(context)
    val controls = TypingControlStore.get(context)
    val learning = LearningStore.get(context) { word, language -> lexicon.lookup(language, word).present }

    init {
        val assets = context.applicationContext.assets
        Thread({
            lexicon = AndroidMorphologyLexiconLoader.load(assets)
            dictionaryLoaded = lexicon.lookup(KeyboardLanguage.RUSSIAN, "слово").available
        }, "rune-morphology-load").apply { isDaemon = true }.start()
    }

    companion object {
        @Volatile private var instance: PersonalTypingResources? = null
        fun get(context: Context): PersonalTypingResources = instance ?: synchronized(this) {
            instance ?: PersonalTypingResources(context.applicationContext).also { instance = it }
        }
    }
}

/** Synchronous bounded decisions; stores do their disk work on their own worker threads. */
class AndroidTypingPersonalization(private val resources: PersonalTypingResources) : TypingPersonalization {
    var learningEnabled = false
    var touchEnabled = false
    var phrasesEnabled = false
    var protectionEnabled = false
    var learnedRankingEnabled = false
    var compactContextEnabled = false
    private val retypeDistance = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
    private val ready get() = learningEnabled && resources.personal.isReady

    override fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Boolean = automaticDecision(generation, candidate, language).allowed

    override fun automaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (protectionEnabled && (!resources.controls.isReady ||
            resources.controls.snapshot.contains(generation.original.orEmpty(), language))) {
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        }
        val admission = AutoCorrectionAdmissionGuard(resources.lexicon).evaluate(generation, candidate)
        if (!admission.allowed) return AutomaticTypingDecision(false, admission.refusal)
        val original = generation.original
            ?: return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val allowed = !ready || (!resources.personal.model.protectsOriginal(original, language) &&
            !resources.personal.model.rejects(original, candidate.text, language))
        return AutomaticTypingDecision(allowed,
            if (allowed) null else AutomaticAdmissionRefusal.NOT_QUALIFIED)
    }

    override fun preference(original: String, candidate: String, language: KeyboardLanguage): Double =
        (if (ready) resources.personal.model.preference(original, candidate, language).toDouble() else 0.0) +
            (if (touchEnabled && resources.touch.isReady) resources.touch.model.candidateBonus(original, candidate) else 0.0) +
            resources.learning.preference(original, candidate, language)

    override fun contextualPreference(context: String, original: String, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Double {
        val personal = if (ready) resources.personal.model.preference(original, candidate.text, language).toDouble() else 0.0
        val touch = if (touchEnabled && resources.touch.isReady)
            resources.touch.model.candidateBonus(original, candidate.text) else 0.0
        val base = if (learnedRankingEnabled && resources.experiments.learnedReady && resources.experiments.supports(language))
            resources.experiments.rankScore(context, original, candidate, personal, touch) else personal + touch
        val neural = if (compactContextEnabled) resources.experiments.contextScore(context, candidate.text, language) else 0.0
        return base + neural + resources.learning.preference(original, candidate.text, language)
    }

    override fun accepted(original: String, replacement: String, language: KeyboardLanguage) {
        resources.learning.accepted(original, replacement, language)
        if (ready) resources.personal.update { it.recordAccepted(original, replacement, language) }
        confirmTouch(original, replacement)
    }

    override fun rejected(original: String, replacement: String, language: KeyboardLanguage) {
        resources.learning.rejected(original, replacement, language)
        if (ready) resources.personal.update { it.recordRejected(original, replacement, language) }
        clearPending()
    }

    override fun confirmed(word: String, language: KeyboardLanguage) {
        resources.learning.confirmed(word, language)
        if (ready) resources.personal.update { it.recordConfirmedWord(word, language) }
        confirmTouch(word, word)
    }

    private fun confirmTouch(original: String, replacement: String) {
        if (touchEnabled && resources.touch.isReady && resources.touch.model.confirmWord(original, replacement)) {
            resources.touch.scheduleSave()
        }
        clearPending()
    }

    override fun committed(prefix: String, word: String, retypedFrom: String?, language: KeyboardLanguage) {
        if (retypedFrom != null) resources.learning.manualRetype(retypedFrom, word, language)
        if (!ready) return
        resources.personal.update { model ->
            if (retypedFrom != null && retypedFrom.length in 3..48 && word.length in 3..48 &&
                resources.lexicon.lookup(language, word).present &&
                retypeDistance.features(retypedFrom, word, language).editCost in 0.25..2.0) {
                model.recordManualRetype(retypedFrom, word, language)
            }
            model.recordPhrase(prefix, word, language)
        }
    }

    override fun continuations(context: String, language: KeyboardLanguage): List<String> =
        if (phrasesEnabled && resources.personal.isReady) resources.personal.model.suggestions(context, language).map { it.text }
        else emptyList()

    override fun clearPending() { resources.touch.model.clearPending() }
}
