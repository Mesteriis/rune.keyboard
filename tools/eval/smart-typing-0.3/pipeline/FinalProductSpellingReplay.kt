package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.PublicOriginalProtection
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutoCorrectionAdmissionGuard
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionDecision
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointRescuePolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordContextPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WordContextQualification
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionThresholds
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionChoice
import io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingSource
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryThresholds
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ExperimentModels
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenExperimentAssets
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import java.security.MessageDigest
import java.text.BreakIterator
import java.util.Base64
import java.util.Locale

/** Developer-only observer. Expected text, labels and corpus cohorts never enter this process. */
object FinalProductSpellingReplay {
    private class AdmissionPersonalization(private val guard: AutoCorrectionAdmissionGuard,
        private val morphology: MorphologyLexicon, private val rareWords: RareWordLexicon,
        private val experiments: ExperimentModels,
        private val jointThresholds: JointCorrectionThresholds? = null,
        private val productionJoint: Boolean = false,
        private val rescueEnabled: Boolean = false, private val wordContextEnabled: Boolean = false,
        private val contextualEnabled: Boolean = false) : TypingPersonalization {
        var decision: AutomaticTypingDecision? = null
            private set
        var candidate: String? = null
            private set

        fun reset() { decision = null; candidate = null }

        override fun awaitingJointCandidates(generation: CandidateGeneration, language: KeyboardLanguage): Boolean =
            jointThresholds != null && (!productionJoint || JointQualification.enabled(language, generation.original?.length ?: 0)) &&
                experiments.jointReady && experiments.contextReady && !generation.jointEvaluated

        override fun jointAutomaticEvaluation(context: String, generation: CandidateGeneration,
            language: KeyboardLanguage, baselineWord: String?): io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionEvaluation {
            val baseline = io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionEvaluation(
                jointAutomaticChoice(context, generation, language, baselineWord))
            if (!contextualEnabled || morphology.lookup(language, generation.original.orEmpty()).present ||
                rareWords.lookup(generation.original.orEmpty()).present) return baseline
            return io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualCorrectionPolicy.evaluate(
                experiments, context, generation, language, baseline, baselineWord) { candidate ->
                val decision = contextualAutomaticDecision(generation, candidate, language)
                if (decision.allowed) null else decision.refusal ?: AutomaticAdmissionRefusal.NOT_QUALIFIED
            }
        }

        override fun contextualAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): AutomaticTypingDecision {
            if (!contextualEnabled || !experiments.contextualReady ||
                !io.github.mesteriis.rune.keyboard.smarttyping.correction.ContextualQualification.enabled(
                    language, generation.original?.length ?: 0))
                return AutomaticTypingDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
            return jointAutomaticDecision(generation, candidate, language)
        }

        override fun jointAutomaticChoice(context: String, generation: CandidateGeneration,
            language: KeyboardLanguage, baselineWord: String?): JointCorrectionChoice? {
            val thresholds = jointThresholds ?: return null
            if (productionJoint && !JointQualification.enabled(language, generation.original?.length ?: 0)) return null
            if (!generation.jointSearch.isComplete || !generation.jointEvaluated ||
                generation.alternatives.any { it.kind == GeneratedCandidateKind.COMMON_CONFUSION }) return null
            fun withWordContext(primary: JointCorrectionChoice?): JointCorrectionChoice? {
                if (!WordContextPolicy.maySupplement(primary, baselineWord) || !wordContextEnabled) return primary
                val evaluated = WordContextPolicy.evaluate(context, generation, language)
                val proposal = evaluated.choice?.candidate ?: return primary
                return if (wordContextAutomaticDecision(generation, proposal, language).allowed)
                    JointCorrectionChoice(proposal, wordContext = true) else primary
            }
            val choice = JointCorrectionPolicy.select(experiments, context, generation, language, thresholds, baselineWord)
                ?: JointCorrectionChoice(null)
            val primary = if (choice.candidate != null &&
                !jointAutomaticDecision(generation, choice.candidate, language).allowed) null else choice
            if (primary?.candidate != null || baselineWord != null || !rescueEnabled) return withWordContext(primary)
            val rescue = JointRescuePolicy.select(experiments, context, generation, language) ?: return withWordContext(primary)
            return if (rescueAutomaticDecision(generation, rescue, language).allowed)
                JointCorrectionChoice(rescue, rescue = true) else withWordContext(primary)
        }

        override fun contextualPreference(context: String, original: String, candidate: GeneratedCandidate,
            language: KeyboardLanguage): Double =
            PublicOriginalProtection.manualPreference(original, candidate, morphology, rareWords)

        override fun abstainingJointPreference(context: String, original: String, candidate: GeneratedCandidate,
            language: KeyboardLanguage): Double = if (rescueEnabled && original.length in 5..32 && experiments.rescueReady)
            experiments.rescueScore(context, original, candidate).takeIf(Double::isFinite) ?: 0.0 else 0.0

        override fun wordContextAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): AutomaticTypingDecision {
            val publicWord = PublicOriginalProtection.evaluate(generation, candidate, rareWords)
            val evaluated = if (wordContextEnabled && publicWord.allowed)
                guard.evaluateWordContext(generation, candidate) else if (!publicWord.allowed) publicWord
                else AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
            return AutomaticTypingDecision(evaluated.allowed, evaluated.refusal)
                .also { decision = it; this.candidate = candidate.terminalKey }
        }

        override fun rescueAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): AutomaticTypingDecision {
            val publicWord = PublicOriginalProtection.evaluate(generation, candidate, rareWords)
            val evaluated = if (rescueEnabled && publicWord.allowed) guard.evaluateRescue(generation, candidate)
                else if (!publicWord.allowed) publicWord
                else AutomaticAdmissionDecision(false, AutomaticAdmissionRefusal.NOT_QUALIFIED)
            return AutomaticTypingDecision(evaluated.allowed, evaluated.refusal)
                .also { decision = it; this.candidate = candidate.terminalKey }
        }

        override fun jointAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): AutomaticTypingDecision {
            if (productionJoint && !JointQualification.enabled(language, generation.original?.length ?: 0))
                return AutomaticTypingDecision(false)
            if (!generation.jointEvaluated || !generation.jointSearch.isComplete ||
                candidate !in generation.jointSearch.alternatives) return AutomaticTypingDecision(false)
            val publicWord = PublicOriginalProtection.evaluate(generation, candidate, rareWords)
            val evaluated = if (publicWord.allowed) guard.evaluateJoint(generation, candidate,
                JointQualification.uniqueAmbiguousWinnerEnabled(language, generation.original?.length ?: 0)) else publicWord
            return AutomaticTypingDecision(evaluated.allowed, evaluated.refusal)
                .also { decision = it; this.candidate = candidate.terminalKey }
        }

        override fun allowsAutomatic(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): Boolean = guard.allows(generation, candidate)

        override fun automaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): AutomaticTypingDecision {
            val publicWord = PublicOriginalProtection.evaluate(generation, candidate, rareWords)
            val evaluated = if (publicWord.allowed) guard.evaluate(generation, candidate) else publicWord
            this.candidate = candidate.terminalKey
            return AutomaticTypingDecision(evaluated.allowed, evaluated.refusal).also { decision = it }
        }

        override fun recoveryAutomaticCandidate(context: String, generation: CandidateGeneration,
            language: KeyboardLanguage): GeneratedCandidate? = experiments.recoveryAutomaticCandidate(context, generation, language)

        override fun recoveryAutomaticDecision(generation: CandidateGeneration, candidate: GeneratedCandidate,
            language: KeyboardLanguage): AutomaticTypingDecision {
            val source = generation.original?.let(TokenUnicode::folded) ?: return AutomaticTypingDecision(false)
            val rare = rareWords.lookup(source)
            if (!rare.available || rare.present || !generation.neighborRecovery.isComplete ||
                candidate !in generation.neighborRecovery.alternatives) return AutomaticTypingDecision(false)
            return refinementDecision(generation, candidate.text, language, emptyList())
                .also { decision = it; this.candidate = candidate.terminalKey }
        }

        override fun refinementDecision(generation: CandidateGeneration, word: String,
            language: KeyboardLanguage, comparedWords: List<String>): AutomaticTypingDecision {
            if (word == generation.original) return AutomaticTypingDecision(true)
            val all = (generation.alternatives + generation.compactAlternatives + generation.neighborRecovery.alternatives)
                .distinctBy { it.canonicalKey }
            val candidate = all.firstOrNull { it.text == word } ?: return AutomaticTypingDecision(false)
            val publicWord = PublicOriginalProtection.evaluate(generation, candidate, rareWords)
            val evaluated = if (publicWord.allowed)
                guard.evaluateRefinement(generation.copy(alternatives = all), candidate, comparedWords) else publicWord
            return AutomaticTypingDecision(evaluated.allowed, evaluated.refusal)
        }

        override fun compactAutomaticCandidate(context: String, generation: CandidateGeneration,
            language: KeyboardLanguage): GeneratedCandidate? {
            val source = generation.original?.let(TokenUnicode::folded) ?: return null
            val morph = morphology.lookup(language, source); val rare = rareWords.lookup(source)
            if (!morph.available || !rare.available || morph.present || rare.present) return null
            return experiments.compactAutomaticCandidate(context, generation, language)
        }

        override fun compactAutomaticDecision(generation: CandidateGeneration,
            candidate: GeneratedCandidate, language: KeyboardLanguage): AutomaticTypingDecision {
            val source = generation.original?.let(TokenUnicode::folded)
                ?: return AutomaticTypingDecision(false, io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal.NOT_QUALIFIED)
            val morph = morphology.lookup(language, source); val rare = rareWords.lookup(source)
            val allowed = morph.available && rare.available && !morph.present && !rare.present &&
                generation.compactAlternatives.any { it.canonicalKey == candidate.canonicalKey }
            return AutomaticTypingDecision(allowed,
                if (allowed) null else io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal.NOT_QUALIFIED)
                .also { decision = it; this.candidate = candidate.terminalKey }
        }
    }

    private fun json(value: Any?): String = when (value) {
        null -> "null"
        is String -> buildString {
            append('"')
            value.forEach { c -> when(c) {
                '"' -> append("\\\""); '\\' -> append("\\\\")
                '\n' -> append("\\n"); '\r' -> append("\\r"); '\t' -> append("\\t")
                else -> if (c.code < 32) append("\\u%04x".format(c.code)) else append(c)
            } }
            append('"')
        }
        is Boolean, is Number -> value.toString()
        is Map<*, *> -> value.entries.joinToString(",", "{", "}") { json(it.key.toString()) + ":" + json(it.value) }
        is Iterable<*> -> value.joinToString(",", "[", "]") { json(it) }
        else -> error("UNSUPPORTED_JSON_TYPE")
    }

    /** In-memory editor derived only from TypingEdit commands. */
    private class Editor {
        var text = ""; private set
        var caret = 0; private set
        var composingStart = -1; private set
        var composingEnd = -1; private set
        val commands = mutableListOf<Map<String, Any?>>()
        fun execute(edit: TypingEdit): Boolean {
            when (edit) {
                is TypingEdit.Batch -> {
                    commands.add(mapOf("type" to "Batch", "count" to edit.edits.size))
                    for (item in edit.edits) if (!edit.isCurrent() || !execute(item)) return false
                }
                is TypingEdit.SetComposingText -> replace(edit.value, true)
                is TypingEdit.CommitText -> replace(edit.value, false)
                TypingEdit.FinishComposingText -> {
                    commands.add(mapOf("type" to "FinishComposingText")); composingStart = -1; composingEnd = -1
                }
                is TypingEdit.SetComposingRegion -> {
                    check(edit.start >= 0 && edit.end <= text.length && edit.end > edit.start)
                    commands.add(mapOf("type" to "SetComposingRegion", "start" to edit.start, "end" to edit.end))
                    composingStart = edit.start; composingEnd = edit.end
                }
            }
            return true
        }
        private fun replace(value: String, composing: Boolean) {
            val start = if (composingStart >= 0) composingStart else caret
            val end = if (composingStart >= 0) composingEnd else caret
            commands.add(mapOf("type" to if (composing) "SetComposingText" else "CommitText",
                "value" to value, "replacedStart" to start, "replacedEnd" to end))
            text = text.substring(0, start) + value + text.substring(end)
            caret = start + value.length
            composingStart = if (composing && value.isNotEmpty()) start else -1
            composingEnd = if (composing && value.isNotEmpty()) caret else -1
        }
        fun snapshot() = mapOf("text" to text, "caret" to caret,
            "composingStart" to composingStart, "composingEnd" to composingEnd)
    }

    private val graphemes = GraphemeSegmenter { text ->
        val iterator = BreakIterator.getCharacterInstance(Locale.ROOT).apply { setText(text) }
        buildList { var boundary = iterator.first(); while (boundary != BreakIterator.DONE) {
            add(boundary); boundary = iterator.next()
        } }
    }

    private fun item(candidate: GeneratedCandidate) = mapOf(
        "text" to candidate.text, "canonicalKey" to candidate.canonicalKey,
        "terminalKey" to candidate.terminalKey, "language" to candidate.language.locale.language,
        "isFallback" to candidate.isFallback, "languagePrior" to candidate.languagePrior,
        "frequencyRank" to candidate.frequencyRank, "unitDistance" to candidate.unitDistance,
        "editCost" to candidate.editFeatures.editCost,
        "repeatedCharacterEdits" to candidate.editFeatures.repeatedCharacterEdits,
        "repetitionBonus" to candidate.editFeatures.repetitionBonus,
        "lengthDifference" to candidate.lengthDifference, "casePattern" to candidate.casePattern.name,
        "kind" to candidate.kind.name, "canonicalCaseUnambiguous" to candidate.canonicalCaseUnambiguous,
        "canonicalCaseAutoEligible" to candidate.canonicalCaseAutoEligible)

    private fun candidate(generation: CandidateGeneration) = mapOf(
        "original" to generation.original, "completion" to generation.completion.name,
        "isValidWord" to generation.isValidWord,
        "prohibitsAutoReplace" to generation.prohibitsAutoReplace,
        "protectedReason" to generation.protectedReason?.name,
        "inspectedStates" to generation.inspectedStates,
        "verifiedTerminals" to generation.verifiedTerminals,
        "alternatives" to generation.alternatives.map(::item),
        "localSearch" to mapOf("completion" to generation.localSearch.completion.name,
            "inspectedStates" to generation.localSearch.inspectedStates,
            "verifiedTerminals" to generation.localSearch.verifiedTerminals,
            "alternatives" to generation.localSearch.alternatives.map(::item)),
        "compactAlternatives" to generation.compactAlternatives.map(::item),
        "neighborRecovery" to mapOf("completion" to generation.neighborRecovery.completion.name,
            "inspectedStates" to generation.neighborRecovery.inspectedStates,
            "verifiedTerminals" to generation.neighborRecovery.verifiedTerminals,
            "alternatives" to generation.neighborRecovery.alternatives.map(::item)))

    private fun state(controller: TypingSessionController) = mapOf(
        "enabled" to controller.state.enabled, "sessionId" to controller.state.sessionId,
        "revision" to controller.state.revision, "contextText" to controller.state.contextText,
        "composingText" to controller.state.composing?.text,
        "typedWord" to controller.state.composing?.typedWord,
        "leadingBoundary" to controller.state.composing?.leadingBoundary,
        "originalSelected" to controller.state.originalSelected,
        "canRequestCandidates" to controller.canRequestCandidates,
        "canRequestModelRanking" to controller.canRequestModelRanking)

    private fun executorSelfCheck() {
        val editor = Editor()
        check(editor.execute(TypingEdit.SetComposingText("ab")) && editor.text == "ab")
        check(editor.execute(TypingEdit.SetComposingText("abc")) && editor.text == "abc")
        check(editor.execute(TypingEdit.CommitText("Cat ")) && editor.text == "Cat ")
        check(editor.execute(TypingEdit.SetComposingRegion(3, 4)))
        check(editor.execute(TypingEdit.SetComposingText(" dog")) && editor.text == "Cat dog")
        check(editor.execute(TypingEdit.FinishComposingText))
        check(editor.execute(TypingEdit.CommitText("!")) && editor.text == "Cat dog!")
        check(!editor.execute(TypingEdit.Batch(listOf(TypingEdit.CommitText("bad"))) { false }))
        check(editor.text == "Cat dog!")
        System.err.println("INDEPENDENT_EDITOR_SELF_CHECK_PASS")
    }

    private data class Delivery(val id: String, val split: String, val language: String,
        val sessionId: Long, val revision: Long, val requestId: Long, val prefix: String,
        val candidateIds: List<Int>, val continuations: List<String>, val code: String,
        val scores: List<NumericScore>)

    @JvmStatic fun main(args: Array<String>) {
        check(args.size in 4..5)
        val mode = args[2]
        check(mode in setOf("export", "ready", "unavailable", "recovery", "joint-export", "joint-ready", "joint-production", "contextual-production", "joint-rescue-ready", "joint-primary-only", "word-context-ready", "word-context-baseline", "refinement-export", "refinement-ready"))
        val productionMode = mode in setOf("joint-production", "contextual-production", "joint-rescue-ready",
            "joint-primary-only", "word-context-ready", "word-context-baseline")
        val jointPipelineMode = productionMode || mode == "joint-ready" || mode == "joint-export"
        val targetSplit = args[3]
        check(targetSplit in setOf("all", "calibration", "holdout"))
        check((mode in setOf("ready", "refinement-ready", "joint-ready")) == (args.size == 5))
        val jointConfig = if (mode == "joint-ready") File(args[4]).readText().trim().split('	').also { check(it.size == 6 || it.size == 8) } else null
        val jointThresholds = if (productionMode) JointQualification.thresholds else jointConfig?.let { JointCorrectionThresholds(
            RecoveryThresholds(it[2].toDouble(), it[3].toDouble()), RecoveryThresholds(it[4].toDouble(), it[5].toDouble()),
            if (it.size == 8) RecoveryThresholds(it[6].toDouble(), it[7].toDouble()) else RecoveryThresholds(it[4].toDouble(), it[5].toDouble())) }
        executorSelfCheck()
        val deliveries = mutableMapOf<String, Delivery>()
        if (mode in setOf("ready", "refinement-ready")) File(args[4]).useLines { lines -> lines.forEach { line ->
            val fields = line.split('\t'); check(fields.size == 11)
            val id = String(Base64.getDecoder().decode(fields[0]), Charsets.UTF_8)
            val candidateIds = fields[7].split(',').map(String::toInt)
            val continuations = fields[8].split(',').map {
                String(Base64.getDecoder().decode(it), Charsets.UTF_8)
            }
            val scores = if (fields[10] == "NONE") emptyList() else fields[10].split(';').map { encoded ->
                val pieces = encoded.split(','); check(pieces.size == 3)
                NumericScore(pieces[0].toInt(), pieces[1].toDouble(), pieces[2].toInt())
            }
            val delivery = Delivery(id, fields[1], fields[2], fields[3].toLong(), fields[4].toLong(),
                fields[5].toLong(), String(Base64.getDecoder().decode(fields[6]), Charsets.UTF_8),
                candidateIds, continuations, fields[9], scores)
            check(deliveries.put(id, delivery) == null) { "DUPLICATE_DELIVERY_ID" }
        } }
        val consumedDeliveries = mutableSetOf<String>()
        var hadError = false
        val assets = File(args[1])
        fun mapping(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
            it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
        }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN,
            FrozenPackedLexicons.SPANISH).map { trust ->
            val language = trust.language.locale.language
            val load = PackedLexiconData.validate(trust,
                mapping(File(assets, "smarttyping/lexicon/$language.trie")),
                mapping(File(assets, "smarttyping/lexicon/$language.trie.lengths")),
                mapping(File(assets, "smarttyping/lexicon/frequency/$language.ranks")))
            check(load is PackedLexiconLoad.Ready) { "PACKED_ASSET_NOT_READY:$language" }; load.lexicon
        }
        val cases = KeyboardLanguage.entries.associateWith { language ->
            val trust = FrozenCanonicalCaseLexicons.forLanguage(language)
            val bytes = File(assets, trust.path).readBytes()
            val digest = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            check(bytes.size.toLong() == trust.bytes && digest == trust.sha256) { "CASE_HASH" }
            CanonicalCaseData.validate(bytes)
        }
        val morphologyFile = File(assets, FrozenMorphologyLexicon.ASSET_PATH)
        check(morphologyFile.length() == FrozenMorphologyLexicon.ASSET_BYTES) { "MORPHOLOGY_SIZE" }
        val morphology = PackedMorphologyLexicon.open(
            mapping(morphologyFile), FrozenMorphologyLexicon.ASSET_SHA256)
        check(morphology.lookup(KeyboardLanguage.RUSSIAN, "слово").available) { "MORPHOLOGY_NOT_READY" }
        val rareFile = File(assets, FrozenRareWordLexicon.ASSET_PATH)
        check(rareFile.length() == FrozenRareWordLexicon.ASSET_BYTES) { "RARE_WORDS_SIZE" }
        val rareWords = PackedRareWordLexicon.open(mapping(rareFile), FrozenRareWordLexicon.ASSET_SHA256)
        check(rareWords.lookup("кармен").available) { "RARE_WORDS_NOT_READY" }
        val generator = CandidateGenerator(PackedCandidateLexicon(handles),
            CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
            CanonicalCaseLexicon { language, key -> cases.getValue(language).lookup(key) },
            morphology, rareWords)
        val admissionGuard = AutoCorrectionAdmissionGuard(morphology)
        fun experimentAsset(name: String, size: Int, expectedHash: String): ByteArray {
            val bytes = File(assets, "smarttyping/experiments/$name").readBytes()
            val actualHash = MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it) }
            check(bytes.size == size && actualHash == expectedHash) { "EXPERIMENT_ASSET_IDENTITY:$name" }
            return bytes
        }
        val experiments = ExperimentModels().apply {
            if (productionMode) loadJointRanker(experimentAsset("ru-joint-ranker.bin",
                JointQualification.RANKER_BYTES, JointQualification.RANKER_SHA256))
            if (productionMode) loadRescueRanker(experimentAsset("ru-joint-rescue-ranker.bin",
                JointRescueQualification.RANKER_BYTES, JointRescueQualification.RANKER_SHA256))
            if (jointConfig != null) {
                val model = File(jointConfig[0]); check(model.length() in 20..65536)
                val bytes = model.readBytes()
                check(MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) } == jointConfig[1])
                loadJointRanker(bytes)
            }
            loadRanker(experimentAsset("ru-ranker.bin", FrozenExperimentAssets.RANK_BYTES,
                FrozenExperimentAssets.RANK_SHA256))
            loadLegacyAutomaticRanker(experimentAsset("ru-ranker-auto-v1.bin",
                FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_BYTES,
                FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_SHA256))
            loadRecoveryRanker(experimentAsset("ru-neighbor-ranker.bin",
                io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification.RANKER_BYTES,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification.RANKER_SHA256))

            loadContext(experimentAsset("ru-ranking-context.bin", FrozenExperimentAssets.RANKING_CONTEXT_BYTES,
                FrozenExperimentAssets.RANKING_CONTEXT_SHA256))
        }
        if (mode == "contextual-production") {
            val frozen = io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenContextualAssets
            fun mapped(name: String, size: Long): java.nio.ByteBuffer {
                val file = File(assets, "smarttyping/experiments/$name"); check(file.length() == size)
                return FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
                    it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
                }
            }
            experimentAsset("ru-contextual-policy.json", frozen.POLICY_BYTES, frozen.POLICY_SHA256)
            val wiki = io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordPairFeatures.open(
                mapped("ru-wiki.ctx", frozen.WIKI_BYTES), frozen.WIKI_SHA256)!!
            val conversation = io.github.mesteriis.rune.keyboard.smarttyping.experiments.WordPairFeatures.open(
                mapped("ru-conversation.ctx", frozen.CONVERSATION_BYTES), frozen.CONVERSATION_SHA256)!!
            val grammar = io.github.mesteriis.rune.keyboard.smarttyping.experiments.GrammarFeatureDictionary.open(
                mapped("ru-context.gram", frozen.GRAMMAR_BYTES), frozen.GRAMMAR_SHA256)!!
            experiments.loadContextualRanker(io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualRanker.create(
                experimentAsset("ru-contextual-ranker.bin", frozen.MODEL_BYTES, frozen.MODEL_SHA256), wiki, conversation, grammar)!!)
            check(experiments.contextualReady)
        }
        check(experiments.learnedReady && experiments.legacyAutomaticReady && experiments.contextReady) {
            "COMPACT_MODELS_NOT_READY"
        }
        val personalization = AdmissionPersonalization(admissionGuard, morphology, rareWords, experiments, jointThresholds, productionMode,
            mode == "joint-rescue-ready" || mode in setOf("joint-production", "contextual-production", "word-context-ready", "word-context-baseline") && JointRescueQualification.QUALIFIED,
            mode == "word-context-ready" || mode in setOf("joint-production", "contextual-production") && WordContextQualification.enabled(KeyboardLanguage.RUSSIAN),
            mode == "contextual-production")
        System.err.println("ALL_14_PACKAGED_LEXICON_MORPHOLOGY_AND_RARE_ASSETS_VALIDATED")
        System.err.println("COMPACT_RANKER_AND_CONTEXT_ASSETS_VALIDATED")
        val settings = KeyboardSettings.DEFAULT
        File(args[0]).useLines { lines -> lines.forEachIndexed { index, line ->
            val fields = line.split('\t'); check(fields.size == 6 && fields[0].toInt() == index)
            fun decoded(i: Int) = String(Base64.getDecoder().decode(fields[i]), Charsets.UTF_8)
            val id = decoded(1); val split = fields[2]
            if (targetSplit != "all" && split != targetSplit) return@forEachIndexed
            val language = KeyboardLanguage.entries.single { it.locale.language == fields[3] }
            val prefix = decoded(4); val typed = decoded(5)
            val keyboard = KeyboardState(language)
            val editorContext = EditorContext.from(1, 0)
            val policy = MechanicalPunctuationPolicy(editorContext.inputPolicy, editorContext.mode,
                editorContext.requiresRawKeyEvents, settings.mechanicalPunctuation, settings.doubleSpacePeriod)
            val controller = if (mode == "word-context-ready") TypingSessionController(graphemes,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification { lang, source ->
                    source == SpellingSource.WORD_CONTEXT ||
                        io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification.CURRENT.allows(lang, source)
                }) else if (mode == "joint-rescue-ready") TypingSessionController(graphemes,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification { lang, source ->
                    source == SpellingSource.JOINT_RESCUE ||
                        io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification.CURRENT.allows(lang, source)
                }) else if (mode == "joint-ready") TypingSessionController(graphemes,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification { lang, source ->
                    source in setOf(SpellingSource.JOINT_SHORT, SpellingSource.JOINT_LONG) ||
                        io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification.CURRENT.allows(lang, source)
                }) else if (mode.startsWith("refinement")) TypingSessionController(graphemes,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification { lang, source ->
                    source in setOf(io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingSource.NEIGHBOR_RECOVERY,
                        io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingSource.MODEL_REFINEMENT) ||
                        io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification.CURRENT.allows(lang, source)
                }, refinementThresholds = if (mode == "refinement-ready")
                    io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification.refinement else
                    io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryThresholds(-1000.0, 0.000001))
                else TypingSessionController(graphemes)
            val editor = Editor()
            personalization.reset()
            controller.setPersonalization(personalization, language)
            controller.startSession(editorContext, 0, 0)
            if (mode.startsWith("refinement")) controller.configureFeatures(
                io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature.VISIBLE_UNDO.bit,
                io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature.VISIBLE_UNDO.bit)
            val result = linkedMapOf<String, Any?>("index" to index, "id" to id, "split" to split,
                "language" to language.locale.language, "prefix" to prefix, "typed" to typed,
                "maximumAlternatives" to CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
                "morphologyAdmission" to true,
                "autocorrectionMode" to settings.autocorrectionMode.name,
                "currentQualificationWithoutModel" to controller.isSpellingQualified(language, false),
                "currentQualificationWithModel" to controller.isSpellingQualified(language, true))
            try {
                fun ack() {
                    check(!controller.updateSelection(editor.caret, editor.caret, editor.composingStart,
                        editor.composingEnd, editor::execute)) { "UNATTRIBUTED_SELECTION" }
                    check(editor.text.endsWith(controller.state.contextText)) { "CONTEXT_EDITOR_DIVERGENCE" }
                }
                fun type(value: String): TypingTextResult {
                    val response = controller.typeText(value, policy, keyboard, false,
                        settings.autocorrectionMode, editor::execute)
                    check(response == TypingTextResult.HANDLED) { "INPUT_$response" }; ack(); return response
                }
                val fullInput = (if (prefix.isNotEmpty()) "$prefix " else "") + typed
                fullInput.codePoints().forEach { type(String(Character.toChars(it))) }
                result["inputExpected"] = fullInput; result["beforeBoundary"] = editor.snapshot()
                result["stateBeforeCandidates"] = state(controller)
                result["inputChangedByTyping"] = editor.text != fullInput
                result["typingCommands"] = editor.commands.toList()
                val generationStarted = System.nanoTime()
                val baselineGeneration = generator.generate(typed, language)
                val baselineFinished = System.nanoTime()
                val recovered = if (mode == "recovery" || jointPipelineMode || mode.startsWith("refinement")) generator.generateRecovery(typed, language, baselineGeneration) else baselineGeneration
                val recoveryFinished = System.nanoTime()
                val fullGeneration = if (mode == "joint-ready" ||
                    productionMode && JointQualification.enabled(language, typed.length)) recovered.copy(
                    jointSearch = generator.generateJointPool(typed, language, recovered), jointEvaluated = true) else recovered
                val jointFinished = System.nanoTime()
                val stageTimings = linkedMapOf(
                    "baselineSearch" to baselineFinished - generationStarted,
                    "recoverySearch" to recoveryFinished - baselineFinished,
                    "jointSearch" to jointFinished - recoveryFinished)
                result["hostStageNanos"] = stageTimings
                if (mode == "recovery") {
                    val all = (fullGeneration.alternatives + fullGeneration.compactAlternatives + fullGeneration.neighborRecovery.alternatives).distinctBy { it.canonicalKey }
                    val sourceRare = rareWords.lookup(TokenUnicode.folded(typed))
                    result["recoveryAdmission"] = fullGeneration.neighborRecovery.alternatives.associate { candidate ->
                        candidate.text to (sourceRare.available && !sourceRare.present &&
                            admissionGuard.evaluate(fullGeneration.copy(alternatives = all, localSearch = LocalSearchEvidence.NONE), candidate).allowed)
                    }
                }
                result["fullTokenGenerationNanos"] = System.nanoTime() - generationStarted
                result["fullTokenGeneration"] = candidate(fullGeneration)
                if ((mode == "joint-ready" || productionMode)) {
                    val ownedPrefix = (if (prefix.isNotEmpty()) "$prefix " else "").takeLast(128)
                    result["jointModelScores"] = listOf(experiments.jointOriginalScore(ownedPrefix, typed)) +
                        fullGeneration.jointSearch.alternatives.map { experiments.jointScore(ownedPrefix, typed, it) }
                    result["jointSearch"] = mapOf("completion" to fullGeneration.jointSearch.completion.name,
                        "alternatives" to fullGeneration.jointSearch.alternatives.map(::item))
                    result["jointTargetKnown"] = fullGeneration.jointSearch.alternatives.associate { proposal ->
                        proposal.canonicalKey to morphology.lookup(language, proposal.terminalKey).present
                    }
                }
                if (mode == "joint-export") {
                    val joint = generator.generateJointPool(typed, language, fullGeneration)
                    val compared = (listOf(typed) + joint.alternatives.map { it.text }).distinct()
                    result["jointSearch"] = mapOf("completion" to joint.completion.name,
                        "alternatives" to joint.alternatives.map(::item))
                    result["jointAdmission"] = joint.alternatives.associate { proposal ->
                        val publicWord = PublicOriginalProtection.evaluate(fullGeneration, proposal, rareWords)
                        proposal.text to (publicWord.allowed && admissionGuard.evaluateRefinement(
                            fullGeneration.copy(alternatives = joint.alternatives), proposal, compared).allowed)
                    }
                }
                if (experiments.rescueReady) {
                    val ownedPrefix = (if (prefix.isNotEmpty()) "$prefix " else "").takeLast(128)
                    result["rescueModelScores"] = listOf(experiments.rescueOriginalScore(ownedPrefix, typed)) +
                        fullGeneration.jointSearch.alternatives.map { experiments.rescueScore(ownedPrefix, typed, it) }
                }
                // Match the worker's separate manual reply; it never supplies automatic evidence.
                val manualStarted = System.nanoTime()
                val manualSearch = generator.generateManualPool(typed, language, baselineGeneration, enabled = true)
                stageTimings["manualSearch"] = System.nanoTime() - manualStarted
                result["manualSearchGeneration"] = manualSearch?.let(::candidate)
                val localDecision = LocalCorrectionPolicy.decide(fullGeneration, language)?.canonicalKey
                result["localDecision"] = localDecision
                result["compactPolicyCandidate"] = experiments.compactAutomaticCandidate(
                    prefix, fullGeneration, language)?.terminalKey
                val sourceMorphology = if (language == KeyboardLanguage.RUSSIAN)
                    morphology.lookup(language, TokenUnicode.folded(typed)) else null
                result["compactSourceMorphology"] = sourceMorphology?.let {
                    mapOf("available" to it.available, "present" to it.present)
                }
                val compactCandidates = if (language == KeyboardLanguage.RUSSIAN && localDecision == null &&
                    !fullGeneration.isValidWord && fullGeneration.protectedReason == null &&
                    fullGeneration.localSearch.completion == CandidateCompletion.COMPLETE)
                    fullGeneration.localSearch.alternatives else emptyList()
                result["compactScores"] = compactCandidates.map { scored ->
                    val rankerScore = experiments.rankScore(prefix, typed, scored)
                    val contextScore = experiments.contextScore(prefix, scored.text, language)
                    val admission = admissionGuard.evaluate(fullGeneration, scored)
                    mapOf("text" to scored.text, "canonicalKey" to scored.canonicalKey,
                        "terminalKey" to scored.terminalKey, "rankerScore" to rankerScore,
                        "contextScore" to contextScore, "combinedScore" to rankerScore + contextScore,
                        "strictAdmissionAllowed" to admission.allowed,
                        "strictAdmissionRefusal" to admission.refusal?.name)
                }
                val localRequest = controller.beginCandidateRequest(index.toLong() + 1, language)
                result["requestToken"] = localRequest?.token
                val stagedMode = (mode == "joint-ready" || productionMode)
                val actualBaseline = localRequest?.let {
                    if (it.token == typed) baselineGeneration else generator.generate(it.token, language)
                }
                val generation = localRequest?.let {
                    if (it.token == typed) fullGeneration else if (stagedMode) {
                        val recoveredActual = generator.generateRecovery(it.token, language, actualBaseline!!)
                        if (mode == "joint-ready" || JointQualification.enabled(language, it.token.length))
                            recoveredActual.copy(jointSearch = generator.generateJointPool(it.token, language, recoveredActual),
                                jointEvaluated = true) else recoveredActual
                    } else actualBaseline!!
                }
                val actualManual = localRequest?.let {
                    if (it.token == typed) manualSearch else
                        generator.generateManualPool(it.token, language, actualBaseline!!, enabled = true)
                }
                result["actualRequestGeneration"] = generation?.let(::candidate)
                result["actualOriginal"] = generation?.original ?: controller.state.composing?.typedWord
                val rankingStarted = System.nanoTime()
                result["candidatesAccepted"] = if (localRequest != null) {
                    val staged = stagedMode
                    val accepted = controller.acceptCandidates(LocalCandidateReply(localRequest.sessionId, localRequest.revision,
                        localRequest.requestId, if (staged) actualBaseline!! else generation!!,
                        manualGeneration = actualManual, isFinal = !staged))
                    if (staged && accepted) controller.acceptRecoveryCandidates(LocalCandidateReply(localRequest.sessionId,
                        localRequest.revision, localRequest.requestId, generation!!, manualGeneration = actualManual,
                        stage = CandidateStage.RECOVERY)) else accepted
                } else null
                stageTimings["controllerCandidateRanking"] = System.nanoTime() - rankingStarted
                val modelRequest = if (mode.startsWith("refinement")) null else controller.beginModelRanking(index.toLong() + 1)
                result["actualModelRequest"] = modelRequest?.let { mapOf(
                    "sessionId" to it.token.sessionId, "revision" to it.token.revision,
                    "requestId" to it.token.requestId, "prefix" to it.prefix,
                    "candidateIds" to it.token.candidateIds, "continuations" to it.continuations) }
                if (mode == "export") {
                    result["status"] = "EXPORTED"; println(json(result))
                    if ((index + 1) % 500 == 0) System.err.println("ROWS_COMPLETED:${index + 1}")
                    return@forEachIndexed
                }
                result["modelAdmission"] = if (modelRequest == null) {
                    if (!mode.startsWith("refinement")) check(deliveries[id] == null) { "DELIVERY_FOR_NO_REQUEST" }; "NO_CURRENT_MODEL_REQUEST"
                } else if (mode == "unavailable" || mode == "recovery" || jointPipelineMode) {
                    result["modelReplyAccepted"] = controller.acceptModelRanking(ScoringReply(
                        modelRequest.token, ScoringCode.UNAVAILABLE, 0, emptyList()))
                    "EXPLICIT_MODEL_UNAVAILABLE"
                } else {
                    val delivery = deliveries[id] ?: error("MISSING_READY_DELIVERY")
                    check(delivery.id == id && delivery.split == split &&
                        delivery.language == language.locale.language &&
                        delivery.sessionId == modelRequest.token.sessionId &&
                        delivery.revision == modelRequest.token.revision &&
                        delivery.requestId == modelRequest.token.requestId) { "DELIVERY_IDENTITY_MISMATCH" }
                    check(delivery.prefix == modelRequest.prefix &&
                        delivery.candidateIds == modelRequest.token.candidateIds &&
                        delivery.continuations == modelRequest.continuations) { "DELIVERY_PAYLOAD_MISMATCH" }
                    check(consumedDeliveries.add(id)) { "DELIVERY_REUSED" }
                    if (delivery.code == "UNAVAILABLE") {
                        check(delivery.scores.isEmpty())
                        result["modelReplyAccepted"] = controller.acceptModelRanking(ScoringReply(
                            modelRequest.token, ScoringCode.UNAVAILABLE, 0, emptyList()))
                        "MATCHED_SCORING_ERROR"
                    } else {
                        check(delivery.code == "OK")
                        result["modelReplyAccepted"] = controller.acceptModelRanking(ScoringReply(
                            modelRequest.token, ScoringCode.OK, 0, delivery.scores))
                        "MATCHED_NUMERIC_REPLY"
                    }
                }
                result["stateBeforeBoundary"] = state(controller)
                result["candidateView"] = mapOf("enabled" to controller.candidateViewState.enabled,
                    "selectedCandidateId" to controller.candidateViewState.selectedCandidateId,
                    "candidates" to controller.candidateViewState.candidates.map {
                        mapOf("id" to it.id, "text" to it.text, "role" to when (it) {
                            is CandidateUiItem.Original -> "ORIGINAL"
                            is CandidateUiItem.Correction -> "CORRECTION"
                            is CandidateUiItem.Punctuation -> "PUNCTUATION"
                            is CandidateUiItem.Continuation -> "CONTINUATION"
                            is CandidateUiItem.Tool -> "TOOL"
                            is CandidateUiItem.Undo -> "UNDO"
                        }) })
                val beforeBoundaryText = editor.text; editor.commands.clear()
                val boundaryStarted = System.nanoTime()
                result["boundaryResult"] = type(" ").name
                stageTimings["spaceBoundary"] = System.nanoTime() - boundaryStarted
                result["afterBoundary"] = editor.snapshot()
                result["automaticAdmissionAllowed"] = personalization.decision?.allowed
                result["automaticAdmissionRefusal"] = personalization.decision?.refusal?.name
                result["automaticAdmissionCandidate"] = personalization.candidate
                result["boundaryCommands"] = editor.commands.toList()
                result["boundaryChangedBeyondInsertedSpace"] = editor.text != beforeBoundaryText + " "
                result["stateAfterBoundary"] = state(controller)
                result["autoEdit"] = controller.state.lastAutoEdit?.let { mapOf(
                    "original" to it.original, "applied" to it.applied,
                    "committedStart" to it.committedStart, "contextBefore" to it.contextBefore,
                    "restoreComposition" to it.restoreComposition.text,
                    "hasCorrectionCandidates" to (it.correction != null),
                    "correctionGeneration" to it.correction?.generation?.let(::candidate)) }
                if (mode.startsWith("refinement")) {
                    val refinement = controller.beginPreviousWordRefinement(index.toLong() + 1)
                    result["refinementRequest"] = refinement?.let { mapOf("sessionId" to it.token.sessionId,
                        "revision" to it.token.revision, "requestId" to it.token.requestId, "prefix" to it.prefix,
                        "candidateIds" to it.token.candidateIds, "continuations" to it.continuations) }
                    val correction = controller.state.lastAutoEdit?.correction
                    result["refinementAdmission"] = if (refinement != null && correction != null)
                        refinement.continuations.associateWith { personalization.refinementDecision(correction.generation,
                            it, language, refinement.continuations).allowed } else emptyMap<String, Boolean>()
                    if (mode == "refinement-ready" && refinement != null) {
                        val delivery = deliveries[id] ?: error("MISSING_REFINEMENT_DELIVERY")
                        check(delivery.prefix == refinement.prefix && delivery.continuations == refinement.continuations &&
                            delivery.candidateIds == refinement.token.candidateIds && delivery.sessionId == refinement.token.sessionId &&
                            delivery.revision == refinement.token.revision && delivery.requestId == refinement.token.requestId)
                        consumedDeliveries.add(id)
                        type("след")
                        result["refinementAccepted"] = controller.acceptPreviousWordRefinement(ScoringReply(refinement.token,
                            if (delivery.code == "OK") ScoringCode.OK else ScoringCode.UNAVAILABLE, 0, delivery.scores), editor::execute)
                        ack()
                        result["afterRefinement"] = editor.snapshot()
                        check(editor.text.endsWith(" след") && controller.state.composing?.text == " след")
                        val rootUndo = controller.candidateViewState.candidates.filterIsInstance<CandidateUiItem.Undo>().single()
                        check(controller.selectCandidate(rootUndo.id, editor::execute) == TypingTextResult.HANDLED)
                        ack()
                        result["afterRootUndo"] = editor.snapshot()
                        check(editor.text == beforeBoundaryText + " след") { "ROOT_UNDO_DIVERGENCE" }
                        check(controller.candidateViewState.candidates.none { it is CandidateUiItem.Undo })
                    }
                }
                editor.commands.clear(); val undo = controller.deletePrevious(editor::execute)
                result["backspaceResult"] = undo.name; if (undo == TypingTextResult.HANDLED) ack()
                result["afterBackspace"] = editor.snapshot(); result["backspaceCommands"] = editor.commands.toList()
                result["restoredBeforeBoundaryExactly"] = editor.text == beforeBoundaryText
                result["stateAfterBackspace"] = state(controller); result["status"] = "COMPLETE"
            } catch (error: Exception) {
                hadError = true
                result["status"] = "ERROR"; result["error"] = error.javaClass.name + ":" + error.message
                result["editorAtFailure"] = editor.snapshot(); result["stateAtFailure"] = state(controller)
                result["commandsAtFailure"] = editor.commands.toList(); error.printStackTrace(System.err)
            }
            println(json(result)); if ((index + 1) % 500 == 0) System.err.println("ROWS_COMPLETED:${index + 1}")
        } }
        if (mode in setOf("ready", "refinement-ready")) check(consumedDeliveries == deliveries.keys) { "UNCONSUMED_OR_FOREIGN_DELIVERY" }
        check(!hadError) { "ROW_ERRORS" }
    }
}
