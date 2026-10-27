package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import android.content.Context
import android.content.SharedPreferences
import android.os.Trace
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
import java.util.concurrent.atomic.AtomicBoolean
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.AndroidExperimentResources
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ExperimentModels
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionEvaluation
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlStore
import io.github.mesteriis.rune.keyboard.smarttyping.learning.LearningStore
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.PublicOriginalProtection
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutoCorrectionAdmissionGuard
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditCostProfile
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidMorphologyLexiconLoader
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidRareWordLexiconLoader
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingPersonalization
import io.github.mesteriis.rune.keyboard.smarttyping.session.AutomaticTypingDecision
import io.github.mesteriis.rune.keyboard.smarttyping.touch.TouchCalibrationStore

/** Shared dictionaries/stores; session eligibility remains owned by the IME, never by this singleton. */
class PersonalTypingResources private constructor(context: Context) {
    @Volatile var lexicon: MorphologyLexicon = MorphologyLexicon.UNAVAILABLE
        private set
    @Volatile var dictionaryLoaded = false
        private set
    @Volatile var rareWords: RareWordLexicon = RareWordLexicon.UNAVAILABLE
        private set
    val personal = PersonalTypingStore.get(context) { word, language -> lexicon.lookup(language, word).present }
    val touch = TouchCalibrationStore.get(context)
    val experiments: ExperimentModels = AndroidExperimentResources.get()
    val controls = TypingControlStore.get(context)
    val learning = LearningStore.get(context) { word, language -> lexicon.lookup(language, word).present }

    private val application = context.applicationContext
    private val preferences = KeyboardPreferences(application)
    private val russianStarted = AtomicBoolean(false)
    // Process singleton: keep this listener strongly referenced for its whole lifetime.
    private val languageListener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
        if (key == null || key == SettingsCodec.KEY_LANGUAGES_ENABLED) loadRussianIfEnabled()
    }

    init {
        preferences.registerListener(languageListener)
        loadRussianIfEnabled()
    }

    private fun loadRussianIfEnabled() {
        Trace.beginSection(SmartTypingTraceSection.RESOURCE_PREPARE.sectionName)
        try {
            if (KeyboardLanguage.RUSSIAN !in preferences.readSettings().enabledLanguages ||
                !russianStarted.compareAndSet(false, true)) return
            AndroidExperimentResources.loadRussian(application)
            val assets = application.assets
            Thread({
                Trace.beginSection(SmartTypingTraceSection.DICTIONARY_LOAD.sectionName)
                try {
                    lexicon = AndroidMorphologyLexiconLoader.load(assets)
                    rareWords = AndroidRareWordLexiconLoader.load(assets)
                    dictionaryLoaded = lexicon.lookup(KeyboardLanguage.RUSSIAN, "слово").available &&
                        rareWords.lookup("кармен").available
                    if (dictionaryLoaded) {
                        Trace.beginSection(SmartTypingTraceSection.DICTIONARY_READY.sectionName)
                        Trace.endSection()
                    }
                } finally {
                    Trace.endSection()
                }
            }, "rune-morphology-load").apply { isDaemon = true }.start()
        } finally {
            Trace.endSection()
        }
    }

    companion object {
        @Volatile private var instance: PersonalTypingResources? = null
        fun get(context: Context): PersonalTypingResources = instance ?: synchronized(this) {
            instance ?: PersonalTypingResources(context.applicationContext).also { instance = it }
        }
    }
}

/** Synchronous bounded decisions; stores do their disk work on their own worker threads. */
class AndroidTypingPersonalization(
    private val resources: PersonalTypingResources,
    private val onConfirmationFull: () -> Unit = {},
) : TypingPersonalization {
    var learningEnabled = false
    var touchEnabled = false
    var phrasesEnabled = false
    var protectionEnabled = false
    var learnedRankingEnabled = false
    var compactContextEnabled = false
    private var confirmationFullReported = false
    private val retypeDistance = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
    private val ready get() = learningEnabled && resources.personal.isReady

    private fun protectedOriginalRefusal(original: String, language: KeyboardLanguage) =
        PersonalAdmissionPolicy.protectedOriginalRefusal(protectionEnabled, resources.controls.isReady) {
            resources.controls.snapshot.contains(original, language)
        }

    override fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Boolean = automaticDecision(generation, candidate, language).allowed

    override fun automaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        protectedOriginalRefusal(generation.original.orEmpty(), language)?.let {
            return AutomaticTypingDecision(false, it)
        }
        val publicWord = PublicOriginalProtection.evaluate(generation, candidate, resources.rareWords)
        if (!publicWord.allowed) return AutomaticTypingDecision(false, publicWord.refusal)
        val admission = AutoCorrectionAdmissionGuard(resources.lexicon).evaluate(generation, candidate)
        if (!admission.allowed) return AutomaticTypingDecision(false, admission.refusal)
        val original = generation.original
            ?: return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val refusal = PersonalAdmissionPolicy.personalRefusal(ready, resources.personal.model,
            original, candidate.text, language)
        return AutomaticTypingDecision(refusal == null, refusal)
    }

    override fun refinementDecision(generation: CandidateGeneration, word: String,
        language: KeyboardLanguage, comparedWords: List<String>): AutomaticTypingDecision =
        refinementDecision(generation, word, language, comparedWords, jointWinner = false)

    private fun refinementDecision(generation: CandidateGeneration, word: String,
        language: KeyboardLanguage, comparedWords: List<String>, jointWinner: Boolean,
        rescueWinner: Boolean = false, wordContextWinner: Boolean = false): AutomaticTypingDecision {
        val original = generation.original ?: return AutomaticTypingDecision(false)
        protectedOriginalRefusal(original, language)?.let { return AutomaticTypingDecision(false, it) }
        PersonalAdmissionPolicy.personalRefusal(ready, resources.personal.model, original, word, language)?.let {
            return AutomaticTypingDecision(false, it)
        }
        if (word == original) return AutomaticTypingDecision(true)
        val all = (generation.alternatives + generation.compactAlternatives + generation.neighborRecovery.alternatives)
            .distinctBy { it.canonicalKey }
        val candidate = all.firstOrNull { it.text == word } ?: return AutomaticTypingDecision(false)
        val publicWord = PublicOriginalProtection.evaluate(generation, candidate, resources.rareWords)
        if (!publicWord.allowed) return AutomaticTypingDecision(false, publicWord.refusal)
        val guard = AutoCorrectionAdmissionGuard(resources.lexicon)
        val decision = if (wordContextWinner) guard.evaluateWordContext(generation, candidate)
        else if (rescueWinner) guard.evaluateRescue(generation, candidate)
        else if (jointWinner) guard.evaluateJoint(generation, candidate,
            io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification
                .uniqueAmbiguousWinnerEnabled(language, original.length))
        else guard.evaluateRefinement(generation.copy(alternatives = all), candidate, comparedWords)
        return AutomaticTypingDecision(decision.allowed, decision.refusal)
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
        return base + neural + resources.learning.preference(original, candidate.text, language) +
            PublicOriginalProtection.manualPreference(original, candidate, resources.lexicon, resources.rareWords)
    }

    override fun abstainingJointPreference(context: String, original: String, candidate: GeneratedCandidate,
        language: KeyboardLanguage): Double = if (original.length in 5..32 &&
        io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification.enabled(language) &&
        resources.experiments.rescueReady && resources.experiments.contextReady)
        resources.experiments.rescueScore(context, original, candidate).takeIf(Double::isFinite) ?: 0.0
        else 0.0

    override fun awaitingJointCandidates(generation: CandidateGeneration, language: KeyboardLanguage): Boolean =
        jointReady(generation, language) && !generation.jointEvaluated

    private fun jointReady(generation: CandidateGeneration, language: KeyboardLanguage): Boolean =
        io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification.enabled(
            language, generation.original?.length ?: 0) && resources.dictionaryLoaded &&
            resources.experiments.jointReady && resources.experiments.contextReady

    override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, baselineWord: String?):
        JointCorrectionChoice? = jointAutomaticEvaluation(context, generation, language, baselineWord).choice

    override fun jointAutomaticEvaluation(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, baselineWord: String?): JointCorrectionEvaluation {
        val baseline = legacyJointAutomaticEvaluation(context, generation, language, baselineWord)
        if (!resources.experiments.contextualReady || !jointReady(generation, language) ||
            resources.rareWords.lookup(generation.original.orEmpty()).present ||
            resources.lexicon.lookup(language, generation.original.orEmpty()).present) return baseline
        val contextual = io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualCorrectionPolicy.evaluate(
            resources.experiments, context, generation, language, baseline, baselineWord) { candidate ->
            val decision = contextualAutomaticDecision(generation, candidate, language)
            if (decision.allowed) null else decision.refusal ?: AutomaticAdmissionRefusal.NOT_QUALIFIED
        }
        val infinitive = io.github.mesteriis.rune.keyboard.smarttyping.experiments.InfinitiveRevisionPolicy.evaluate(
            resources.experiments, context, generation, language, contextual, baselineWord, resources.lexicon) { candidate ->
            val decision = grammarRevisionAutomaticDecision(generation, candidate, language)
            if (decision.allowed) null else decision.refusal ?: AutomaticAdmissionRefusal.NOT_QUALIFIED
        }
        return io.github.mesteriis.rune.keyboard.smarttyping.experiments.NounCaseRevisionPolicy.evaluate(
            resources.experiments, context, generation, language, infinitive, baselineWord, resources.lexicon) { candidate ->
            val decision = nounCaseAutomaticDecision(generation, candidate, language)
            if (decision.allowed) null else decision.refusal ?: AutomaticAdmissionRefusal.NOT_QUALIFIED
        }
    }

    override fun nounCaseAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (!resources.experiments.nounCaseReady ||
            !io.github.mesteriis.rune.keyboard.smarttyping.correction.NounCaseRevisionQualification.enabled(
                language, generation.original?.length ?: 0))
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return jointAutomaticDecision(generation, candidate, language)
    }

    override fun grammarRevisionAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (!resources.experiments.grammarRevisionReady ||
            !io.github.mesteriis.rune.keyboard.smarttyping.correction.InfinitiveRevisionQualification.enabled(
                language, generation.original?.length ?: 0))
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return jointAutomaticDecision(generation, candidate, language)
    }

    override fun contextualAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (!resources.experiments.contextualReady ||
            !io.github.mesteriis.rune.keyboard.smarttyping.correction.ContextualQualification.enabled(
                language, generation.original?.length ?: 0))
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return jointAutomaticDecision(generation, candidate, language)
    }

    private fun legacyJointAutomaticEvaluation(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, baselineWord: String?): JointCorrectionEvaluation {
        if (!io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification.enabled(
                language, generation.original?.length ?: 0))
            return JointCorrectionEvaluation(refusal = JointCorrectionRefusal.NOT_QUALIFIED)
        if (!jointReady(generation, language))
            return JointCorrectionEvaluation(refusal = JointCorrectionRefusal.RESOURCE_UNAVAILABLE)
        if (!generation.jointEvaluated)
            return JointCorrectionEvaluation(refusal = JointCorrectionRefusal.RESULT_NOT_READY)
        val source = generation.original.orEmpty()
        if (resources.rareWords.lookup(source).present)
            return JointCorrectionEvaluation(refusal = JointCorrectionRefusal.RARE_ORIGINAL)
        if (resources.lexicon.lookup(language, source).present)
            return JointCorrectionEvaluation(refusal = JointCorrectionRefusal.ORIGINAL_VALID)
        if (!generation.jointSearch.isComplete)
            return JointCorrectionEvaluation(refusal = JointCorrectionRefusal.SEARCH_INCOMPLETE)
        fun withWordContext(primary: JointCorrectionEvaluation): JointCorrectionEvaluation {
            // An explicit joint abstention vetoes the raw legacy proposal. Preserve only a legacy
            // replacement that would still be applied when no joint decision was returned.
            if (!io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordContextPolicy.maySupplement(primary.choice, baselineWord) ||
                !io.github.mesteriis.rune.keyboard.smarttyping.correction.WordContextQualification.enabled(language)) return primary
            val evaluated = io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordContextPolicy.evaluate(
                context, generation, language)
            val proposal = evaluated.choice?.candidate ?: return primary.copy(wordContextAttempted = true,
                wordContextRefusal = evaluated.refusal)
            val admitted = wordContextAutomaticDecision(generation, proposal, language)
            if (!admitted.allowed) return primary.copy(wordContextAttempted = true,
                wordContextAdmissionRefusal = admitted.refusal ?: AutomaticAdmissionRefusal.NOT_QUALIFIED)
            return primary.copy(choice = JointCorrectionChoice(proposal, wordContext = true), wordContextAttempted = true)
        }
        val evaluation = io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionPolicy.evaluate(
            resources.experiments, context, generation, language,
            io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification.thresholds, baselineWord)
        val choice = evaluation.choice ?: JointCorrectionChoice(null)
        var primary = evaluation.copy(choice = choice)
        if (choice.candidate != null) {
            val admission = jointAutomaticDecision(generation, choice.candidate, language)
            if (!admission.allowed) primary = JointCorrectionEvaluation(admissionRefusal = admission.refusal
                ?: AutomaticAdmissionRefusal.NOT_QUALIFIED)
        }
        if (primary.choice?.candidate != null || baselineWord != null || source.length !in 5..32 ||
            !io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification.enabled(language)) return withWordContext(primary)
        val rescueEvaluation = io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointRescuePolicy.evaluate(
            resources.experiments, context, generation, language)
        val rescue = rescueEvaluation.choice?.candidate ?: return withWordContext(primary.copy(
            rescueAttempted = true, rescueRefusal = rescueEvaluation.refusal))
        val admission = rescueAutomaticDecision(generation, rescue, language)
        if (!admission.allowed) return withWordContext(primary.copy(rescueAttempted = true,
            rescueAdmissionRefusal = admission.refusal ?: AutomaticAdmissionRefusal.NOT_QUALIFIED))
        return primary.copy(choice = JointCorrectionChoice(rescue, rescue = true), rescueAttempted = true)
    }

    override fun wordContextAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (!io.github.mesteriis.rune.keyboard.smarttyping.correction.WordContextQualification.enabled(language) ||
            !jointReady(generation, language) ||
            candidate !in generation.jointSearch.alternatives)
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return refinementDecision(generation.copy(alternatives = generation.jointSearch.alternatives),
            candidate.text, language, emptyList(), jointWinner = false, wordContextWinner = true)
    }

    override fun rescueAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (!io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification.enabled(language) ||
            !resources.experiments.rescueReady || !jointReady(generation, language) ||
            candidate !in generation.jointSearch.alternatives)
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return refinementDecision(generation.copy(alternatives = generation.jointSearch.alternatives),
            candidate.text, language, emptyList(), jointWinner = false, rescueWinner = true)
    }

    override fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (!jointReady(generation, language) || !generation.jointEvaluated || !generation.jointSearch.isComplete ||
            candidate !in generation.jointSearch.alternatives) return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        return refinementDecision(generation.copy(alternatives = generation.jointSearch.alternatives), candidate.text,
            language, listOf(generation.original.orEmpty()) + generation.jointSearch.alternatives.map { it.text }, jointWinner = true)
    }

    override fun recoveryAutomaticCandidate(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): GeneratedCandidate? {
        if (!resources.dictionaryLoaded || language != KeyboardLanguage.RUSSIAN) return null
        return resources.experiments.recoveryAutomaticCandidate(context, generation, language)
    }

    override fun recoveryAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (language != KeyboardLanguage.RUSSIAN || !generation.neighborRecovery.isComplete ||
            generation.neighborRecovery.alternatives.none { it == candidate })
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val original = generation.original ?: return AutomaticTypingDecision(false)
        val rare = resources.rareWords.lookup(io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode.folded(original))
        if (!rare.available || rare.present) return AutomaticTypingDecision(false,
            if (rare.present) AutomaticAdmissionRefusal.ORIGINAL_VALID else AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
        return refinementDecision(generation, candidate.text, language, emptyList())
    }

    override fun compactAutomaticCandidate(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): GeneratedCandidate? {
        if (!resources.dictionaryLoaded || language != KeyboardLanguage.RUSSIAN) return null
        val source = generation.original?.let(io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode::folded)
            ?: return null
        val morphology = resources.lexicon.lookup(language, source)
        val rare = resources.rareWords.lookup(source)
        if (!morphology.available || !rare.available || morphology.present || rare.present) return null
        return resources.experiments.compactAutomaticCandidate(context, generation, language)
    }

    override fun compactAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
        language: KeyboardLanguage): AutomaticTypingDecision {
        if (language != KeyboardLanguage.RUSSIAN || !resources.dictionaryLoaded ||
            generation.compactAlternatives.none { it.canonicalKey == candidate.canonicalKey })
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val source = generation.original?.let(io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode::folded)
            ?: return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val morphology = resources.lexicon.lookup(language, source)
        val rare = resources.rareWords.lookup(source)
        if (!morphology.available || !rare.available)
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
        if (morphology.present || rare.present)
            return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.ORIGINAL_VALID)
        if (candidate.kind == io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind.PUBLIC_AUGMENTED) {
            val targetMorphology = resources.lexicon.lookup(language, candidate.terminalKey)
            val targetRare = resources.rareWords.lookup(candidate.terminalKey)
            if (!targetMorphology.available || !targetRare.available ||
                (!targetMorphology.present && !targetRare.present))
                return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        }
        protectedOriginalRefusal(generation.original.orEmpty(), language)?.let {
            return AutomaticTypingDecision(false, it)
        }
        val original = generation.original
            ?: return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
        val refusal = PersonalAdmissionPolicy.personalRefusal(ready, resources.personal.model,
            original, candidate.text, language)
        return AutomaticTypingDecision(refusal == null, refusal)
    }

    override fun accepted(original: String, replacement: String, language: KeyboardLanguage) {
        resources.learning.accepted(original, replacement, language)
        if (ready) resources.personal.update { model ->
            confirmWithCapacityNotice(model, replacement, language) { model.recordAccepted(original, replacement, language) }
        }
        confirmTouch(original, replacement)
    }

    override fun rejected(original: String, replacement: String, language: KeyboardLanguage) {
        resources.learning.rejected(original, replacement, language)
        if (ready) resources.personal.update { it.recordRejected(original, replacement, language) }
        clearPending()
    }

    override fun confirmed(word: String, language: KeyboardLanguage) {
        resources.learning.confirmed(word, language)
        if (ready) resources.personal.update { model ->
            confirmWithCapacityNotice(model, word, language) { model.recordConfirmedWord(word, language) }
        }
        confirmTouch(word, word)
    }

    /** One notice per full-table episode, never from rendering or ordinary phrase observations. */
    private fun confirmWithCapacityNotice(model: PersonalTypingModel, word: String, language: KeyboardLanguage,
        change: () -> Unit) {
        if (model.snapshot().confirmed.size < PersonalTypingModel.MAX_CONFIRMED) confirmationFullReported = false
        change()
        if (!confirmationFullReported && PersonalTypingModel.normalizeWord(word) != null &&
            !model.protectsOriginal(word, language) && model.snapshot().confirmed.size >= PersonalTypingModel.MAX_CONFIRMED) {
            confirmationFullReported = true
            onConfirmationFull()
        }
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
                confirmWithCapacityNotice(model, word, language) {
                    model.recordManualRetype(retypedFrom, word, language)
                }
            }
            model.recordPhrase(prefix, word, language)
        }
    }

    override fun continuations(context: String, language: KeyboardLanguage): List<String> =
        if (phrasesEnabled && resources.personal.isReady) resources.personal.model.suggestions(context, language).map { it.text }
        else emptyList()

    override fun clearPending() { resources.touch.model.clearPending() }
}
