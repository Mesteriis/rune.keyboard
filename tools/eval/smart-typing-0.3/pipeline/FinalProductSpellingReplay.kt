package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
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
            "alternatives" to generation.localSearch.alternatives.map(::item)))

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
        check(mode in setOf("export", "ready", "unavailable"))
        val targetSplit = args[3]
        check(targetSplit in setOf("all", "calibration", "holdout"))
        check((mode == "ready") == (args.size == 5))
        executorSelfCheck()
        val deliveries = mutableMapOf<String, Delivery>()
        if (mode == "ready") File(args[4]).useLines { lines -> lines.forEach { line ->
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
        val generator = CandidateGenerator(PackedCandidateLexicon(handles),
            CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
            CanonicalCaseLexicon { language, key -> cases.getValue(language).lookup(key) })
        System.err.println("ALL_12_PACKAGED_TRIE_LENGTH_RANK_CASE_ASSETS_VALIDATED")
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
            val controller = TypingSessionController(graphemes); val editor = Editor()
            controller.startSession(editorContext, 0, 0)
            val result = linkedMapOf<String, Any?>("index" to index, "id" to id, "split" to split,
                "language" to language.locale.language, "prefix" to prefix, "typed" to typed,
                "maximumAlternatives" to CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
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
                val fullGeneration = generator.generate(typed, language)
                result["fullTokenGeneration"] = candidate(fullGeneration)
                result["localDecision"] = LocalCorrectionPolicy.decide(fullGeneration, language)?.canonicalKey
                val localRequest = controller.beginCandidateRequest(index.toLong() + 1, language)
                result["requestToken"] = localRequest?.token
                val generation = localRequest?.let {
                    if (it.token == typed) fullGeneration else generator.generate(it.token, language)
                }
                result["actualRequestGeneration"] = generation?.let(::candidate)
                result["actualOriginal"] = generation?.original ?: controller.state.composing?.typedWord
                result["candidatesAccepted"] = if (localRequest != null) controller.acceptCandidates(
                    LocalCandidateReply(localRequest.sessionId, localRequest.revision, localRequest.requestId,
                        generation!!)) else null
                val modelRequest = controller.beginModelRanking(index.toLong() + 1)
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
                    check(deliveries[id] == null) { "DELIVERY_FOR_NO_REQUEST" }; "NO_CURRENT_MODEL_REQUEST"
                } else if (mode == "unavailable") {
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
                        }) })
                val beforeBoundaryText = editor.text; editor.commands.clear()
                result["boundaryResult"] = type(" ").name; result["afterBoundary"] = editor.snapshot()
                result["boundaryCommands"] = editor.commands.toList()
                result["boundaryChangedBeyondInsertedSpace"] = editor.text != beforeBoundaryText + " "
                result["stateAfterBoundary"] = state(controller)
                result["autoEdit"] = controller.state.lastAutoEdit?.let { mapOf(
                    "original" to it.original, "applied" to it.applied,
                    "committedStart" to it.committedStart, "contextBefore" to it.contextBefore,
                    "restoreComposition" to it.restoreComposition.text,
                    "hasCorrectionCandidates" to (it.correction != null),
                    "correctionGeneration" to it.correction?.generation?.let(::candidate)) }
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
        if (mode == "ready") check(consumedDeliveries == deliveries.keys) { "UNCONSUMED_OR_FOREIGN_DELIVERY" }
        check(!hadError) { "ROW_ERRORS" }
    }
}
