package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CalibratedSpellingPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CanonicalCaseLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRoute
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRouter
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LazyPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateWorker
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.NoopSmartTypingTracer
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTracer
import java.util.concurrent.Executor

/** Only non-text live eligibility. The service derives editorAllowsSmartTyping from EditorContext. */
data class CandidateOwnerState(
    val editorAllowsSmartTyping: Boolean,
    val inputViewActive: Boolean,
    val layer: KeyboardLayer,
    val language: KeyboardLanguage,
    val hasSelection: Boolean,
    val autocorrectionMode: AutocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE,
    val candidateStripEnabled: Boolean = true,
    val deterministicAutoReplaceQualified: Boolean = false,
    val modelAutoReplaceQualified: Boolean = false,
    val modelRuntimeQualified: Boolean = true,
    val contextualPunctuationEnabled: Boolean = false,
    val contextualModelReady: Boolean = false,
) {
    val baseEligible: Boolean
        get() = editorAllowsSmartTyping && inputViewActive && layer == KeyboardLayer.LETTERS && !hasSelection
    val spellingEnabled: Boolean
        get() = autocorrectionMode != AutocorrectionMode.OFF
    val showsCandidates: Boolean
        get() = baseEligible && candidateStripEnabled
    private val automaticMode: Boolean
        get() = autocorrectionMode == AutocorrectionMode.HIGH_CONFIDENCE
    /** Retrieval serves visible suggestions and either qualified automatic branch. */
    val canRequestSpelling: Boolean
        get() = baseEligible && spellingEnabled && (candidateStripEnabled ||
            automaticMode && (deterministicAutoReplaceQualified ||
                modelAutoReplaceQualified && modelRuntimeQualified))
    /** A hidden strip and deterministic-only qualification must not bind the model process. */
    val canRequestModelSpelling: Boolean
        get() = modelRuntimeQualified && baseEligible && spellingEnabled &&
            (candidateStripEnabled || automaticMode && modelAutoReplaceQualified)
    val canRequestContextual: Boolean
        get() = modelRuntimeQualified && baseEligible && candidateStripEnabled &&
            contextualPunctuationEnabled && contextualModelReady
    val canRequestCandidateWork: Boolean
        get() = canRequestSpelling || canRequestContextual
    val canActivateAnyModelCandidate: Boolean
        get() = modelRuntimeQualified && (canRequestModelSpelling ||
            baseEligible && candidateStripEnabled && contextualPunctuationEnabled)
}

/** Main owner only; readiness never calls back, renders never submit, and no request survives a boundary. */
class LocalCandidateCoordinator internal constructor(
    private val controller: TypingSessionController,
    private val lexicon: CandidateLexicon,
    private val requestRoute: (LanguageRoute) -> Boolean,
    private val routeReady: (LanguageRoute) -> Boolean,
    private val invalidateLoads: () -> Unit,
    private val closeLoads: () -> Unit,
    private val ownerDispatcher: Executor,
    ownerState: () -> CandidateOwnerState,
    onCandidatesChanged: () -> Unit,
    private val modelRanking: ModelCandidateCoordinator? = null,
    private val trace: SmartTypingTracer = NoopSmartTypingTracer,
    private val canonicalCaseLexicon: CanonicalCaseLexicon = CanonicalCaseLexicon.EMPTY,
) : AutoCloseable {
    constructor(
        controller: TypingSessionController,
        lexicons: LazyPackedLexicons,
        ownerDispatcher: Executor,
        ownerState: () -> CandidateOwnerState,
        onCandidatesChanged: () -> Unit,
        modelRanking: ModelCandidateCoordinator? = null,
        trace: SmartTypingTracer = NoopSmartTypingTracer,
        canonicalCaseLexicon: CanonicalCaseLexicon = CanonicalCaseLexicon.EMPTY,
    ) : this(controller, lexicons.lexicon, lexicons::request, lexicons::isReady,
        lexicons::invalidate, lexicons::close, ownerDispatcher, ownerState, onCandidatesChanged,
        modelRanking, trace, canonicalCaseLexicon)

    private val ownerThread = Thread.currentThread()
    private var ownerState: (() -> CandidateOwnerState)? = ownerState
    private var onCandidatesChanged: (() -> Unit)? = onCandidatesChanged
    private var worker: LocalCandidateWorker? = null
    private var pending: Pending? = null
    private var epoch = 0L
    private var requestId = 0L
    private var closed = false

    val modelReadinessHint: io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
        get() {
            checkOwner()
            return modelRanking?.modelReadinessHint
                ?: io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint.MISSING
        }

    /** Wrap only actual typing commands. Their controller result decides whether admission is allowed. */
    fun edit(action: () -> TypingTextResult): TypingTextResult {
        checkOwner()
        if (closed) return action()
        // Retain the latest accepted decision until this action consumes its exact word.
        // Cancel worker/callback ownership first, so late work cannot race a boundary commit.
        val owner = ownerState?.invoke()
        cancelCandidates(clearAllowlist = owner?.canRequestCandidateWork != true)
        val editEpoch = epoch
        val session = controller.state.sessionId
        val revision = controller.state.revision
        val result = action()
        if (!closed && epoch == editEpoch && controller.state.sessionId == session &&
            controller.state.revision != revision && result == TypingTextResult.HANDLED) {
            requestCurrentWord()
        } else if (!closed && epoch == editEpoch) {
            controller.clearCandidates()
            invalidateLoads()
        }
        return result
    }

    /** Session/view/language/layer/privacy/cursor/boundary invalidation; never waits for computation. */
    fun invalidate() {
        checkOwner()
        if (closed) return
        cancelCandidates(clearAllowlist = true)
        modelRanking?.invalidate()
        invalidateLoads()
    }

    /** A tap must retain its current allowlist until the controller resolves the ID. */
    fun selectCandidate(id: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        checkOwner()
        val owner = ownerState?.invoke()
        if (closed || owner?.showsCandidates != true || !controller.ownsCandidateComposition) {
            invalidate()
            return TypingTextResult.REJECTED
        }
        val item = viewState.candidates.firstOrNull { it.id == id } ?: return TypingTextResult.REJECTED
        if (item is CandidateUiItem.Correction && !owner.spellingEnabled) return TypingTextResult.REJECTED
        if (item is CandidateUiItem.Punctuation && !owner.canRequestContextual) return TypingTextResult.REJECTED
        cancelCandidates(clearAllowlist = false)
        invalidateLoads()
        // Under OFF, Original can acknowledge only the current spelling, never restore a prior
        // manual correction if a caller changed policy without clearing its old metadata.
        if (!owner.spellingEnabled && item !is CandidateUiItem.Punctuation) {
            return if (controller.selectOriginal(id)) TypingTextResult.HANDLED else TypingTextResult.REJECTED
        }
        return controller.selectCandidate(id, execute)
    }

    /** Pure presentation: calling this cannot request a route or submit a job. */
    val viewState: SmartTypingViewState
        get() {
            checkOwner()
            val owner = ownerState?.invoke()
            if (closed || owner?.showsCandidates != true) return SmartTypingViewState.HIDDEN
            val view = controller.candidateViewState
            if (!view.enabled) return view
            if (owner.spellingEnabled) {
                if (owner.canRequestContextual || view.candidates.none { it is CandidateUiItem.Punctuation }) return view
                val visible = view.candidates.filterNot { it is CandidateUiItem.Punctuation }
                val selected = view.selectedCandidateId?.takeIf { id -> visible.any { it.id == id } }
                    ?: visible.firstOrNull()?.id
                return SmartTypingViewState(true, visible, selected)
            }
            val originalId = controller.originalCandidateId ?: return SmartTypingViewState.EMPTY
            val original = CandidateUiItem.Original(originalId, controller.state.composing!!.typedWord)
            val contextual = view.candidates.filterIsInstance<CandidateUiItem.Punctuation>().take(1)
            return SmartTypingViewState(true, listOf(original) + contextual, original.id)
        }

    override fun close() {
        checkOwner()
        if (closed) return
        cancelCandidates(clearAllowlist = true)
        closed = true
        worker?.close()
        worker = null
        closeLoads()
        modelRanking?.close()
        ownerState = null
        onCandidatesChanged = null
    }

    private fun requestCurrentWord() {
        val owner = ownerState?.invoke() ?: return
        if (!owner.canRequestCandidateWork || !controller.canRequestCandidates) {
            invalidateLoads()
            return
        }
        val route = LanguageRouter.route(controller.state.composing!!.typedWord, owner.language)
        if (!requestRoute(route)) return
        // No worker is created until the complete route is ready; later Ready additions use its bridge.
        val target = worker ?: LocalCandidateWorker(CandidateGenerator(lexicon,
            CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES, canonicalCaseLexicon),
            ownerDispatcher, ::acceptReply, trace)
            .also { worker = it }
        if (requestId == Long.MAX_VALUE) return
        val request = controller.beginCandidateRequest(++requestId, owner.language) ?: return
        pending = Pending(request.sessionId, request.revision, request.requestId, owner.language, epoch)
        if (!target.submit(request)) {
            pending = null
            controller.clearCandidates()
        }
    }

    private fun acceptReply(reply: LocalCandidateReply) {
        checkOwner()
        val current = pending ?: return
        if (closed || current.epoch != epoch || reply.sessionId != current.sessionId ||
            reply.revision != current.revision || reply.requestId != current.requestId) return
        val owner = ownerState?.invoke()
        val typing = controller.state
        val original = typing.composing?.typedWord
        if (owner?.canRequestCandidateWork != true || owner.language != current.language ||
            typing.sessionId != current.sessionId || typing.revision != current.revision ||
            !controller.canRequestCandidates || original == null || reply.generation.original != original ||
            !routeReady(LanguageRouter.route(original, owner.language))) {
            invalidate()
            return
        }
        pending = null
        if (controller.acceptCandidates(reply)) {
            onCandidatesChanged?.invoke()
            modelRanking?.candidatesChanged()
        }
    }

    private fun cancelCandidates(clearAllowlist: Boolean) {
        modelRanking?.cancel()
        epoch++
        pending = null
        worker?.cancel()
        if (clearAllowlist) controller.clearCandidates()
    }

    private fun checkOwner() {
        check(Thread.currentThread() === ownerThread) { "Candidate coordinator owner thread required" }
    }

    private data class Pending(
        val sessionId: Long,
        val revision: Long,
        val requestId: Long,
        val language: KeyboardLanguage,
        val epoch: Long,
    )
}
