package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessSource
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityModelResponse
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticReason
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticSource
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.NoopSmartTypingTracer
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTracer
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.section

/** Owner-thread scheduling seam. A delayed task contains numeric identity only, never input text. */
interface ModelPauseScheduler {
    fun postDelayed(task: Runnable, millis: Long)
    fun remove(task: Runnable)
    fun nowMillis(): Long = System.nanoTime() / 1_000_000
}

/**
 * Local candidates are ready immediately; model results rank only that allowlist.
 * Eligibility/readiness are cached owner facts. Neither a timer nor a reconnect replays old input.
 */
class ModelCandidateCoordinator(
    private val controller: TypingSessionController,
    clientFactory: (ModelScoringListener) -> ModelScoringClient,
    private val scheduler: ModelPauseScheduler,
    private val ownerState: () -> CandidateOwnerState,
    private val readiness: ModelReadinessSource,
    private val changed: () -> Unit,
    private val trace: SmartTypingTracer = NoopSmartTypingTracer,
) : ModelScoringListener, AutoCloseable {
    private val ownerThread = Thread.currentThread()
    private val client = clientFactory(this)
    private var timer: Runnable? = null
    private var epoch = 0L
    private var requestId = 0L
    private var closed = false
    private var pendingOwner: CandidateOwnerState? = null
    private var pendingKind: RequestKind? = null
    private var spaceStartedAt = 0L
    private var spaceExecutor: ((TypingEdit) -> Boolean)? = null
    private var diagnosticRequest: ScoringToken? = null
    private var diagnosticScheduled: Pair<Long, Long>? = null
    private var diagnosticSource = DiagnosticSource.MODEL
    // Numeric identities only. Keep a bounded sample of cancelled requests for their late replies.
    private val qualityResponses = LinkedHashMap<ScoringToken, QualityModelResponse>()
    internal var onPreviousWordRefined: (() -> Unit)? = null

    /** Cached metadata only, independent of transport connectivity and quality qualification. */
    val modelReadinessHint: ModelReadinessHint
        get() { checkOwner(); return readiness.hint }

    /** Actual eligible text edit only: overlap weight loading with typing/local lexicon loading. */
    fun prepareForEdit() {
        checkOwner()
        if (closed) return
        readiness.setActive(featureEligible())
        client.attachSession(controller.state.sessionId, eligible())
    }

    /** Called only after a newly accepted local candidate result, never by rendering/readiness. */
    fun candidatesChanged() {
        checkOwner()
        if (closed) return
        if (pendingKind == RequestKind.REFINEMENT && controller.canRefinePreviousWord) return
        cancel()
        val session = controller.state.sessionId
        val revision = controller.state.revision
        readiness.setActive(featureEligible())
        if (!eligible()) { client.attachSession(session, false); return }
        // A valid word does not score, but must not abort payload-free weight loading for
        // this still-eligible text session. Idle unload and session invalidation remain active.
        val kind = requestKind() ?: return
        diagnosticSource = if (kind == RequestKind.CONTEXTUAL) DiagnosticSource.CONTEXTUAL else DiagnosticSource.MODEL
        diagnosticScheduled = session to revision
        controller.recordRequest(DiagnosticReason.SCHEDULED, diagnosticSource, session, revision)
        val owner = ownerState()
        client.attachSession(session, true)
        val scheduledEpoch = epoch
        val task = object : Runnable {
            override fun run() {
                checkOwner()
                if (closed || timer !== this || epoch != scheduledEpoch) return
                timer = null
                if (!eligible() || requestKind() != kind || ownerState() != owner || controller.state.sessionId != session ||
                    controller.state.revision != revision || !client.available || requestId == Long.MAX_VALUE) {
                    controller.recordRequest(if (!client.available) DiagnosticReason.SERVICE_REFUSED else DiagnosticReason.CANCELLED,
                        diagnosticSource, session, revision)
                    diagnosticScheduled = null
                    return
                }
                val nextId = ++requestId
                val input = when (kind) {
                    RequestKind.SPELLING -> controller.beginModelRanking(nextId)
                    RequestKind.CONTEXTUAL -> controller.beginContextualRanking(nextId)
                    RequestKind.REFINEMENT -> null
                } ?: return
                pendingOwner = owner
                pendingKind = kind
                diagnosticRequest = input.token
                diagnosticScheduled = null
                trace.section(SmartTypingTraceSection.MODEL_REQUEST) {
                    captureQualityResponse(input.token)
                    client.score(input)
                }
            }
        }
        timer = task
        scheduler.postDelayed(task, PAUSE_MILLIS)
    }

    /** Text/tap action barrier. Retain the binding within the same eligible session. */
    fun cancel() {
        checkOwner()
        if (closed) return
        diagnosticRequest?.let { controller.recordRequest(DiagnosticReason.CANCELLED, diagnosticSource,
            it.sessionId, it.revision, it.requestId) }
        diagnosticScheduled?.let { controller.recordRequest(DiagnosticReason.CANCELLED, diagnosticSource, it.first, it.second) }
        if (pendingKind == RequestKind.REFINEMENT) controller.cancelPreviousWordRefinement()
        diagnosticRequest = null
        diagnosticScheduled = null
        epoch++
        pendingOwner = null
        pendingKind = null
        spaceExecutor = null
        timer?.let(scheduler::remove); timer = null
        controller.cancelModelRanking()
        client.cancel()
    }

    /** Only acknowledged next-word appends keep a refinement; the controller owns that decision. */
    internal fun edit(action: () -> TypingTextResult): TypingTextResult {
        if (pendingKind != RequestKind.REFINEMENT) cancel()
        val result = action()
        if (pendingKind == RequestKind.REFINEMENT && !controller.canRefinePreviousWord) cancel()
        return result
    }

    internal fun startPreviousWordRefinement(execute: (TypingEdit) -> Boolean): Boolean {
        checkOwner()
        if (closed || !controller.canRefinePreviousWord || !automaticSpaceEligible() || requestId == Long.MAX_VALUE) return false
        // One replacement request is allowed after local application; old scoring cannot outlive it.
        cancel()
        val input = controller.beginPreviousWordRefinement(++requestId) ?: return false
        pendingOwner = ownerState()
        pendingKind = RequestKind.REFINEMENT
        diagnosticSource = DiagnosticSource.MODEL_REFINEMENT
        diagnosticRequest = input.token
        spaceExecutor = execute
        val currentEpoch = epoch
        val expiry = object : Runnable {
            override fun run() {
                if (timer === this && epoch == currentEpoch) cancel()
            }
        }
        timer = expiry
        scheduler.postDelayed(expiry, controller.previousWordRemainingMillis())
        client.attachSession(controller.state.sessionId, true)
        trace.section(SmartTypingTraceSection.MODEL_REQUEST) {
            captureQualityResponse(input.token)
            client.score(input)
        }
        return true
    }

    /** Space never waits. Flush its existing pause once and retain only this unchanged suffix. */
    internal fun editSpace(execute: (TypingEdit) -> Boolean, action: () -> TypingTextResult): TypingTextResult {
        checkOwner()
        val owner = ownerState()
        val startedAt = scheduler.nowMillis()
        if (closed || !automaticSpaceEligible() || requestKind() != RequestKind.SPELLING) {
            cancel()
            val result = action()
            if (result == TypingTextResult.HANDLED) startPreviousWordRefinement(execute)
            return result
        }
        timer?.let { task -> scheduler.remove(task); task.run() }
        val editingEpoch = epoch
        val result = controller.retainRankingAcrossSpace(action)
        if (result == TypingTextResult.HANDLED && controller.canRefinePreviousWord) {
            startPreviousWordRefinement(execute)
            return result
        }
        if (closed || epoch != editingEpoch || ownerState() != owner || pendingKind != RequestKind.SPELLING ||
            result != TypingTextResult.HANDLED || !controller.hasSpaceCorrection || !automaticSpaceEligible()) {
            cancel()
            return result
        }
        spaceExecutor = execute
        spaceStartedAt = startedAt
        val expiry = object : Runnable {
            override fun run() {
                checkOwner()
                if (timer === this && epoch == editingEpoch) {
                    diagnosticRequest?.let {
                        recordSpaceExpiry(it)
                        controller.recordRequest(DiagnosticReason.DEADLINE_MISSED,
                            diagnosticSource, it.sessionId, it.revision, it.requestId)
                    }
                    diagnosticRequest = null
                    cancel()
                }
            }
        }
        timer = expiry
        scheduler.postDelayed(expiry, (SPACE_GRACE_MILLIS - (scheduler.nowMillis() - startedAt)).coerceAtLeast(0))
        return result
    }

    /** Starts spelling ranking after a completed local search abstains across an owned Space. */
    internal fun candidatesChangedAcrossSpace(reply: LocalCandidateReply,
        execute: (TypingEdit) -> Boolean, elapsedNanos: Long): Boolean {
        checkOwner()
        val elapsedMillis = (elapsedNanos + 999_999) / 1_000_000
        val owner = ownerState()
        if (closed || elapsedNanos < 0 || elapsedMillis >= SPACE_GRACE_MILLIS ||
            !automaticSpaceEligible() || requestId == Long.MAX_VALUE) return false
        readiness.setActive(featureEligible())
        client.attachSession(controller.state.sessionId, true)
        val input = controller.beginModelRankingAfterLocalSpace(reply, ++requestId) ?: return false
        epoch++
        pendingOwner = owner
        pendingKind = RequestKind.SPELLING
        diagnosticSource = DiagnosticSource.MODEL
        diagnosticRequest = input.token
        diagnosticScheduled = null
        spaceExecutor = execute
        spaceStartedAt = scheduler.nowMillis() - elapsedMillis
        val currentEpoch = epoch
        val expiry = object : Runnable {
            override fun run() {
                checkOwner()
                if (timer === this && epoch == currentEpoch) {
                    diagnosticRequest?.let {
                        recordSpaceExpiry(it)
                        controller.recordRequest(DiagnosticReason.DEADLINE_MISSED,
                            diagnosticSource, it.sessionId, it.revision, it.requestId)
                    }
                    diagnosticRequest = null
                    cancel()
                }
            }
        }
        timer = expiry
        scheduler.postDelayed(expiry, SPACE_GRACE_MILLIS - elapsedMillis)
        trace.section(SmartTypingTraceSection.MODEL_REQUEST) {
            captureQualityResponse(input.token)
            client.score(input)
        }
        return true
    }

    /** Session/view/layer/language/settings/privacy invalidation, not an ordinary keystroke. */
    fun invalidate() {
        checkOwner()
        if (closed) return
        cancel()
        client.attachSession(null, false)
        readiness.setActive(featureEligible())
    }

    override fun currentCompositionRevision(): Long { checkOwner(); return controller.state.revision }
    override fun onDiscardedReply(reply: ScoringReply) {
        checkOwner()
        recordQualityResponse(reply)
        if (spaceExecutor != null && !withinSpaceWindow()) recordSpaceExpiry(reply.token)
        controller.recordScoringReply(reply, DiagnosticReason.STALE)
    }
    override fun isCurrentRequest(token: ScoringToken): Boolean {
        checkOwner()
        val kind = pendingKind ?: return false
        if (kind == RequestKind.REFINEMENT) return controller.isCurrentPreviousWordRefinement(token)
        return if (spaceExecutor != null) withinSpaceWindow() && controller.isCurrentSpaceCorrection(token)
            else isCurrent(kind, token)
    }
    private fun captureQualityResponse(token: ScoringToken) {
        val response = controller.beginQualityModelResponse() ?: return
        qualityResponses[token] = response
        if (qualityResponses.size > MAX_QUALITY_RESPONSES) qualityResponses.remove(qualityResponses.keys.first())
    }

    private fun recordQualityResponse(reply: ScoringReply) {
        val response = qualityResponses.remove(reply.token) ?: return
        if (!closed && ownerState().baseEligible)
            controller.recordQualityModelResponse(response, reply.elapsedMillis)
    }

    private fun recordSpaceExpiry(token: ScoringToken) {
        if (!closed && pendingKind == RequestKind.SPELLING && pendingOwner == ownerState() && automaticSpaceEligible())
            controller.recordModelWindowExpired(token)
    }

    override fun onReply(reply: ScoringReply) {
        trace.section(SmartTypingTraceSection.MODEL_RESULT) {
            checkOwner()
            recordQualityResponse(reply)
            val kind = pendingKind ?: run {
                controller.recordScoringReply(reply, DiagnosticReason.STALE)
                return@section
            }
            val executeSpace = spaceExecutor
            if (executeSpace != null && (if (kind == RequestKind.REFINEMENT) !controller.canRefinePreviousWord else !withinSpaceWindow())) {
                recordSpaceExpiry(reply.token)
                controller.recordRequest(DiagnosticReason.DEADLINE_MISSED, diagnosticSource,
                    reply.token.sessionId, reply.token.revision, reply.token.requestId)
                diagnosticRequest = null
                cancel(); return@section
            }
            if (executeSpace != null && !automaticSpaceEligible()) {
                controller.recordScoringReply(reply, DiagnosticReason.STALE, kind == RequestKind.CONTEXTUAL)
                cancel(); return@section
            }
            if (closed || (executeSpace == null && !eligible()) || pendingOwner != ownerState() ||
                !isCurrentRequest(reply.token)) {
                controller.recordScoringReply(reply, DiagnosticReason.STALE, kind == RequestKind.CONTEXTUAL)
                return@section
            }
            if (reply.code == ScoringCode.NO_MODEL || reply.code == ScoringCode.LOAD_FAILED) {
                controller.recordScoringReply(reply, contextual = kind == RequestKind.CONTEXTUAL)
                diagnosticRequest = null
                cancel(); client.attachSession(null, false); readiness.setActive(false)
                return@section
            }
            val accepted = if (executeSpace != null && kind == RequestKind.REFINEMENT)
                controller.acceptPreviousWordRefinement(reply, executeSpace)
            else if (executeSpace != null) controller.acceptSpaceCorrection(reply, executeSpace) else when (kind) {
                RequestKind.SPELLING -> controller.acceptModelRanking(reply)
                RequestKind.CONTEXTUAL -> controller.acceptContextualRanking(reply)
                RequestKind.REFINEMENT -> false
            }
            pendingOwner = null
            pendingKind = null
            diagnosticRequest = null
            spaceExecutor = null
            timer?.let(scheduler::remove); timer = null
            if (accepted) {
                if (kind == RequestKind.REFINEMENT) onPreviousWordRefined?.invoke()
                changed()
            }
        }
    }
    override fun onAvailabilityChanged(available: Boolean) {
        checkOwner()
        if (!available && !closed) {
            diagnosticRequest?.let { controller.recordRequest(DiagnosticReason.SERVICE_REFUSED, diagnosticSource,
                it.sessionId, it.revision, it.requestId) }
            diagnosticScheduled?.let { controller.recordRequest(DiagnosticReason.SERVICE_REFUSED, diagnosticSource,
                it.first, it.second) }
            cancel()
        }
        // A new connection never resubmits an earlier composition.
    }
    /** Parent shutdown can cancel synchronously before reaching this coordinator's close. */
    internal fun discardQualityResponseAdmissions() { checkOwner(); qualityResponses.clear() }

    override fun close() {
        checkOwner()
        if (closed) return
        discardQualityResponseAdmissions()
        cancel(); closed = true; client.close(); readiness.close()
    }
    private fun featureEligible() = !closed && ownerState().canActivateAnyModelCandidate && controller.state.enabled
    private fun eligible() = featureEligible() && readiness.hint == ModelReadinessHint.READY &&
        controller.canRequestCandidates
    private fun automaticSpaceEligible() = featureEligible() && readiness.hint == ModelReadinessHint.READY &&
        client.available && ownerState().let { it.canRequestModelSpelling && it.modelAutoReplaceQualified &&
            it.autocorrectionMode == AutocorrectionMode.HIGH_CONFIDENCE }
    private fun withinSpaceWindow() = spaceExecutor != null &&
        scheduler.nowMillis() - spaceStartedAt in 0 until SPACE_GRACE_MILLIS
    private fun requestKind(): RequestKind? = when {
        ownerState().canRequestModelSpelling && controller.canRequestModelRanking -> RequestKind.SPELLING
        ownerState().canRequestContextual && controller.canRequestContextualRanking -> RequestKind.CONTEXTUAL
        else -> null
    }
    private fun isCurrent(kind: RequestKind, token: ScoringToken) = when (kind) {
        RequestKind.SPELLING -> controller.isCurrentModelRanking(token)
        RequestKind.CONTEXTUAL -> controller.isCurrentContextualRanking(token)
        RequestKind.REFINEMENT -> controller.isCurrentPreviousWordRefinement(token)
    }
    private fun checkOwner() = check(Thread.currentThread() === ownerThread) { "Model candidate owner thread required" }
    private enum class RequestKind { SPELLING, CONTEXTUAL, REFINEMENT }
    companion object {
        internal const val MAX_QUALITY_RESPONSES = 8
        /** Development pause, not a measured latency/energy budget; service CPU duty still applies. */
        const val PAUSE_MILLIS = 400L
        /** UX limit on a late correction, not extra inference duty or a performance claim. */
        const val SPACE_GRACE_MILLIS = 250L
    }
}
