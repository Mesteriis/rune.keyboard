package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RankingModelScore
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import java.security.MessageDigest
import java.text.BreakIterator
import java.util.Base64
import java.util.Locale

/** Scratch observer. No expected answer, cohort, corpus label, or model score enters this program. */
object ProductControllerDiagnostic {
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

    /** In-memory editor, derived only from commands. Never reads controller buffers to edit text. */
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
                    for (item in edit.edits) {
                        if (!edit.isCurrent() || !execute(item)) return false
                    }
                }
                is TypingEdit.SetComposingText -> replace(edit.value, true)
                is TypingEdit.CommitText -> replace(edit.value, false)
                TypingEdit.FinishComposingText -> {
                    commands.add(mapOf("type" to "FinishComposingText"))
                    composingStart = -1; composingEnd = -1
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
            commands.add(mapOf("type" to if (composing) "SetComposingText" else "CommitText", "value" to value,
                "replacedStart" to start, "replacedEnd" to end))
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
        buildList { var b = iterator.first(); while (b != BreakIterator.DONE) { add(b); b = iterator.next() } }
    }

    private fun candidate(g: CandidateGeneration) = mapOf(
        "original" to g.original, "completion" to g.completion.name, "isValidWord" to g.isValidWord,
        "prohibitsAutoReplace" to g.prohibitsAutoReplace, "protectedReason" to g.protectedReason?.name,
        "inspectedStates" to g.inspectedStates, "verifiedTerminals" to g.verifiedTerminals,
        "alternatives" to g.alternatives.map { c -> mapOf(
            "text" to c.text, "canonicalKey" to c.canonicalKey, "terminalKey" to c.terminalKey,
            "language" to c.language.locale.language, "isFallback" to c.isFallback,
            "languagePrior" to c.languagePrior, "frequencyRank" to c.frequencyRank,
            "unitDistance" to c.unitDistance, "editCost" to c.editFeatures.editCost,
            "repeatedCharacterEdits" to c.editFeatures.repeatedCharacterEdits,
            "repetitionBonus" to c.editFeatures.repetitionBonus, "lengthDifference" to c.lengthDifference,
            "casePattern" to c.casePattern.name, "kind" to c.kind.name,
            "canonicalCaseUnambiguous" to c.canonicalCaseUnambiguous) })

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
        check(editor.execute(TypingEdit.SetComposingText("ab")) && editor.text == "ab" && editor.caret == 2)
        check(editor.execute(TypingEdit.SetComposingText("abc")) && editor.text == "abc")
        check(editor.execute(TypingEdit.CommitText("Cat ")) && editor.text == "Cat " && editor.composingStart == -1)
        check(editor.execute(TypingEdit.SetComposingRegion(3, 4)) && editor.caret == 4)
        check(editor.execute(TypingEdit.SetComposingText(" dog")) && editor.text == "Cat dog")
        check(editor.execute(TypingEdit.FinishComposingText) && editor.composingStart == -1)
        check(editor.execute(TypingEdit.CommitText("!")) && editor.text == "Cat dog!")
        check(!editor.execute(TypingEdit.Batch(listOf(TypingEdit.CommitText("bad"))) { false }) && editor.text == "Cat dog!")
        System.err.println("INDEPENDENT_EDITOR_SELF_CHECK_PASS")
    }

    @JvmStatic fun main(args: Array<String>) {
        check(args.size == 2)
        executorSelfCheck()
        val assets = File(args[1])
        fun mapping(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
            it.map(FileChannel.MapMode.READ_ONLY, 0, it.size())
        }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH).map { trust ->
            val lang = trust.language.locale.language
            val load = PackedLexiconData.validate(trust, mapping(File(assets, "smarttyping/lexicon/$lang.trie")),
                mapping(File(assets, "smarttyping/lexicon/$lang.trie.lengths")),
                mapping(File(assets, "smarttyping/lexicon/frequency/$lang.ranks")))
            check(load is PackedLexiconLoad.Ready) { "PACKED_ASSET_NOT_READY:$lang" }
            load.lexicon
        }
        val cases = KeyboardLanguage.entries.associateWith { language ->
            val trust = FrozenCanonicalCaseLexicons.forLanguage(language)
            val bytes = File(assets, trust.path).readBytes()
            val digest = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            check(bytes.size.toLong() == trust.bytes && digest == trust.sha256) { "CASE_HASH" }
            CanonicalCaseData.validate(bytes)
        }
        val generator = CandidateGenerator(PackedCandidateLexicon(handles), CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
            CanonicalCaseLexicon { language, key -> cases.getValue(language).lookup(key) })
        System.err.println("ALL_12_PACKAGED_TRIE_LENGTH_RANK_CASE_ASSETS_VALIDATED")
        val settings = KeyboardSettings.DEFAULT
        File(args[0]).useLines { lines -> lines.forEachIndexed { index, line ->
            val fields = line.split('\t')
            check(fields.size == 11 && fields[0].toInt() == index)
            fun decoded(i: Int) = String(Base64.getDecoder().decode(fields[i]), Charsets.UTF_8)
            val id = decoded(1)
            val language = KeyboardLanguage.entries.single { it.locale.language == fields[2] }
            val prefix = decoded(3); val typed = decoded(4)
            val keyboard = KeyboardState(language)
            val editorContext = EditorContext.from(1, 0)
            val policy = MechanicalPunctuationPolicy(editorContext.inputPolicy, editorContext.mode,
                editorContext.requiresRawKeyEvents, settings.mechanicalPunctuation, settings.doubleSpacePeriod)
            val controller = TypingSessionController(graphemes)
            val editor = Editor()
            controller.startSession(editorContext, 0, 0)
            val result = linkedMapOf<String, Any?>("index" to index, "id" to id, "language" to language.locale.language,
                "prefix" to prefix, "typed" to typed, "maximumAlternatives" to CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,
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
                    val response = controller.typeText(value, policy, keyboard, doubleSpaceGesture = false,
                        autocorrectionMode = settings.autocorrectionMode, execute = editor::execute)
                    check(response == TypingTextResult.HANDLED) { "INPUT_$response" }
                    ack()
                    return response
                }
                val fullInput = (if (prefix.isNotEmpty()) "$prefix " else "") + typed
                fullInput.codePoints().forEach { type(String(Character.toChars(it))) }
                result["inputExpected"] = fullInput
                result["beforeBoundary"] = editor.snapshot()
                result["stateBeforeCandidates"] = state(controller)
                result["inputChangedByTyping"] = editor.text != fullInput
                result["typingCommands"] = editor.commands.toList()
                val fullGeneration = generator.generate(typed, language)
                result["fullTokenGeneration"] = candidate(fullGeneration)
                val request = controller.beginCandidateRequest(index.toLong(), language)
                result["requestToken"] = request?.token
                val generation = request?.let { if (it.token == typed) fullGeneration else generator.generate(it.token, language) }
                result["actualRequestGeneration"] = generation?.let(::candidate)
                result["candidatesAccepted"] = if (request != null) controller.acceptCandidates(LocalCandidateReply(
                    request.sessionId, request.revision, request.requestId, generation!!)) else null
                val ordinaryBeforeModel = generation?.let { CalibratedSpellingPolicy.rank(it, language) }
                fun ranking(value: io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedRanking?) = value?.let {
                    mapOf("candidateIds" to it.candidateIds, "preferredId" to it.preferredId, "usedModel" to it.usedModel)
                }
                result["ordinaryRankingBeforeModel"] = ranking(ordinaryBeforeModel)
                val scoredRequestExists = fields[5] != "NONE"
                val expectedPrefix = if (scoredRequestExists) decoded(5) else null
                val expectedContinuations = if (scoredRequestExists) fields[6].split(',').map {
                    String(Base64.getDecoder().decode(it), Charsets.UTF_8)
                } else null
                val expectedIds = if (scoredRequestExists) fields[7].split(',').map(String::toInt) else null
                val responseStatus = fields[8]
                result["freshCacheStatus"] = responseStatus
                result["freshCacheError"] = fields[9].takeIf { it != "NONE" }
                result["scoredRequest"] = if (scoredRequestExists) mapOf("prefix" to expectedPrefix,
                    "continuations" to expectedContinuations, "candidateIds" to expectedIds) else null
                val modelRequest = controller.beginModelRanking(index.toLong() + 1)
                result["actualModelRequest"] = modelRequest?.let { mapOf("prefix" to it.prefix,
                    "continuations" to it.continuations, "candidateIds" to it.token.candidateIds) }
                val mismatches = mutableListOf<String>()
                if (modelRequest != null && scoredRequestExists) {
                    if (modelRequest.prefix != expectedPrefix) mismatches.add("PREFIX")
                    if (modelRequest.continuations != expectedContinuations) mismatches.add("CONTINUATIONS")
                    if (modelRequest.token.candidateIds != expectedIds) mismatches.add("CANDIDATE_IDS")
                }
                result["payloadMismatches"] = mismatches.toList()
                var rankingAfterModel = ordinaryBeforeModel
                result["modelAdmission"] = when {
                    modelRequest == null -> "NO_CURRENT_MODEL_REQUEST"
                    !scoredRequestExists -> "REFUSED_NO_SCORED_REQUEST"
                    mismatches.isNotEmpty() -> "REFUSED_PAYLOAD_MISMATCH"
                    responseStatus == "ERROR" -> {
                        result["modelReplyAccepted"] = controller.acceptModelRanking(ScoringReply(
                            modelRequest.token, ScoringCode.UNAVAILABLE, 0, emptyList()))
                        "MATCHED_SCORING_ERROR"
                    }
                    responseStatus != "OK" -> "REFUSED_NO_FRESH_RESPONSE"
                    else -> {
                        val numeric = fields[10].split(';').map { part ->
                            val pieces = part.split(',')
                            check(pieces.size == 3)
                            NumericScore(pieces[0].toInt(), pieces[1].toDouble(), pieces[2].toInt())
                        }
                        // ScoringReply itself checks numeric IDs match the live request order.
                        result["modelReplyAccepted"] = controller.acceptModelRanking(ScoringReply(
                            modelRequest.token, ScoringCode.OK, 0, numeric))
                        rankingAfterModel = generation?.let { CalibratedSpellingPolicy.rank(it, language,
                            numeric.map { RankingModelScore(it.candidateId, it.sumLogProbability, it.tokenCount) }) }
                        "MATCHED_NUMERIC_REPLY"
                    }
                }
                result["ordinaryRankingAfterModel"] = ranking(rankingAfterModel)
                result["stateBeforeBoundary"] = state(controller)
                result["candidateView"] = mapOf("enabled" to controller.candidateViewState.enabled,
                    "selectedCandidateId" to controller.candidateViewState.selectedCandidateId,
                    "candidates" to controller.candidateViewState.candidates.map { mapOf("id" to it.id, "text" to it.text) })
                val beforeBoundaryText = editor.text
                editor.commands.clear()
                result["boundaryResult"] = type(" ").name
                result["afterBoundary"] = editor.snapshot()
                result["boundaryCommands"] = editor.commands.toList()
                result["boundaryChangedBeyondInsertedSpace"] = editor.text != beforeBoundaryText + " "
                result["stateAfterBoundary"] = state(controller)
                result["autoEdit"] = controller.state.lastAutoEdit?.let { mapOf(
                    "original" to it.original, "applied" to it.applied, "committedStart" to it.committedStart,
                    "contextBefore" to it.contextBefore, "restoreComposition" to it.restoreComposition.text,
                    "hasCorrectionCandidates" to (it.correction != null),
                    "correctionGeneration" to it.correction?.generation?.let(::candidate)) }
                editor.commands.clear()
                val undo = controller.deletePrevious(editor::execute)
                result["backspaceResult"] = undo.name
                if (undo == TypingTextResult.HANDLED) ack()
                result["afterBackspace"] = editor.snapshot()
                result["backspaceCommands"] = editor.commands.toList()
                result["restoredBeforeBoundaryExactly"] = editor.text == beforeBoundaryText
                result["stateAfterBackspace"] = state(controller)
                result["status"] = "COMPLETE"
            } catch (e: Exception) {
                result["status"] = "ERROR"; result["error"] = e.javaClass.name + ":" + e.message
                result["editorAtFailure"] = editor.snapshot(); result["stateAtFailure"] = state(controller)
                result["commandsAtFailure"] = editor.commands.toList()
                e.printStackTrace(System.err)
            }
            println(json(result))
            if ((index + 1) % 500 == 0) System.err.println("ROWS_COMPLETED:${index + 1}")
        } }
    }
}
