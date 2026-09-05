package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessSource
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
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
        cancel()
        val session = controller.state.sessionId
        val revision = controller.state.revision
        readiness.setActive(featureEligible())
        if (!eligible()) { client.attachSession(session, false); return }
        // A valid word does not score, but must not abort payload-free weight loading for
        // this still-eligible text session. Idle unload and session invalidation remain active.
        val kind = requestKind() ?: return
        val owner = ownerState()
        client.attachSession(session, true)
        val scheduledEpoch = epoch
        val task = object : Runnable {
            override fun run() {
                checkOwner()
                if (closed || timer !== this || epoch != scheduledEpoch) return
                timer = null
                if (!eligible() || requestKind() != kind || ownerState() != owner || controller.state.sessionId != session ||
                    controller.state.revision != revision || !client.available || requestId == Long.MAX_VALUE) return
                val nextId = ++requestId
                val input = when (kind) {
                    RequestKind.SPELLING -> controller.beginModelRanking(nextId)
                    RequestKind.CONTEXTUAL -> controller.beginContextualRanking(nextId)
                } ?: return
                pendingOwner = owner
                pendingKind = kind
                trace.section(SmartTypingTraceSection.MODEL_REQUEST) { client.score(input) }
            }
        }
        timer = task
        scheduler.postDelayed(task, PAUSE_MILLIS)
    }

    /** Text/tap action barrier. Retain the binding within the same eligible session. */
    fun cancel() {
        checkOwner()
        if (closed) return
        epoch++
        pendingOwner = null
        pendingKind = null
        spaceExecutor = null
        timer?.let(scheduler::remove); timer = null
        controller.cancelModelRanking()
        client.cancel()
    }

    /** Space never waits. Flush its existing pause once and retain only this unchanged suffix. */
    internal fun editSpace(execute: (TypingEdit) -> Boolean, action: () -> TypingTextResult): TypingTextResult {
        checkOwner()
        val owner = ownerState()
        if (closed || !automaticSpaceEligible() || requestKind() != RequestKind.SPELLING) {
            cancel()
            return action()
        }
        timer?.let { task -> scheduler.remove(task); task.run() }
        val editingEpoch = epoch
        val result = controller.retainRankingAcrossSpace(action)
        if (closed || epoch != editingEpoch || ownerState() != owner || pendingKind != RequestKind.SPELLING ||
            result != TypingTextResult.HANDLED || !controller.hasSpaceCorrection || !automaticSpaceEligible()) {
            cancel()
            return result
        }
        spaceExecutor = execute
        spaceStartedAt = scheduler.nowMillis()
        val expiry = object : Runnable {
            override fun run() {
                checkOwner()
                if (timer === this && epoch == editingEpoch) cancel()
            }
        }
        timer = expiry
        scheduler.postDelayed(expiry, SPACE_GRACE_MILLIS)
        return result
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
    override fun isCurrentRequest(token: ScoringToken): Boolean {
        checkOwner()
        val kind = pendingKind ?: return false
        return if (spaceExecutor != null) withinSpaceWindow() && controller.isCurrentSpaceCorrection(token)
            else isCurrent(kind, token)
    }
    override fun onReply(reply: ScoringReply) {
        trace.section(SmartTypingTraceSection.MODEL_RESULT) {
            checkOwner()
            val kind = pendingKind ?: return@section
            val executeSpace = spaceExecutor
            if (executeSpace != null && (!withinSpaceWindow() || !automaticSpaceEligible())) {
                cancel(); return@section
            }
            if (closed || (executeSpace == null && !eligible()) || pendingOwner != ownerState() ||
                !isCurrentRequest(reply.token)) return@section
            if (reply.code == ScoringCode.NO_MODEL || reply.code == ScoringCode.LOAD_FAILED) {
                cancel(); client.attachSession(null, false); readiness.setActive(false)
                return@section
            }
            val accepted = if (executeSpace != null) controller.acceptSpaceCorrection(reply, executeSpace) else when (kind) {
                RequestKind.SPELLING -> controller.acceptModelRanking(reply)
                RequestKind.CONTEXTUAL -> controller.acceptContextualRanking(reply)
            }
            pendingOwner = null
            pendingKind = null
            spaceExecutor = null
            timer?.let(scheduler::remove); timer = null
            if (accepted) changed()
        }
    }
    override fun onAvailabilityChanged(available: Boolean) {
        checkOwner()
        if (!available && !closed) cancel()
        // A new connection never resubmits an earlier composition.
    }
    override fun close() {
        checkOwner()
        if (closed) return
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
    }
    private fun checkOwner() = check(Thread.currentThread() === ownerThread) { "Model candidate owner thread required" }
    private enum class RequestKind { SPELLING, CONTEXTUAL }
    companion object {
        /** Development pause, not a measured latency/energy budget; service CPU duty still applies. */
        const val PAUSE_MILLIS = 400L
        /** UX limit on a late correction, not extra inference duty or a performance claim. */
        const val SPACE_GRACE_MILLIS = 250L
    }
}
