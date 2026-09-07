package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPlanner
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPlan
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalEditKind
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.OwnedPunctuationSuffix
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.PunctuationAction
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualPunctuationEngine
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RankingModelScore
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedRanking
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CommonConfusions
import io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenReason
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateSearchControl
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateRequest
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.NoopSmartTypingTracer
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTracer
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.section
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticEvent
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticKind
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticText
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.NoTypingDiagnostics
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnostics
import java.util.ArrayDeque

/**
 * Main-thread session owner. The execution callback returns the editor's actual result; all
 * acknowledgements and failure cleanup happen here. It must not independently replay edits.
 */
class TypingSessionController internal constructor(
    private val graphemes: GraphemeSegmenter,
    private val spellingQualification: SpellingQualification = SpellingQualification.CURRENT,
    private val trace: SmartTypingTracer = NoopSmartTypingTracer,
) {
    private var diagnostics: TypingDiagnostics = NoTypingDiagnostics
    fun setDiagnostics(observer: TypingDiagnostics) {
        closeDiagnosticsAdmission()
        diagnostics = observer
    }
    fun closeDiagnosticsAdmission() { try { diagnostics.invalidate() } catch (_: Throwable) { } }
    /** Called only with an actual Rune command, never an editor read. */
    fun recordInput(input: String) {
        diagnose(DiagnosticKind.INPUT, DiagnosticReason.NONE) { diagnosticText(input = input) }
    }

    private fun diagnose(kind: DiagnosticKind, reason: DiagnosticReason, count: Int = 0,
        selected: Int = -1, model: Boolean = false, session: Long = state.sessionId,
        revision: Long = state.revision, text: (() -> DiagnosticText)? = { diagnosticText() }) {
        try { diagnostics.record(DiagnosticEvent(kind, reason, session, revision,
            count, selected, model), text) } catch (_: Throwable) { }
    }
    private fun diagnosticText(input: String = "", result: String = "") = DiagnosticText(
        input = input, context = context?.text.orEmpty(), original = state.composing?.typedWord.orEmpty(),
        candidates = candidateSelection?.alternatives?.map { it.text }.orEmpty(), result = result,
    )
    private fun rankingRejected(reason: DiagnosticReason, origin: ScoringToken? = null, count: Int = 0,
        text: (() -> DiagnosticText)? = if (reason == DiagnosticReason.STALE) null else { { diagnosticText() } }): Boolean {
        diagnose(DiagnosticKind.RANKING, reason, count, session = origin?.sessionId ?: state.sessionId,
            revision = origin?.revision ?: state.revision, text = text)
        return false
    }
    private fun boundaryBypass(reason: DiagnosticReason): TypingTextResult {
        diagnose(DiagnosticKind.BOUNDARY, reason)
        return TypingTextResult.BYPASS
    }
    constructor() : this(IcuGraphemeSegmenter)
    internal constructor(trace: SmartTypingTracer) : this(IcuGraphemeSegmenter, SpellingQualification.CURRENT, trace)

    /** Legacy replay metadata reports general ranking only; finite exceptions are separate. */
    internal fun isSpellingQualified(language: KeyboardLanguage, modelAssisted: Boolean): Boolean =
        if (modelAssisted) spellingQualification.allowsModel(language) else spellingQualification.allowsGeneralLocal(language)

    /** Retrieval availability only: the selected source still needs its own boundary admission. */
    internal fun isLocalSpellingQualified(language: KeyboardLanguage): Boolean =
        spellingQualification.allowsCommonConfusion(language) || spellingQualification.allowsGeneralLocal(language)

    internal fun isModelSpellingQualified(language: KeyboardLanguage): Boolean = spellingQualification.allowsModel(language)

    var state = TypingSessionState()
        private set

    /** Acknowledged gesture hint only; visual Shift remains owned by KeyboardState. */
    var sentenceCapitalizationPending: Boolean = false
        private set

    private var context: SessionTextContext? = null
    private var selectionStart = -1
    private var selectionEnd = -1
    private var composingStart = -1
    private val expectedSelections = ArrayDeque<EditorSelection>()
    private var expectedEditorSelection: EditorSelection? = null
    private var lastAcknowledgedSelection: EditorSelection? = null
    private var awaitingEditorSelection = false
    private var plainWordUntilBoundary = false
    private var editorEditDepth = 0
    private var candidateEpoch = 0L
    private var lastCandidateRequestId = -1L
    private var pendingCandidate: CandidateStamp? = null
    private var candidateSelection: CandidateSelection? = null
    private var pendingModelRanking: ModelRankingStamp? = null
    private var pendingSpaceCorrection: SpaceCorrectionStamp? = null
    private var pendingContextualRanking: ContextualRankingStamp? = null
    private var contextualSelection: ContextualSelection? = null
    private var contextualCompletedSelection: CandidateSelection? = null
    private var lastModelRequestId = 0L

    /** Owner must additionally check the active view, editor policy, layer, language and readiness. */
    val ownsCandidateComposition: Boolean
        get() {
            val composing = state.composing ?: return false
            return state.enabled && !awaitingEditorSelection && editorEditDepth == 0 &&
                composing.typedWord.isNotEmpty() && composingStart >= 0 &&
                selectionStart == selectionEnd &&
                selectionStart.toLong() == composingStart.toLong() + composing.text.length &&
                context?.text?.endsWith(composing.text) == true
        }

    val canRequestCandidates: Boolean
        get() = ownsCandidateComposition && !state.originalSelected &&
            candidateSelection?.manual != true &&
            !ProtectedTokenPolicy.isProtected(state.composing!!.typedWord)

    /** Only the numeric stamp is retained. Caller admits this request after live service checks. */
    fun beginCandidateRequest(requestId: Long, activeLanguage: KeyboardLanguage): LocalCandidateRequest? {
        if (!canRequestCandidates || requestId < 0 || requestId <= lastCandidateRequestId) return null
        clearCandidates()
        lastCandidateRequestId = requestId
        pendingCandidate = CandidateStamp(state.sessionId, state.revision, requestId, activeLanguage)
        return LocalCandidateRequest(state.sessionId, state.revision, requestId,
            state.composing!!.typedWord, activeLanguage, eligible = true)
    }

    /** Service rechecks its policy/language/lifetime first; this owner checks the exact live word. */
    fun acceptCandidates(reply: LocalCandidateReply): Boolean {
        val stamp = pendingCandidate ?: return false
        if (stamp.sessionId != reply.sessionId || stamp.revision != reply.revision || stamp.requestId != reply.requestId) return false
        pendingCandidate = null
        val generation = reply.generation
        if (state.sessionId != stamp.sessionId || state.revision != stamp.revision ||
            !canRequestCandidates || generation.original != state.composing?.typedWord ||
            generation.completion == CandidateCompletion.CANCELLED ||
            generation.alternatives.size > CandidateGenerator.MAX_ALTERNATIVES ||
            generation.inspectedStates !in 0..CandidateSearchControl.MAX_STATES ||
            generation.verifiedTerminals !in 0..CandidateSearchControl.MAX_VERIFIED
        ) return false

        val suggests = generation.completion == CandidateCompletion.COMPLETE ||
            generation.completion == CandidateCompletion.STATES_EXHAUSTED ||
            generation.completion == CandidateCompletion.VERIFIED_EXHAUSTED
        val canonicalCaseOnly = generation.alternatives.isNotEmpty() &&
            generation.alternatives.all { it.kind == GeneratedCandidateKind.CANONICAL_CASE }
        if ((!suggests || generation.isValidWord || generation.protectedReason != null) &&
            generation.alternatives.isNotEmpty() && !(generation.isValidWord && canonicalCaseOnly)) return false
        val original = generation.original!!
        val originalCase = CasePattern.analyze(original)
        val seen = hashSetOf(TokenUnicode.folded(original))
        var canonicalCaseCount = 0
        for (candidate in generation.alternatives) {
            val reason = ProtectedTokenPolicy.reason(candidate.text)
            // Eligible one-letter uppercase input can expand to a multi-letter uppercase display.
            // Source admission stays protected; only its preserved ALL_CAPS output is allowed.
            val canonicalCase = candidate.kind == GeneratedCandidateKind.CANONICAL_CASE
            if (canonicalCase) canonicalCaseCount++
            if ((reason != null && !(reason == ProtectedTokenReason.ALL_CAPS && originalCase == CasePattern.UPPER)) ||
                canonicalCase && (canonicalCaseCount > 1 || originalCase != CasePattern.LOWER ||
                    CasePattern.analyze(candidate.text) != CasePattern.TITLE ||
                    TokenUnicode.folded(candidate.text) != TokenUnicode.folded(original)) ||
                !canonicalCase && !seen.add(TokenUnicode.folded(candidate.text))) return false
        }
        val alternatives = generation.alternatives.toList()
        val snapshot = generation.copy(alternatives = alternatives)
        val commonId = CommonConfusions.preferredId(snapshot, stamp.language)
        val ranking = if (commonId > 0) {
            CalibratedRanking(listOf(commonId) + alternatives.indices.map { it + 1 }.filter { it != commonId },
                preferredId = commonId, usedModel = false)
        } else if (snapshot.isCanonicalCaseCorrection()) {
            CalibratedRanking(listOf(1), preferredId = 1, usedModel = false)
        } else trace.section(SmartTypingTraceSection.CANDIDATE_RANK) {
            CalibratedSpellingPolicy.rank(snapshot, stamp.language)
        }
        candidateSelection = CandidateSelection(snapshot, stamp.language, stamp.requestId,
            selectedIndex = (ranking?.preferredId ?: 0) - 1,
            order = ranking?.candidateIds?.map { it - 1 } ?: alternatives.indices.toList(), ranking = ranking)
        diagnose(DiagnosticKind.CANDIDATES, DiagnosticReason.ACCEPTED, alternatives.size,
            (ranking?.preferredId ?: 0) - 1, ranking?.usedModel == true)
        return true
    }

    /** No editor mutation or veto reset. Service calls this when its own policy/route invalidates. */
    fun clearCandidates() {
        candidateEpoch++
        pendingCandidate = null
        candidateSelection = null
        pendingModelRanking = null
        pendingSpaceCorrection = null
        pendingContextualRanking = null
        contextualSelection = null
        contextualCompletedSelection = null
    }

    /** Snapshot only after consumer eligibility checks. Full candidate set; Rune-owned prefix only. */
    val canRequestModelRanking: Boolean
        get() = canRequestCandidates && candidateSelection?.let {
            it.original.codePointCount(0, it.original.length) > 2 && !isEligibleLocalReplacement(it) &&
                !it.modelRanked && !it.generation.isValidWord && it.alternatives.isNotEmpty() &&
                state.composing?.typedWord == it.original
        } == true

    fun beginModelRanking(requestId: Long): ScoringInput? {
        val selection = candidateSelection ?: return null
        if (!canRequestModelRanking || requestId <= lastModelRequestId) return null
        val text = context?.text ?: return null
        if (!text.endsWith(selection.original)) return null
        val token = ScoringToken(state.sessionId, state.revision, requestId,
            (0..selection.alternatives.size).toList())
        val input = try {
            ScoringInput(token, text.dropLast(selection.original.length),
                listOf(selection.original) + selection.alternatives.map { it.text })
        } catch (_: IllegalArgumentException) { return null }
        lastModelRequestId = requestId
        pendingModelRanking = ModelRankingStamp(token, selection)
        return input
    }

    /** Store a calibrated ranking; boundary mutation separately checks preference and qualification. */
    fun acceptModelRanking(reply: ScoringReply): Boolean {
        if (!isCurrentModelRanking(reply.token)) return rankingRejected(DiagnosticReason.STALE)
        pendingModelRanking = null
        val selection = candidateSelection ?: return rankingRejected(DiagnosticReason.INVALID)
        if (reply.code != ScoringCode.OK) return rankingRejected(DiagnosticReason.MODEL_ERROR)
        val ranking = trace.section(SmartTypingTraceSection.CANDIDATE_RANK) {
            CalibratedSpellingPolicy.rank(selection.generation, selection.language,
                reply.scores.map { RankingModelScore(it.candidateId, it.sumLogProbability, it.tokenCount) })
        } ?: return rankingRejected(DiagnosticReason.ABSTAINED)
        candidateSelection = selection.copy(
            order = ranking.candidateIds.map { it - 1 },
            selectedIndex = ranking.preferredId - 1,
            modelRanked = true,
            ranking = ranking,
        )
        diagnose(DiagnosticKind.RANKING, DiagnosticReason.ACCEPTED, selection.alternatives.size,
            ranking.preferredId - 1, ranking.usedModel)
        return true
    }

    fun isCurrentModelRanking(token: ScoringToken): Boolean {
        val pending = pendingModelRanking ?: return false
        val selection = candidateSelection ?: return false
        return token == pending.token && selection === pending.selection && canRequestCandidates &&
            state.sessionId == token.sessionId && state.revision == token.revision &&
            state.composing?.typedWord == selection.original
    }

    /** Cancels ranking ownership without removing the current deterministic/manual strip. */
    fun cancelModelRanking() {
        pendingModelRanking = null
        pendingSpaceCorrection = null
        pendingContextualRanking = null
    }

    /**
     * The owner opts in only for an ordinary Space in qualified automatic mode. The word is
     * committed immediately. Preserve exactly one already-admitted ranking if the resulting
     * document still ends in that complete Rune-owned word plus one composing space.
     */
    internal fun retainRankingAcrossSpace(action: () -> TypingTextResult): TypingTextResult {
        val ranking = pendingModelRanking?.takeIf { isCurrentModelRanking(it.token) }
        val previous = state.composing
        val owned = punctuationEvidence()
        val tokenStart = owned?.text?.indexOfLast { it.isWhitespace() }?.plus(1)
        val captured = if (ranking != null && previous != null && owned != null && tokenStart != null &&
            previous.text.length < MAX_COMPOSING_UTF16 &&
            (tokenStart > 0 || owned.startsAtTokenBoundary) && owned.text.substring(tokenStart) == previous.typedWord &&
            !ranking.selection.generation.prohibitsAutoReplace &&
            spellingQualification.allowsModel(ranking.selection.language)) {
            SpaceCorrectionStamp(ranking, previous, composingStart, context!!.text)
        } else null
        val result = action()
        if (result == TypingTextResult.HANDLED && captured != null &&
            state.sessionId == captured.ranking.token.sessionId && state.lastAutoEdit == null &&
            ownsSpaceAfter(captured)) {
            captured.revisionAfterSpace = state.revision
            pendingSpaceCorrection = captured
        }
        return result
    }

    internal val hasSpaceCorrection: Boolean get() = pendingSpaceCorrection != null

    internal fun isCurrentSpaceCorrection(token: ScoringToken): Boolean {
        val pending = pendingSpaceCorrection ?: return false
        return token == pending.ranking.token && state.sessionId == token.sessionId &&
            state.revision == pending.revisionAfterSpace && ownsSpaceAfter(pending)
    }

    private fun ownsSpaceAfter(pending: SpaceCorrectionStamp): Boolean =
        state.enabled && !awaitingEditorSelection && editorEditDepth == 0 &&
            state.composing == ComposingSegment(leadingBoundary = " ") &&
            selectionStart == selectionEnd && composingStart.toLong() == pending.start.toLong() + pending.previous.text.length &&
            selectionStart.toLong() == composingStart.toLong() + 1 &&
            context?.text?.endsWith(pending.previous.text + " ") == true

    /** Uses only the certified suffix. The caller also enforces the deadline and live preferences. */
    internal fun acceptSpaceCorrection(reply: ScoringReply, execute: (TypingEdit) -> Boolean): Boolean {
        if (!isCurrentSpaceCorrection(reply.token)) return rankingRejected(DiagnosticReason.STALE)
        val pending = pendingSpaceCorrection ?: return rankingRejected(DiagnosticReason.INVALID)
        pendingSpaceCorrection = null
        val selection = pending.ranking.selection
        val payload = { DiagnosticText(context = pending.contextBefore, original = selection.original,
            candidates = selection.alternatives.map { it.text }) }
        if (reply.code != ScoringCode.OK) return rankingRejected(DiagnosticReason.MODEL_ERROR,
            pending.ranking.token, selection.alternatives.size, payload)
        val ranking = trace.section(SmartTypingTraceSection.CANDIDATE_RANK) {
            CalibratedSpellingPolicy.rank(selection.generation, selection.language,
                reply.scores.map { RankingModelScore(it.candidateId, it.sumLogProbability, it.tokenCount) })
        } ?: return rankingRejected(DiagnosticReason.ABSTAINED, pending.ranking.token, selection.alternatives.size, payload)
        if (!ranking.usedModel || ranking.preferredId <= 0) return rankingRejected(DiagnosticReason.ABSTAINED,
            pending.ranking.token, selection.alternatives.size, payload)
        val word = selection.alternatives.getOrNull(ranking.preferredId - 1)?.text ?: return false
        val rendered = pending.previous.copy(typedWord = word).text + " "
        val end = pending.start.toLong() + rendered.length
        if (rendered.length > MAX_COMPOSING_UTF16 || rendered.codePointCount(0, rendered.length) > 128 ||
            end > Int.MAX_VALUE) return false
        val caret = end.toInt()
        remember(EditorSelection(selectionStart, selectionEnd, pending.start, selectionStart))
        remember(EditorSelection(caret, caret, -1, -1))
        val boundary = ComposingSegment(leadingBoundary = " ")
        diagnose(DiagnosticKind.BOUNDARY, DiagnosticReason.AUTO_REPLACE, selection.alternatives.size,
            ranking.preferredId - 1, ranking.usedModel, pending.ranking.token.sessionId, pending.ranking.token.revision) {
            DiagnosticText(context = context?.text.orEmpty(), original = selection.original,
                candidates = selection.alternatives.map { it.text }, result = rendered)
        }
        return trace.section(SmartTypingTraceSection.CORRECTION_COMMIT) {
            applyGuardedBatch(listOf(TypingEdit.SetComposingRegion(pending.start, selectionStart),
                TypingEdit.CommitText(rendered), TypingEdit.SetComposingRegion(caret - 1, caret)),
                EditorSelection(caret, caret, caret - 1, caret), execute) {
                check(context!!.replaceSuffix(pending.previous.text + " ", rendered)) { "Space correction ownership mismatch" }
                composingStart = caret - 1
                state = state.copy(composing = boundary, originalSelected = false,
                    lastAutoEdit = UndoableTextEdit(pending.previous.text, rendered, state.sessionId, state.revision,
                        pending.previous, pending.contextBefore, pending.start, boundary,
                        UndoCorrectionCandidates(selection.generation, selection.language, selection.requestId)))
                publish()
            } == TypingTextResult.HANDLED
        }
    }

    val canRequestContextualRanking: Boolean
        get() {
            val selection = candidateSelection ?: return false
            val composing = state.composing ?: return false
            return composing.typedWord.codePointCount(0, composing.typedWord.length) > 2 &&
                canRequestCandidates && selection.generation.isValidWord &&
                selection.alternatives.isEmpty() && contextualCompletedSelection !== selection &&
                composing.leadingBoundary == " " &&
                contextualInput(selection.language) != null
        }

    fun beginContextualRanking(requestId: Long): ScoringInput? {
        if (!canRequestContextualRanking || requestId <= lastModelRequestId) return null
        val selection = candidateSelection ?: return null
        val (prefix, variants) = contextualInput(selection.language) ?: return null
        val token = ScoringToken(state.sessionId, state.revision, requestId, variants.map { it.id })
        val input = try { ScoringInput(token, prefix, variants.map { it.continuation }) }
        catch (_: IllegalArgumentException) { return null }
        lastModelRequestId = requestId
        pendingContextualRanking = ContextualRankingStamp(token, selection, variants)
        return input
    }

    fun isCurrentContextualRanking(token: ScoringToken): Boolean {
        val pending = pendingContextualRanking ?: return false
        return token == pending.token && candidateSelection === pending.selection &&
            canRequestContextualRanking && state.sessionId == token.sessionId && state.revision == token.revision
    }

    fun acceptContextualRanking(reply: ScoringReply): Boolean {
        if (!isCurrentContextualRanking(reply.token)) return rankingRejected(DiagnosticReason.STALE)
        val pending = pendingContextualRanking ?: return rankingRejected(DiagnosticReason.INVALID)
        pendingContextualRanking = null
        val payload = { DiagnosticText(context = context?.text.orEmpty(), original = pending.selection.original,
            candidates = pending.variants.map { it.continuation }) }
        if (reply.code != ScoringCode.OK || reply.scores.size != pending.variants.size) return rankingRejected(
            DiagnosticReason.MODEL_ERROR, pending.token, pending.variants.size, payload)
        contextualCompletedSelection = pending.selection
        return trace.section(SmartTypingTraceSection.CANDIDATE_RANK) {
            val winnerId = ContextualPunctuationPolicy.choose(pending.variants.map { it.id },
                reply.scores.map { ContextualPunctuationPolicy.Score(it.candidateId, it.sumLogProbability, it.tokenCount) })
                ?: return@section rankingRejected(DiagnosticReason.ABSTAINED, pending.token, pending.variants.size, payload)
            val winner = pending.variants.singleOrNull { it.id == winnerId } ?: return@section rankingRejected(
                DiagnosticReason.INVALID, pending.token, pending.variants.size, payload)
            contextualSelection = ContextualSelection(pending.token, pending.selection, winner, pending.variants)
            diagnose(DiagnosticKind.RANKING, DiagnosticReason.CONTEXTUAL, pending.variants.size,
                pending.variants.indexOf(winner), true, pending.token.sessionId, pending.token.revision) {
                DiagnosticText(context = context?.text.orEmpty(), original = pending.selection.original,
                    candidates = pending.variants.map { it.continuation }, result = winner.continuation)
            }
            true
        }
    }

    private fun contextualInput(language: KeyboardLanguage): Pair<String, List<ContextualPunctuationEngine.Variant>>? {
        val composing = state.composing ?: return null
        val text = context?.text ?: return null
        if (!text.endsWith(composing.text)) return null
        val prefix = text.dropLast(composing.text.length)
        val variants = ContextualPunctuationEngine.variants(prefix, composing.typedWord, language)
        return variants.takeIf { it.size in 2..8 }?.let { prefix to it }
    }

    /** Diagnostic completion; exhaustion still prohibits automatic replacement. */
    val candidateCompletion: CandidateCompletion?
        get() = candidateSelection?.completion

    /** Pure projection. Service applies its additional HIDDEN policy before displaying it. */
    val candidateViewState: SmartTypingViewState
        get() {
            if (!state.enabled) return SmartTypingViewState.HIDDEN
            val originalId = originalCandidateId ?: return SmartTypingViewState.EMPTY
            val selection = candidateSelection
            val items = buildList {
                add(CandidateUiItem.Original(originalId, selection?.original ?: state.composing!!.typedWord))
                selection?.visibleIndices?.forEach { index ->
                    add(CandidateUiItem.Correction(correctionId(selection.requestId, index), selection.alternatives[index].text))
                }
                contextualSelection?.takeIf { it.selection === selection }?.let { contextual ->
                    if (size < SmartTypingViewState.MAX_VISIBLE_CANDIDATES) {
                        add(CandidateUiItem.Punctuation(contextualId(contextual),
                            contextual.variant.boundary.trimEnd()))
                    }
                }
            }
            val selectedId = if (selection != null && selection.selectedIndex >= 0 &&
                (!state.originalSelected || selection.manual)) {
                correctionId(selection.requestId, selection.selectedIndex)
            } else originalId
            return SmartTypingViewState(true, items, selectedId)
        }

    val originalCandidateId: String?
        get() = if (ownsCandidateComposition)
            "original:${state.sessionId}:${state.revision}:$candidateEpoch" else null

    /** A stale strip tap cannot select a different word or resurrect an earlier session. */
    fun selectOriginal(candidateId: String): Boolean {
        if (candidateId != originalCandidateId) return false
        val selection = candidateSelection
        // The old no-editor API cannot restore a manually replaced word. Use selectCandidate.
        if (selection != null && selection.original != state.composing?.typedWord) return false
        discardUndo()
        clearCandidates()
        state = state.copy(originalSelected = true, revision = state.revision + 1)
        candidateSelection = selection?.copy(selectedIndex = -1, manual = true)
        diagnose(DiagnosticKind.MANUAL, DiagnosticReason.ORIGINAL)
        return true
    }

    /** Explicit user choice only. Unknown/stale IDs are REJECTED and must never fall back/replay. */
    fun selectCandidate(candidateId: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        if (!ownsCandidateComposition) return TypingTextResult.REJECTED
        contextualSelection?.takeIf { candidateId == contextualId(it) }?.let {
            return selectContextual(it, execute)
        }
        val selection = candidateSelection
        val index = if (candidateId == originalCandidateId) -1 else {
            selection?.visibleIndices?.firstOrNull {
                candidateId == correctionId(selection.requestId, it)
            } ?: return TypingTextResult.REJECTED
        }
        if (index == -1 && (selection == null || selection.original == state.composing!!.typedWord)) {
            return if (selectOriginal(candidateId)) TypingTextResult.HANDLED else TypingTextResult.REJECTED
        }
        if (selection == null) return TypingTextResult.REJECTED
        cancelModelRanking()
        val previous = state.composing!!
        val word = if (index == -1) selection.original else selection.alternatives[index].text
        val next = previous.copy(typedWord = word)
        val caret = composingStart.toLong() + next.text.length
        if (caret > Int.MAX_VALUE || next.text.length > MAX_COMPOSING_UTF16) return TypingTextResult.REJECTED
        discardUndo()
        val expected = EditorSelection(caret.toInt(), caret.toInt(), composingStart, caret.toInt())
        diagnose(DiagnosticKind.MANUAL, if (index == -1) DiagnosticReason.ORIGINAL else DiagnosticReason.CORRECTION,
            selection.alternatives.size, index) { diagnosticText(result = word) }
        return applyEdit(TypingEdit.SetComposingText(next.text), expected, execute) {
            check(context?.replaceSuffix(previous.text, next.text) == true) { "Candidate context mismatch" }
            state = state.copy(composing = next, originalSelected = state.originalSelected || index == -1)
            candidateSelection = selection.copy(selectedIndex = index, manual = true)
            publish()
        }
    }

    private fun correctionId(requestId: Long, index: Int): String =
        "correction:${state.sessionId}:${state.revision}:$requestId:$index"

    private fun contextualId(value: ContextualSelection) =
        "punctuation:${value.token.sessionId}:${value.token.revision}:${value.token.requestId}:${value.variant.id}"

    private fun selectContextual(selection: ContextualSelection, execute: (TypingEdit) -> Boolean): TypingTextResult {
        if (!isCurrentContextualSelection(selection)) return TypingTextResult.REJECTED
        val previous = state.composing!!
        val replacement = selection.variant.continuation
        if (replacement.length > MAX_COMPOSING_UTF16 || replacement.codePointCount(0, replacement.length) > 128) {
            return TypingTextResult.REJECTED
        }
        val end = composingStart.toLong() + replacement.length
        if (end > Int.MAX_VALUE) return TypingTextResult.REJECTED
        discardUndo()
        diagnose(DiagnosticKind.MANUAL, DiagnosticReason.CONTEXTUAL, selection.variants.size,
            selection.variants.indexOf(selection.variant), true, selection.token.sessionId, selection.token.revision) {
            DiagnosticText(context = context?.text.orEmpty(), original = selection.selection.original,
                candidates = selection.variants.map { it.continuation }, result = replacement)
        }
        return applyEdit(TypingEdit.SetComposingText(replacement),
            EditorSelection(end.toInt(), end.toInt(), composingStart, end.toInt()), execute) {
            check(context?.replaceSuffix(previous.text, replacement) == true) { "Contextual ownership mismatch" }
            state = state.copy(composing = ComposingSegment(selection.variant.boundary,
                replacement.removePrefix(selection.variant.boundary)))
            publish()
        }
    }

    private fun isCurrentContextualSelection(value: ContextualSelection): Boolean =
        contextualSelection === value && candidateSelection === value.selection &&
            state.sessionId == value.token.sessionId && state.revision == value.token.revision &&
            state.composing?.leadingBoundary == " " && ownsCandidateComposition

    fun startSession(editor: EditorContext, selectionStart: Int, selectionEnd: Int, diagnosticsFresh: Boolean = true) {
        endSession()
        val enabled = editor.supportsSmartTyping &&
            selectionStart >= 0 && selectionEnd >= 0
        this.selectionStart = selectionStart
        this.selectionEnd = selectionEnd
        context = if (enabled) SessionTextContext(graphemes) else null
        state = TypingSessionState(
            sessionId = state.sessionId + 1,
            revision = state.revision + 1,
            enabled = enabled,
        )
        try { diagnostics.startSession(state.sessionId, enabled, diagnosticsFresh) } catch (_: Throwable) { }
        diagnose(DiagnosticKind.SESSION, DiagnosticReason.START)
    }

    fun typeText(text: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        if (text.isNotEmpty()) discardUndo()
        if (!state.enabled || awaitingEditorSelection || text.isEmpty()) return TypingTextResult.BYPASS
        if (text.length == 1 && text[0] in PENDING_BOUNDARY) {
            val current = state.composing
            // Freeze the word exactly once, then retain only the current punctuation boundary.
            if (current?.typedWord?.isNotEmpty() == true || plainWordUntilBoundary ||
                (current?.text?.length ?: 0) + text.length > MAX_COMPOSING_UTF16
            ) {
                if (!finishComposition(execute)) return TypingTextResult.REJECTED
            }
            val pending = state.composing?.leadingBoundary.orEmpty()
            return compose(ComposingSegment(leadingBoundary = pending + text), text, execute)
        }
        if (text.codePoints().allMatch(::isWordCodePoint)) {
            if (plainWordUntilBoundary) return commitPlain(text, execute)
            val previous = state.composing ?: ComposingSegment()
            val next = previous.copy(typedWord = previous.typedWord + text)
            if (next.text.length > MAX_COMPOSING_UTF16) {
                if (!finishComposition(execute)) return TypingTextResult.REJECTED
                plainWordUntilBoundary = true
                return commitPlain(text, execute)
            }
            return compose(next, text, execute)
        }
        if (!finishComposition(execute)) return TypingTextResult.REJECTED
        return commitPlain(text, execute)
    }

    private fun commitPlain(text: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        val caret = minOf(selectionStart, selectionEnd) + text.length
        val expected = EditorSelection(caret, caret, -1, -1)
        return applyEdit(TypingEdit.CommitText(text), expected, execute) {
            context?.append(text)
            publish()
        }
    }

    fun deletePrevious(execute: (TypingEdit) -> Boolean): TypingTextResult {
        clearCandidates()
        if (!state.enabled || awaitingEditorSelection) return TypingTextResult.BYPASS
        state.lastAutoEdit?.let { edit ->
            discardUndo()
            if (edit.committedStart != null) return restoreBoundaryCorrection(edit, execute)
            if (edit.sessionId == state.sessionId && edit.revision == state.revision &&
                state.composing?.text == edit.applied && composingStart >= 0 &&
                selectionStart == selectionEnd &&
                selectionStart.toLong() == composingStart.toLong() + edit.applied.length
            ) {
                val caret = composingStart + edit.original.length
                val expected = EditorSelection(caret, caret, composingStart, caret)
                return applyEdit(TypingEdit.SetComposingText(edit.original), expected, execute) {
                    state = state.copy(
                        composing = edit.restoreComposition,
                        originalSelected = edit.restoreComposition.typedWord.isNotEmpty(),
                    )
                    context?.restore(edit.contextBefore)
                    publish()
                    diagnose(DiagnosticKind.UNDO, DiagnosticReason.ACCEPTED) { diagnosticText(result = edit.original) }
                }
            }
        }
        val previous = state.composing ?: run {
            awaitEditorSelection(execute)
            return TypingTextResult.BYPASS
        }
        reopenPreviousOwnedWord(previous, execute)?.let { return it }
        val end = graphemes.boundaries(previous.text).dropLast(1).last()
        val shortened = previous.text.substring(0, end)
        val next = if (shortened.isEmpty()) null else ComposingSegment(
            leadingBoundary = previous.leadingBoundary.take(shortened.length),
            typedWord = shortened.drop(previous.leadingBoundary.length),
        )
        val caret = composingStart + shortened.length
        val expected = EditorSelection(caret, caret, composingStart, caret)
        if (next == null) {
            // Android editors may report either a zero-width composing span or no span for the
            // empty set. Both are own acknowledgements; explicitly finish after the accepted set.
            remember(EditorSelection(caret, caret, -1, -1))
        }
        val result = applyEdit(TypingEdit.SetComposingText(shortened), expected, execute) {
            context?.removeLastGrapheme()
            state = state.copy(
                composing = next ?: ComposingSegment(),
                originalSelected = state.originalSelected && !next?.typedWord.isNullOrEmpty(),
            )
            publish()
        }
        if (result != TypingTextResult.HANDLED || next != null) return result
        return if (finishComposition(execute)) TypingTextResult.HANDLED else TypingTextResult.REJECTED
    }

    /**
     * Deleting Rune's pending space can safely reopen the complete preceding Rune-owned word.
     * This uses only the in-memory session suffix; it never reads or reconstructs editor text.
     */
    private fun reopenPreviousOwnedWord(
        previous: ComposingSegment,
        execute: (TypingEdit) -> Boolean,
    ): TypingTextResult? {
        if (previous.leadingBoundary != " " || previous.typedWord.isNotEmpty()) return null
        val owned = context?.text ?: return null
        if (!owned.endsWith(previous.text) || selectionStart != selectionEnd || composingStart < 0) return null
        val withoutSpace = owned.dropLast(1)
        var wordStart = withoutSpace.length
        while (wordStart > 0) {
            val codePoint = withoutSpace.codePointBefore(wordStart)
            if (!isWordCodePoint(codePoint)) break
            wordStart -= Character.charCount(codePoint)
        }
        if (wordStart == withoutSpace.length) return null
        val absoluteEnd = selectionStart - 1
        val absoluteStart = absoluteEnd - (withoutSpace.length - wordStart)
        val hasOwnedBoundary = wordStart > 0 && withoutSpace[wordStart - 1].isWhitespace()
        val startsDocument = wordStart == 0 && absoluteStart == 0
        if (absoluteStart < 0 || (!hasOwnedBoundary && !startsDocument)) return null
        val word = withoutSpace.substring(wordStart)
        val expected = EditorSelection(absoluteEnd, absoluteEnd, absoluteStart, absoluteEnd)
        return applyGuardedBatch(
            listOf(TypingEdit.SetComposingText(""), TypingEdit.SetComposingRegion(absoluteStart, absoluteEnd)),
            expected,
            execute,
        ) {
            context!!.removeLastGrapheme()
            composingStart = absoluteStart
            state = state.copy(composing = ComposingSegment(typedWord = word), originalSelected = false)
            publish()
        }
    }

    /** Finishes only Rune's owned span; invalidates revisions even when already idle. */
    fun finishComposition(execute: (TypingEdit) -> Boolean): Boolean {
        clearCandidates()
        discardUndo()
        plainWordUntilBoundary = false
        state = state.copy(revision = state.revision + 1, originalSelected = false)
        if (state.composing == null) return true
        val expected = EditorSelection(selectionStart, selectionEnd, -1, -1)
        return applyEdit(TypingEdit.FinishComposingText, expected, execute) {
            composingStart = -1
            state = state.copy(composing = null)
        } == TypingTextResult.HANDLED
    }

    /** Cursor/layer/language boundaries can explicitly discard context without editor reads. */
    fun invalidate(execute: (TypingEdit) -> Boolean): Boolean {
        closeDiagnosticsAdmission()
        val session = state.sessionId
        val finished = finishComposition(execute)
        if (state.sessionId != session) return false
        context?.clear()
        publish()
        return finished
    }

    /** Before a legacy mutation whose resulting caret is unknown, wait for its actual callback. */
    fun awaitEditorSelection(execute: (TypingEdit) -> Boolean): Boolean {
        val finished = invalidate(execute)
        awaitingEditorSelection = state.enabled && finished
        return finished
    }

    /** Actual service entry: attempt one owned transaction before the raw action. */
    fun typeText(
        text: String,
        policy: MechanicalPunctuationPolicy,
        keyboard: KeyboardState,
        doubleSpaceGesture: Boolean = false,
        autocorrectionMode: AutocorrectionMode = AutocorrectionMode.OFF,
        execute: (TypingEdit) -> Boolean,
    ): TypingTextResult {
        if (text.isNotEmpty()) discardUndo()
        val correction = applyBoundaryCorrection(text, policy, keyboard, autocorrectionMode, execute)
        if (correction != TypingTextResult.BYPASS) return correction
        val action = if (doubleSpaceGesture) PunctuationAction.DoubleSpaceGesture else PunctuationAction.Text(text)
        val transformed = applyPunctuation(action, policy, keyboard, execute)
        // An ineligible gesture follows the ordinary space path once, never the legacy converter.
        return if (transformed == TypingTextResult.BYPASS) typeText(text, execute) else transformed
    }

    /** Prepare SEND/GO/etc. from the last ready decision; never invent punctuation or wait. */
    fun prepareEditorAction(
        policy: MechanicalPunctuationPolicy,
        keyboard: KeyboardState,
        autocorrectionMode: AutocorrectionMode,
        execute: (TypingEdit) -> Boolean,
    ): TypingTextResult {
        discardUndo()
        val correction = applyBoundaryCorrection("", policy, keyboard, autocorrectionMode, execute)
        if (correction != TypingTextResult.BYPASS) return correction
        return if (finishComposition(execute)) TypingTextResult.HANDLED else TypingTextResult.REJECTED
    }

    /** Preserve one correction transaction when a rejected editor action falls back to newline. */
    fun appendEditorActionFallbackNewline(execute: (TypingEdit) -> Boolean): TypingTextResult {
        if (!state.enabled || awaitingEditorSelection || state.composing != null) return TypingTextResult.REJECTED
        val previousUndo = state.lastAutoEdit
        val caret = selectionStart.toLong() + 1
        if (selectionStart != selectionEnd || caret > Int.MAX_VALUE) return TypingTextResult.REJECTED
        val expected = EditorSelection(caret.toInt(), caret.toInt(), -1, -1)
        return applyEdit(TypingEdit.CommitText("\n"), expected, execute) {
            context?.append("\n")
            if (previousUndo != null && previousUndo.sessionId == state.sessionId) {
                state = state.copy(lastAutoEdit = UndoableTextEdit(previousUndo.original,
                    previousUndo.applied + "\n", state.sessionId, state.revision,
                    previousUndo.restoreComposition, previousUndo.contextBefore,
                    previousUndo.committedStart, null, previousUndo.correction))
            }
            publish()
        }
    }

    /** Compatibility entry for a recognized gesture; all conversion now uses the same planner. */
    fun doubleSpace(executeTypingEdit: (TypingEdit) -> Boolean): TypingTextResult {
        discardUndo()
        return applyPunctuation(PunctuationAction.DoubleSpaceGesture,
            MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, false, true),
            KeyboardState(KeyboardLanguage.ENGLISH), executeTypingEdit)
    }

    private fun punctuationEvidence(): OwnedPunctuationSuffix? {
        if (!state.enabled || awaitingEditorSelection || editorEditDepth != 0 ||
            selectionStart < 0 || selectionStart != selectionEnd || plainWordUntilBoundary
        ) return null
        val before = context?.text ?: return null
        val live = state.composing?.text
        if (live != null && (composingStart < 0 ||
                composingStart.toLong() + live.length != selectionStart.toLong() || !before.endsWith(live))) return null
        val count = before.codePointCount(0, before.length)
        val minimum = if (count > 256) before.offsetByCodePoints(0, count - 256) else 0
        val start = if (minimum == 0) 0 else graphemes.boundaries(before).first { it >= minimum }
        if (start > before.length - live.orEmpty().length) return null
        // A cut through a word is not evidence of a whole word. Only document start or an
        // actually retained Rune whitespace immediately before the slice establishes this flag.
        val tokenBoundary = if (start == 0) selectionStart.toLong() - before.length == 0L
            else before[start - 1].isWhitespace()
        return OwnedPunctuationSuffix(before.substring(start), live, tokenBoundary, state.sessionId, state.revision)
    }

    private fun applyPunctuation(
        action: PunctuationAction,
        policy: MechanicalPunctuationPolicy,
        keyboard: KeyboardState,
        execute: (TypingEdit) -> Boolean,
    ): TypingTextResult {
        val owned = punctuationEvidence() ?: return TypingTextResult.BYPASS
        val plan = trace.section(SmartTypingTraceSection.PUNCTUATION_RULE) {
            MechanicalPunctuationPlanner.plan(owned, action, policy)
        } as? MechanicalPunctuationPlan.Replace
            ?: return TypingTextResult.BYPASS
        var rendered = plan.replacementComposing
        plan.sentenceCapsForNewTextAt?.takeIf { keyboard.layer == KeyboardLayer.LETTERS }?.let { offset ->
            val end = offset + Character.charCount(rendered.codePointAt(offset))
            val caps = keyboard.withAutomaticCapitalization(true)
            // Same locale/Shift casing as CommitLetter, restricted to the new first code point.
            val first = rendered.substring(offset, end)
            val cased = if (caps.shiftMode.usesUppercase) first.uppercase(caps.language.locale)
                else first // Manual lowercase suppresses this automatic edit; never lower explicit text.
            rendered = rendered.substring(0, offset) + cased + rendered.substring(end)
        }
        if (rendered == plan.undoOriginal && plan.kind != MechanicalEditKind.DOUBLE_SPACE_PERIOD) {
            return TypingTextResult.BYPASS
        }
        if (rendered.length > MAX_COMPOSING_UTF16 || rendered.codePointCount(0, rendered.length) > 128) {
            return TypingTextResult.BYPASS
        }
        val current = punctuationEvidence() ?: return TypingTextResult.REJECTED
        if (plan.sessionId != current.sessionId || plan.revision != current.revision ||
            plan.expectedComposing != current.composingText || current.text != owned.text
        ) return TypingTextResult.REJECTED
        val previous = state.composing
        val start = if (previous == null) selectionStart else composingStart
        val caret = start.toLong() + rendered.length
        val undoCaret = start.toLong() + plan.undoOriginal.length
        if (caret > Int.MAX_VALUE || undoCaret > Int.MAX_VALUE) return TypingTextResult.BYPASS
        val before = context!!.text
        val rawContext = SessionTextContext(graphemes).apply {
            restore(before.dropLast(previous?.text?.length ?: 0))
            append(plan.undoOriginal)
        }.text
        val next = splitComposition(rendered)
        val restore = splitComposition(plan.undoOriginal)
        val expected = EditorSelection(caret.toInt(), caret.toInt(), start, caret.toInt())
        return applyEdit(TypingEdit.SetComposingText(rendered), expected, execute) {
            // The read-only prefix is never sent to the editor or adopted as composing.
            context!!.restore(before.dropLast(previous?.text?.length ?: 0))
            context!!.append(rendered)
            composingStart = start
            sentenceCapitalizationPending = plan.kind == MechanicalEditKind.DOUBLE_SPACE_PERIOD
            state = state.copy(composing = next,
                originalSelected = state.originalSelected && previous?.typedWord?.isNotEmpty() == true,
                lastAutoEdit = UndoableTextEdit(plan.undoOriginal, rendered, state.sessionId,
                    state.revision, restore, rawContext))
            publish()
            diagnose(DiagnosticKind.BOUNDARY, DiagnosticReason.AUTO_REPLACE) {
                DiagnosticText(context = context?.text.orEmpty(), original = plan.undoOriginal, result = rendered)
            }
        }
    }

    private fun splitComposition(text: String): ComposingSegment {
        var start = text.length
        while (start > 0 && isWordCodePoint(text.codePointBefore(start))) {
            start -= Character.charCount(text.codePointBefore(start))
        }
        return ComposingSegment(text.substring(0, start), text.substring(start))
    }

    private fun isEligibleLocalReplacement(selection: CandidateSelection): Boolean {
        val ranking = selection.ranking ?: return false
        if (ranking.usedModel || ranking.preferredId <= 0 || selection.generation.prohibitsAutoReplace) return false
        return if (CommonConfusions.preferredId(selection.generation, selection.language) == ranking.preferredId)
            spellingQualification.allowsCommonConfusion(selection.language)
        else spellingQualification.allowsGeneralLocal(selection.language)
    }

    /** Latest accepted numeric decision only. No scoring, waiting, editor reads or text reconstruction. */
    private fun applyBoundaryCorrection(boundary: String, policy: MechanicalPunctuationPolicy,
        keyboard: KeyboardState, mode: AutocorrectionMode, execute: (TypingEdit) -> Boolean): TypingTextResult {
        val closesComposition = boundary.isEmpty() || boundary == "\n"
        if (mode != AutocorrectionMode.HIGH_CONFIDENCE ||
            (!closesComposition && (boundary.length != 1 || boundary[0] !in PENDING_BOUNDARY)) ||
            policy.inputPolicy != InputPolicy.NORMAL ||
            policy.mode != EditorMode.TEXT || policy.requiresRawKeyEvents || keyboard.layer != KeyboardLayer.LETTERS ||
            !canRequestCandidates) return boundaryBypass(DiagnosticReason.INELIGIBLE)
        // A first dot/colon can still start a hostname or URI scheme. Do not change a word
        // before that shape becomes distinguishable; the boundary must never wait for context.
        if (boundary == "." || boundary == ":") return boundaryBypass(DiagnosticReason.PROTECTED_FORM)
        val selection = candidateSelection ?: return boundaryBypass(DiagnosticReason.NO_CANDIDATES)
        val ranking = selection.ranking ?: return boundaryBypass(DiagnosticReason.NO_RANKING)
        val canonicalCase = selection.generation.isCanonicalCaseCorrection()
        val automaticEligible = if (canonicalCase) {
            val candidate = selection.generation.alternatives.single()
            candidate.canonicalCaseUnambiguous && candidate.canonicalCaseAutoEligible
        } else !selection.generation.prohibitsAutoReplace &&
            if (ranking.usedModel) spellingQualification.allowsModel(selection.language)
            else isEligibleLocalReplacement(selection)
        if (selection.language != keyboard.language || ranking.preferredId <= 0 ||
            !automaticEligible) {
            return boundaryBypass(DiagnosticReason.POLICY_REJECTED)
        }
        val previous = state.composing ?: return boundaryBypass(DiagnosticReason.OWNERSHIP_REJECTED)
        val word = selection.alternatives.getOrNull(ranking.preferredId - 1)?.text ?: return boundaryBypass(DiagnosticReason.INVALID)
        val corrected = previous.copy(typedWord = word)
        val owned = punctuationEvidence() ?: return boundaryBypass(DiagnosticReason.OWNERSHIP_REJECTED)
        // A composing fragment after '@', '/', '.', a code operator, or an unknown editor
        // prefix is not proof of a whole ordinary token. Only Rune whitespace/document start
        // establishes the boundary; never read the editor to manufacture that evidence.
        val tokenStart = owned.text.indexOfLast { it.isWhitespace() } + 1
        if (tokenStart == 0 && !owned.startsAtTokenBoundary ||
            owned.text.substring(tokenStart) != previous.typedWord) return boundaryBypass(DiagnosticReason.OWNERSHIP_REJECTED)
        val virtual = OwnedPunctuationSuffix(owned.text.dropLast(previous.text.length) + corrected.text,
            corrected.text, owned.startsAtTokenBoundary, owned.sessionId, owned.revision)
        val punctuation = if (closesComposition) null else trace.section(SmartTypingTraceSection.PUNCTUATION_RULE) {
            MechanicalPunctuationPlanner.plan(virtual, PunctuationAction.Text(boundary), policy)
        } as? MechanicalPunctuationPlan.Replace
        val rendered = punctuation?.replacementComposing ?: (corrected.text + boundary)
        if (!rendered.endsWith(boundary) || rendered.length > MAX_COMPOSING_UTF16 ||
            rendered.codePointCount(0, rendered.length) > 128) return boundaryBypass(DiagnosticReason.LIMIT)
        val start = composingStart
        val caret = start.toLong() + rendered.length
        if (caret > Int.MAX_VALUE) return boundaryBypass(DiagnosticReason.LIMIT)
        val end = caret.toInt()
        val boundaryStart = end - boundary.length
        val before = context!!.text
        val next = if (closesComposition) null else ComposingSegment(leadingBoundary = boundary)
        // Intermediate commit acknowledgement can arrive synchronously before region creation.
        remember(EditorSelection(end, end, -1, -1))
        val edits = if (next == null) listOf(TypingEdit.CommitText(rendered)) else
            listOf(TypingEdit.CommitText(rendered), TypingEdit.SetComposingRegion(boundaryStart, end))
        val expected = if (next == null) EditorSelection(end, end, -1, -1) else
            EditorSelection(end, end, boundaryStart, end)
        diagnose(DiagnosticKind.BOUNDARY, DiagnosticReason.AUTO_REPLACE, selection.alternatives.size,
            ranking.preferredId - 1, ranking.usedModel) { diagnosticText(input = boundary, result = rendered) }
        return trace.section(SmartTypingTraceSection.CORRECTION_COMMIT) {
            applyGuardedBatch(edits, expected, execute) {
                check(context!!.replaceSuffix(previous.text, rendered)) { "Correction ownership mismatch" }
                composingStart = if (next == null) -1 else boundaryStart
                state = state.copy(composing = next, originalSelected = false,
                    lastAutoEdit = UndoableTextEdit(previous.text, rendered, state.sessionId, state.revision,
                        previous, before, start, next,
                        UndoCorrectionCandidates(selection.generation, selection.language, selection.requestId)))
                publish()
            }
        }
    }

    private fun restoreBoundaryCorrection(edit: UndoableTextEdit, execute: (TypingEdit) -> Boolean): TypingTextResult {
        val start = edit.committedStart ?: return TypingTextResult.REJECTED
        val end = start.toLong() + edit.applied.length
        if (edit.sessionId != state.sessionId || edit.revision != state.revision ||
            state.composing != edit.composingAfter || selectionStart != selectionEnd || selectionStart.toLong() != end ||
            (edit.composingAfter == null && composingStart != -1) ||
            (edit.composingAfter != null && composingStart.toLong() != end - edit.composingAfter.text.length) ||
            context?.text?.endsWith(edit.applied) != true) {
            // Uncertain committed text must not be adopted as a new composing span.
            disableSession()
            return TypingTextResult.REJECTED
        }
        val caret = start + edit.original.length
        remember(EditorSelection(selectionStart, selectionEnd, start, end.toInt()))
        return trace.section(SmartTypingTraceSection.CORRECTION_UNDO) {
            applyGuardedBatch(listOf(TypingEdit.SetComposingRegion(start, end.toInt()),
                TypingEdit.SetComposingText(edit.original)), EditorSelection(caret, caret, start, caret), execute) {
                composingStart = start
                context!!.restore(edit.contextBefore)
                state = state.copy(composing = edit.restoreComposition, originalSelected = true)
                edit.correction?.let { saved ->
                    candidateSelection = CandidateSelection(saved.generation, saved.language, saved.requestId,
                        selectedIndex = -1, manual = true)
                }
                publish()
                diagnose(DiagnosticKind.UNDO, DiagnosticReason.ACCEPTED) { diagnosticText(result = edit.original) }
            }
        }
    }

    private fun applyGuardedBatch(edits: List<TypingEdit>, expected: EditorSelection,
        execute: (TypingEdit) -> Boolean, accepted: () -> Unit): TypingTextResult {
        val session = state.sessionId
        val revision = state.revision + 1
        val epoch = candidateEpoch + 1
        val batch = TypingEdit.Batch(edits) {
            state.enabled && state.sessionId == session && state.revision == revision && candidateEpoch == epoch
        }
        return applyEdit(batch, expected, execute, accepted)
    }

    /** Settings and non-text boundaries can close Undo without making an editor call. */
    fun discardUndo() {
        if (state.lastAutoEdit != null) state = state.copy(lastAutoEdit = null)
        sentenceCapitalizationPending = false
    }

    /** Returns true when the callback cannot be attributed to a recent Rune edit. */
    fun updateSelection(
        newStart: Int,
        newEnd: Int,
        candidatesStart: Int,
        candidatesEnd: Int,
        execute: (TypingEdit) -> Boolean,
    ): Boolean {
        if (!state.enabled) return false
        val incoming = EditorSelection(newStart, newEnd, candidatesStart, candidatesEnd)
        if (expectedSelections.contains(incoming)) {
            // Framework callbacks are ordered but may coalesce several edits. Retire that prefix;
            // an acknowledged historical span must never authorize a later editor replacement.
            while (expectedSelections.removeFirst() != incoming) Unit
            lastAcknowledgedSelection = incoming
            return false
        }
        if (incoming == lastAcknowledgedSelection && incoming == expectedEditorSelection) return false
        // A duplicate initial callback is harmless, but losing a live composing region is not.
        if (state.composing == null && newStart == selectionStart && newEnd == selectionEnd &&
            candidatesStart == -1 && candidatesEnd == -1
        ) return false

        sentenceCapitalizationPending = false
        val hadComposition = state.composing != null ||
            (expectedEditorSelection?.composingStart ?: -1) >= 0
        val stillOwnsSpan = state.composing != null && candidatesStart == composingStart &&
            candidatesEnd == composingStart + state.composing!!.text.length
        closeDiagnosticsAdmission()
        clearCandidates()
        context?.clear()
        expectedSelections.clear()
        expectedEditorSelection = null
        lastAcknowledgedSelection = null
        awaitingEditorSelection = false
        plainWordUntilBoundary = false
        state = state.copy(
            composing = null, lastAutoEdit = null, originalSelected = false,
            revision = state.revision + 1,
        )
        composingStart = -1
        selectionStart = newStart
        selectionEnd = newEnd
        publish()
        // Never finish an unknown replacement span and never reapply a stale Rune buffer.
        if (stillOwnsSpan) {
            val expected = EditorSelection(newStart, newEnd, -1, -1)
            applyEdit(TypingEdit.FinishComposingText, expected, execute) {}
        }
        if ((hadComposition && !stillOwnsSpan) || (!stillOwnsSpan && candidatesStart >= 0) ||
            newStart < 0 || newEnd < 0
        ) disableSession()
        return true
    }

    fun endSession() {
        closeDiagnosticsAdmission()
        sentenceCapitalizationPending = false
        clearCandidates()
        context?.clear()
        context = null
        expectedSelections.clear()
        expectedEditorSelection = null
        lastAcknowledgedSelection = null
        awaitingEditorSelection = false
        plainWordUntilBoundary = false
        selectionStart = -1
        selectionEnd = -1
        composingStart = -1
        state = TypingSessionState(sessionId = state.sessionId, revision = state.revision + 1)
    }

    private fun compose(
        next: ComposingSegment,
        addedText: String,
        execute: (TypingEdit) -> Boolean,
    ): TypingTextResult {
        val start = if (state.composing == null) minOf(selectionStart, selectionEnd) else composingStart
        val caret = start + next.text.length
        val expected = EditorSelection(caret, caret, start, caret)
        return applyEdit(TypingEdit.SetComposingText(next.text), expected, execute) {
            composingStart = start
            state = state.copy(composing = next)
            context?.append(addedText)
            publish()
        }
    }

    private fun applyEdit(
        edit: TypingEdit,
        expected: EditorSelection,
        execute: (TypingEdit) -> Boolean,
        accepted: () -> Unit,
    ): TypingTextResult = acknowledgeEdit(
        expected = expected,
        execute = { execute(edit) },
        accepted = accepted,
        rejected = {
            // Freeze any span the editor retained, including an ambiguously applied false result.
            // This never resends text. Subsequent plain commits must not replace an old Rune word.
            if (edit is TypingEdit.SetComposingText || edit is TypingEdit.Batch) {
                // The session is already disabled. A dead connection may also reject cleanup;
                // never retry a text mutation or let cleanup revive the failed operation.
                try { execute(TypingEdit.FinishComposingText) } catch (_: RuntimeException) { Unit }
            }
        },
    )

    private fun acknowledgeEdit(
        expected: EditorSelection,
        execute: () -> Boolean,
        accepted: () -> Unit = {},
        rejected: () -> Unit = {},
    ): TypingTextResult {
        val session = state.sessionId
        val revision = state.revision + 1
        val refused = try { diagnostics.editorOperation(session, revision) } catch (_: Throwable) { null }
        clearCandidates()
        val expectedCandidateEpoch = candidateEpoch
        state = state.copy(revision = revision)
        remember(expected)
        editorEditDepth++
        val handled = try { execute() } finally { editorEditDepth-- }
        if (state.sessionId != session || state.revision != revision) {
            // A reentrant external/lifecycle callback already invalidated this operation.
            // Abort a multi-command action even if this individual editor call succeeded.
            try { refused?.invoke() } catch (_: Throwable) { }
            return TypingTextResult.REJECTED
        }
        if (!handled || candidateEpoch != expectedCandidateEpoch) {
            // Owner policy may invalidate candidates reentrantly without changing the editor
            // session. Freeze an ambiguously applied span; never publish its old allowlist.
            try { refused?.invoke() } catch (_: Throwable) { }
            disableSession()
            rejected()
            return TypingTextResult.REJECTED
        }
        selectionStart = expected.start
        selectionEnd = expected.end
        accepted()
        diagnose(DiagnosticKind.EDITOR, DiagnosticReason.EDITOR_ACCEPTED)
        return TypingTextResult.HANDLED
    }

    private fun remember(selection: EditorSelection) {
        expectedEditorSelection = selection
        if (expectedSelections.peekLast() == selection) return
        if (expectedSelections.size == MAX_EXPECTED_SELECTIONS) expectedSelections.removeFirst()
        expectedSelections.addLast(selection)
    }

    private fun publish() {
        state = state.copy(contextText = context?.text.orEmpty())
    }

    private fun disableSession() {
        closeDiagnosticsAdmission()
        sentenceCapitalizationPending = false
        clearCandidates()
        context?.clear()
        context = null
        expectedSelections.clear()
        expectedEditorSelection = null
        lastAcknowledgedSelection = null
        awaitingEditorSelection = false
        plainWordUntilBoundary = false
        composingStart = -1
        state = state.copy(
            composing = null,
            lastAutoEdit = null,
            originalSelected = false,
            contextText = "",
            enabled = false,
            revision = state.revision + 1,
        )
    }

    private data class EditorSelection(val start: Int, val end: Int, val composingStart: Int, val composingEnd: Int)

    private data class CandidateStamp(val sessionId: Long, val revision: Long, val requestId: Long,
        val language: KeyboardLanguage)

    private class ModelRankingStamp(val token: ScoringToken, val selection: CandidateSelection)
    private class SpaceCorrectionStamp(val ranking: ModelRankingStamp, val previous: ComposingSegment,
        val start: Int, val contextBefore: String, var revisionAfterSpace: Long = -1)
    private class ContextualRankingStamp(val token: ScoringToken, val selection: CandidateSelection,
        val variants: List<ContextualPunctuationEngine.Variant>)
    private class ContextualSelection(val token: ScoringToken, val selection: CandidateSelection,
        val variant: ContextualPunctuationEngine.Variant, val variants: List<ContextualPunctuationEngine.Variant>)

    private data class CandidateSelection(
        val generation: CandidateGeneration,
        val language: KeyboardLanguage,
        val requestId: Long,
        val selectedIndex: Int,
        val manual: Boolean = false,
        val order: List<Int> = generation.alternatives.indices.toList(),
        val modelRanked: Boolean = false,
        val ranking: CalibratedRanking? = null,
    ) {
        val original get() = generation.original!!
        val alternatives get() = generation.alternatives
        val completion get() = generation.completion
        val visibleIndices get() = order.take(SmartTypingViewState.MAX_VISIBLE_CANDIDATES - 1)
        override fun toString(): String = "CandidateSelection(redacted)"
    }

    private companion object {
        const val MAX_COMPOSING_UTF16 = 256
        const val MAX_EXPECTED_SELECTIONS = 512
        const val PENDING_BOUNDARY = " ,.!?:;"

        fun isWordCodePoint(codePoint: Int): Boolean {
            val type = Character.getType(codePoint)
            return Character.isLetter(codePoint) || type == Character.NON_SPACING_MARK.toInt() ||
                type == Character.COMBINING_SPACING_MARK.toInt() ||
                type == Character.ENCLOSING_MARK.toInt()
        }

        fun CandidateGeneration.isCanonicalCaseCorrection(): Boolean =
            completion == CandidateCompletion.VALID_WORD && isValidWord && protectedReason == null &&
                alternatives.size == 1 && alternatives[0].kind == GeneratedCandidateKind.CANONICAL_CASE
    }
}
