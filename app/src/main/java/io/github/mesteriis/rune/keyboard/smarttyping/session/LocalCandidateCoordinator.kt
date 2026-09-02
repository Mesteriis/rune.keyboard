package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRoute
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRouter
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LazyPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateWorker
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import java.util.concurrent.Executor

/** Only non-text live eligibility. The service derives editorAllowsSmartTyping from EditorContext. */
data class CandidateOwnerState(
    val editorAllowsSmartTyping: Boolean,
    val inputViewActive: Boolean,
    val layer: KeyboardLayer,
    val language: KeyboardLanguage,
    val hasSelection: Boolean,
) {
    val eligible: Boolean
        get() = editorAllowsSmartTyping && inputViewActive && layer == KeyboardLayer.LETTERS && !hasSelection
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
) : AutoCloseable {
    constructor(
        controller: TypingSessionController,
        lexicons: LazyPackedLexicons,
        ownerDispatcher: Executor,
        ownerState: () -> CandidateOwnerState,
        onCandidatesChanged: () -> Unit,
    ) : this(controller, lexicons.lexicon, lexicons::request, lexicons::isReady,
        lexicons::invalidate, lexicons::close, ownerDispatcher, ownerState, onCandidatesChanged)

    private val ownerThread = Thread.currentThread()
    private var ownerState: (() -> CandidateOwnerState)? = ownerState
    private var onCandidatesChanged: (() -> Unit)? = onCandidatesChanged
    private var worker: LocalCandidateWorker? = null
    private var pending: Pending? = null
    private var epoch = 0L
    private var requestId = 0L
    private var closed = false

    /** Wrap only actual typing commands. Their controller result decides whether admission is allowed. */
    fun edit(action: () -> TypingTextResult): TypingTextResult {
        checkOwner()
        if (closed) return action()
        cancelCandidates(clearAllowlist = true)
        val editEpoch = epoch
        val session = controller.state.sessionId
        val revision = controller.state.revision
        val result = action()
        if (!closed && epoch == editEpoch && controller.state.sessionId == session &&
            controller.state.revision != revision && result == TypingTextResult.HANDLED) {
            requestCurrentWord()
        } else if (!closed && epoch == editEpoch) {
            invalidateLoads()
        }
        return result
    }

    /** Session/view/language/layer/privacy/cursor/boundary invalidation; never waits for computation. */
    fun invalidate() {
        checkOwner()
        if (closed) return
        cancelCandidates(clearAllowlist = true)
        invalidateLoads()
    }

    /** A tap must retain its current allowlist until the controller resolves the ID. */
    fun selectCandidate(id: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        checkOwner()
        if (closed || ownerState?.invoke()?.eligible != true || !controller.ownsCandidateComposition) {
            invalidate()
            return TypingTextResult.REJECTED
        }
        if (controller.candidateViewState.candidates.none { it.id == id }) return TypingTextResult.REJECTED
        cancelCandidates(clearAllowlist = false)
        invalidateLoads()
        return controller.selectCandidate(id, execute)
    }

    /** Pure presentation: calling this cannot request a route or submit a job. */
    val viewState: SmartTypingViewState
        get() {
            checkOwner()
            return if (closed || ownerState?.invoke()?.eligible != true) SmartTypingViewState.HIDDEN
            else controller.candidateViewState
        }

    override fun close() {
        checkOwner()
        if (closed) return
        cancelCandidates(clearAllowlist = true)
        closed = true
        worker?.close()
        worker = null
        closeLoads()
        ownerState = null
        onCandidatesChanged = null
    }

    private fun requestCurrentWord() {
        val owner = ownerState?.invoke() ?: return
        if (!owner.eligible || !controller.canRequestCandidates) {
            invalidateLoads()
            return
        }
        val route = LanguageRouter.route(controller.state.composing!!.typedWord, owner.language)
        if (!requestRoute(route)) return
        // No worker is created until the complete route is ready; later Ready additions use its bridge.
        val target = worker ?: LocalCandidateWorker(CandidateGenerator(lexicon), ownerDispatcher, ::acceptReply)
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
        if (owner?.eligible != true || owner.language != current.language ||
            typing.sessionId != current.sessionId || typing.revision != current.revision ||
            !controller.canRequestCandidates || original == null || reply.generation.original != original ||
            !routeReady(LanguageRouter.route(original, owner.language))) {
            invalidate()
            return
        }
        pending = null
        if (controller.acceptCandidates(reply)) onCandidatesChanged?.invoke()
    }

    private fun cancelCandidates(clearAllowlist: Boolean) {
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
