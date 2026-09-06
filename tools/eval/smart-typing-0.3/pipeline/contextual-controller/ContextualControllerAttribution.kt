package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.client.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.*
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualPunctuationEngine
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import java.io.File
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import java.security.MessageDigest
import java.util.Base64
import java.util.concurrent.Executor

/** Deterministic final-target transport seam; no inference, Android service, or timing claim. */
internal class HostScheduler : ModelPauseScheduler {
    private val tasks = linkedMapOf<Runnable, Long>()
    private var clock = 0L
    override fun postDelayed(task: Runnable, millis: Long) { check(millis >= 0); tasks[task] = clock + millis }
    override fun remove(task: Runnable) { tasks.remove(task) }
    override fun nowMillis() = clock
    fun drain() {
        check(tasks.size <= 1) { "MULTIPLE_MODEL_TIMERS" }
        val entry = tasks.entries.singleOrNull() ?: return
        clock = entry.value; tasks.remove(entry.key); entry.key.run()
    }
}
internal class HostReady : ModelReadinessSource {
    override var hint = ModelReadinessHint.READY; private set
    override fun setActive(active: Boolean) { hint = if (active) ModelReadinessHint.READY else ModelReadinessHint.UNKNOWN }
    override fun close() { hint = ModelReadinessHint.UNKNOWN }
}
internal class HostClient : ModelScoringClient {
    override var available = false; private set
    val requests = mutableListOf<ScoringInput>()
    override fun attachSession(sessionId: Long?, effectiveAvailability: Boolean) {
        available = sessionId != null && effectiveAvailability
    }
    override fun score(input: ScoringInput) { check(available); requests.add(input) }
    override fun cancel() = Unit
    override fun close() { available = false }
}

/** Ready-route seam over validated public readers; it never loads or invents missing assets. */
internal class PrevalidatedRoutes(languages: Set<KeyboardLanguage>, val proof: String) {
    val validatedLanguages = languages.toSet()
    var readyLanguages = validatedLanguages
    var requestAllowed = true
    var closed = false; private set
    var epoch = 0L; private set
    var requestCalls = 0; private set
    private fun required(route: LanguageRoute): Set<KeyboardLanguage> =
        if (route.primary == null || route.protectedReason != null) emptySet()
        else listOfNotNull(route.primary, route.fallback).toSet()
    fun isReady(route: LanguageRoute): Boolean {
        val required = required(route)
        return !closed && required.isNotEmpty() && required.all { it in validatedLanguages && it in readyLanguages }
    }
    fun request(route: LanguageRoute): Boolean { requestCalls++; return requestAllowed && isReady(route) }
    fun invalidate() { epoch++ }
    fun close() { closed = true; invalidate() }
}

internal val secondaryReasonOrder = listOf("SESSION_CLOSED", "OWNER_INELIGIBLE", "OWNERSHIP_UNAVAILABLE",
    "ORIGINAL_SELECTED", "PROTECTED", "ROUTE_PROTECTED", "ROUTE_REQUEST_DENIED", "ROUTE_NOT_READY",
    "CANDIDATE_REQUEST_UNAVAILABLE", "REQUEST_INELIGIBLE", "REPLY_SESSION_MISMATCH", "REPLY_REVISION_MISMATCH",
    "REPLY_REQUEST_MISMATCH", "LIVE_SESSION_MISMATCH", "LIVE_REVISION_MISMATCH", "ACTIVE_LANGUAGE_CHANGED",
    "ORIGINAL_TOKEN_MISMATCH", "COMPOSITION_CHANGED", "ADMISSION_EPOCH_CHANGED", "CANDIDATES_REJECTED",
    "CANONICAL_CASE_PRECEDENCE", "INCOMPLETE_GENERATION", "UNKNOWN_NO_ALTERNATIVES", "NO_OWNED_SPACE",
    "ENGINE_EXCLUDED", "MODEL_REQUEST_NOT_ADMITTED")

private fun routeRecord(route: LanguageRoute?) = route?.let {
    mapOf("primary" to it.primary?.locale?.language, "fallback" to it.fallback?.locale?.language,
        "primaryPrior" to it.primaryPrior, "fallbackPrior" to it.fallbackPrior,
        "fallbackCandidateLimit" to it.fallbackCandidateLimit, "protectedReason" to it.protectedReason?.name)
}

internal class AttributionSession(
    language: KeyboardLanguage,
    private val lexicon: CandidateLexicon,
    private val cases: CanonicalCaseLexicon,
    val routes: PrevalidatedRoutes,
) : AutoCloseable {
    val settings = KeyboardSettings.DEFAULT
    val context = EditorContext.from(1, 0)
    val keyboard = KeyboardState(language = language)
    val controller = TypingSessionController(graphemes = hostGraphemes)
    val editor = HostTypingEditExecutor()
    val scheduler = HostScheduler()
    val client = HostClient()
    private val readiness = HostReady()
    val policy = MechanicalPunctuationPolicy(context.inputPolicy, context.mode, context.requiresRawKeyEvents,
        settings.mechanicalPunctuation, settings.doubleSpacePeriod)
    var owner = CandidateOwnerState(
        editorAllowsSmartTyping = context.supportsSmartTyping, inputViewActive = true,
        layer = keyboard.layer, language = language, hasSelection = false,
        autocorrectionMode = settings.autocorrectionMode, candidateStripEnabled = settings.candidateStrip,
        deterministicAutoReplaceQualified = controller.isSpellingQualified(language, false),
        modelAutoReplaceQualified = controller.isSpellingQualified(language, true),
        modelRuntimeQualified = ModelRuntimeQualification.CURRENT,
        contextualPunctuationEnabled = settings.contextualPunctuationMode == ContextualPunctuationMode.SUGGESTIONS,
        contextualModelReady = true)
    private fun currentOwner() = owner.copy(contextualModelReady = readiness.hint == ModelReadinessHint.READY)
    val model = ModelCandidateCoordinator(controller, { client }, scheduler, ::currentOwner, readiness, {})
    val local = LocalCandidateCoordinator(controller, lexicon, routes::request, routes::isReady, routes::invalidate, routes::close, Executor { it.run() },
        ::currentOwner, {}, modelRanking = model, canonicalCaseLexicon = cases)
    private val generator = CandidateGenerator(lexicon, CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES, cases)
    val inputSteps = mutableListOf<Map<String, Any?>>()
    var generation: CandidateGeneration? = null; private set
    var accepted = false; private set
    var gates: Map<String, Any?> = emptyMap(); private set
    var secondaryReasons: List<String> = emptyList(); private set
    private var candidateRequestId = 0L
    private var closed = false
    init {
        check(settings.autocorrectionMode == AutocorrectionMode.HIGH_CONFIDENCE && settings.candidateStrip &&
            settings.mechanicalPunctuation && settings.contextualPunctuationMode == ContextualPunctuationMode.SUGGESTIONS) { "DEFAULT_SETTINGS_DRIFT" }
        controller.startSession(context, 0, 0)
    }
    fun ack() {
        check(!controller.updateSelection(editor.caret, editor.caret, editor.composingStart, editor.composingEnd, editor::execute)) { "OWNERSHIP_LOSS" }
        check(editor.text.endsWith(controller.state.contextText)) { "EDITOR_CONTEXT_DIVERGENCE" }
        controller.state.composing?.let { check(editor.composingStart >= 0 && editor.text.substring(editor.composingStart, editor.composingEnd) == it.text) { "COMPOSING_DIVERGENCE" } }
    }
    fun type(text: String) {
        text.codePoints().forEachOrdered { point ->
            val value = String(Character.toChars(point)); val start = editor.edits.size
            val result = controller.typeText(value, policy, keyboard, false, settings.autocorrectionMode, editor::execute)
            inputSteps.add(mapOf("value" to value, "result" to result.name, "edits" to editor.edits.drop(start), "editor" to editor.snapshot(),
                "lastAutoEdit" to controller.state.lastAutoEdit?.let { mapOf("original" to it.original, "applied" to it.applied) }))
            check(result == TypingTextResult.HANDLED) { "INPUT_NOT_HANDLED" }; ack()
        }
    }
    fun fullGeneration(word: String) = generationRecord(generator.generate(word, keyboard.language))
    /** Synchronous final-target bridge; mirrors LocalCandidateCoordinator's live guards. */
    fun retrieve(beforeReply: (LocalCandidateRequest, LocalCandidateReply) -> LocalCandidateReply = { _, reply -> reply }): String {
        val reasons = linkedSetOf<String>()
        val admission = linkedMapOf<String, Any?>("routeProof" to routes.proof,
            "validatedLanguages" to routes.validatedLanguages.map { it.locale.language }.sorted())
        fun reject(code: String): String { reasons.add(code); return code }
        val localOutcome = run {
            val initialOwner = currentOwner()
            val initial = controller.state
            admission["ownerCanRequestCandidateWork"] = initialOwner.canRequestCandidateWork
            admission["canRequestCandidatesAtRequest"] = controller.canRequestCandidates
            if (closed) return@run reject("SESSION_CLOSED")
            if (!initialOwner.canRequestCandidateWork) return@run reject("OWNER_INELIGIBLE")
            if (!controller.canRequestCandidates) return@run reject(when {
                initial.originalSelected -> "ORIGINAL_SELECTED"
                initial.composing?.typedWord?.let(ProtectedTokenPolicy::isProtected) == true -> "PROTECTED"
                else -> "OWNERSHIP_UNAVAILABLE"
            })
            model.prepareForEdit()
            val route = LanguageRouter.route(initial.composing!!.typedWord, initialOwner.language)
            admission["requestedRoute"] = routeRecord(route)
            val requested = routes.request(route)
            admission["routeRequestAccepted"] = requested
            admission["routeReadyAtRequest"] = routes.isReady(route)
            if (!requested) return@run reject(when {
                route.primary == null || route.protectedReason != null -> "ROUTE_PROTECTED"
                !routes.isReady(route) -> "ROUTE_NOT_READY"
                else -> "ROUTE_REQUEST_DENIED"
            })
            if (candidateRequestId == Long.MAX_VALUE) return@run reject("CANDIDATE_REQUEST_UNAVAILABLE")
            val request = controller.beginCandidateRequest(++candidateRequestId, initialOwner.language)
                ?: return@run reject("CANDIDATE_REQUEST_UNAVAILABLE")
            val composing = controller.state.composing
            val epoch = routes.epoch
            admission["request"] = mapOf("sessionId" to request.sessionId, "revision" to request.revision,
                "requestId" to request.requestId, "language" to request.activeLanguage.locale.language,
                "original" to request.token, "composingText" to composing?.text, "epoch" to epoch, "eligible" to request.eligible)
            if (!request.eligible) return@run reject("REQUEST_INELIGIBLE")
            generation = generator.generate(request.token, request.activeLanguage)
            val reply = beforeReply(request, LocalCandidateReply(request.sessionId, request.revision, request.requestId, generation!!))
            val liveOwner = currentOwner(); val live = controller.state; val original = live.composing?.typedWord
            val liveRoute = original?.let { LanguageRouter.route(it, liveOwner.language) }
            admission["reply"] = mapOf("sessionId" to reply.sessionId, "revision" to reply.revision,
                "requestId" to reply.requestId, "original" to reply.generation.original)
            admission["liveRoute"] = routeRecord(liveRoute)
            val replyGuards = linkedMapOf(
                "SESSION_CLOSED" to !closed, "OWNER_INELIGIBLE" to liveOwner.canRequestCandidateWork,
                "OWNERSHIP_UNAVAILABLE" to controller.canRequestCandidates,
                "REPLY_SESSION_MISMATCH" to (reply.sessionId == request.sessionId),
                "REPLY_REVISION_MISMATCH" to (reply.revision == request.revision),
                "REPLY_REQUEST_MISMATCH" to (reply.requestId == request.requestId),
                "LIVE_SESSION_MISMATCH" to (live.sessionId == request.sessionId),
                "LIVE_REVISION_MISMATCH" to (live.revision == request.revision),
                "ACTIVE_LANGUAGE_CHANGED" to (liveOwner.language == request.activeLanguage),
                "ORIGINAL_TOKEN_MISMATCH" to (original != null && original == request.token && reply.generation.original == original),
                "COMPOSITION_CHANGED" to (live.composing == composing && controller.ownsCandidateComposition),
                "ADMISSION_EPOCH_CHANGED" to (routes.epoch == epoch),
                "ROUTE_NOT_READY" to (liveRoute != null && routes.isReady(liveRoute)))
            admission["replyGuards"] = replyGuards
            replyGuards.filterValues { !it }.keys.forEach(reasons::add)
            if (replyGuards.any { !it.value }) return@run "CANDIDATES_REJECTED"
            accepted = controller.acceptCandidates(reply)
            if (!accepted) return@run reject("CANDIDATES_REJECTED")
            "ACCEPTED"
        }
        val liveOwner = currentOwner(); val composing = controller.state.composing; val text = controller.state.contextText
        val actualVariants = composing?.takeIf { text.endsWith(it.text) }?.let {
            ContextualPunctuationEngine.variants(text.dropLast(it.text.length), it.typedWord, liveOwner.language)
        }
        if (closed) reasons.add("SESSION_CLOSED")
        if (!liveOwner.canRequestCandidateWork) reasons.add("OWNER_INELIGIBLE")
        if (!controller.ownsCandidateComposition) reasons.add("OWNERSHIP_UNAVAILABLE")
        if (controller.state.originalSelected) reasons.add("ORIGINAL_SELECTED")
        if (composing?.typedWord?.let(ProtectedTokenPolicy::isProtected) == true) reasons.add("PROTECTED")
        if (generation?.alternatives?.any { it.kind == GeneratedCandidateKind.CANONICAL_CASE } == true) reasons.add("CANONICAL_CASE_PRECEDENCE")
        if (generation != null && generation!!.completion !in setOf(CandidateCompletion.COMPLETE, CandidateCompletion.VALID_WORD)) reasons.add("INCOMPLETE_GENERATION")
        if (generation?.let { !it.isValidWord && it.alternatives.isEmpty() } == true) reasons.add("UNKNOWN_NO_ALTERNATIVES")
        if (composing?.leadingBoundary != " ") reasons.add("NO_OWNED_SPACE")
        if (actualVariants != null && actualVariants.isEmpty()) reasons.add("ENGINE_EXCLUDED")
        gates = mapOf("ownsComposition" to controller.ownsCandidateComposition,
            "canRequestCandidates" to controller.canRequestCandidates, "canRequestSpelling" to liveOwner.canRequestModelSpelling,
            "canRequestModelRanking" to controller.canRequestModelRanking, "canRequestContextualOwner" to liveOwner.canRequestContextual,
            "canRequestContextualRanking" to controller.canRequestContextualRanking, "canRequestCandidateWork" to liveOwner.canRequestCandidateWork,
            "deterministicQualified" to liveOwner.deterministicAutoReplaceQualified, "modelQualified" to liveOwner.modelAutoReplaceQualified,
            "runtimeQualified" to liveOwner.modelRuntimeQualified, "candidateStrip" to liveOwner.candidateStripEnabled,
            "autocorrectionMode" to liveOwner.autocorrectionMode.name, "contextualMode" to settings.contextualPunctuationMode.name,
            "mechanicalEnabled" to settings.mechanicalPunctuation, "doubleSpaceEnabled" to settings.doubleSpacePeriod,
            "readiness" to readiness.hint.name, "originalSelected" to controller.state.originalSelected,
            "contextualVariantCount" to actualVariants?.size, "candidateAdmission" to admission)
        val spelling = controller.canRequestModelRanking && liveOwner.canRequestModelSpelling
        val contextual = controller.canRequestContextualRanking && liveOwner.canRequestContextual
        if (accepted) model.candidatesChanged()
        scheduler.drain(); check(client.requests.size <= 1) { "MULTIPLE_MODEL_REQUESTS" }
        val terminal = when {
            localOutcome != "ACCEPTED" -> localOutcome
            client.requests.isNotEmpty() && spelling -> "SPELLING_REQUEST"
            client.requests.isNotEmpty() && contextual -> "CONTEXTUAL_REQUEST"
            client.requests.isNotEmpty() -> error("UNEXPECTED_MODEL_ROUTE")
            "CANONICAL_CASE_PRECEDENCE" in reasons -> "CANONICAL_CASE_PRECEDENCE"
            "INCOMPLETE_GENERATION" in reasons -> "INCOMPLETE_GENERATION"
            "UNKNOWN_NO_ALTERNATIVES" in reasons -> "UNKNOWN_NO_ALTERNATIVES"
            "NO_OWNED_SPACE" in reasons -> "NO_OWNED_SPACE"
            "ENGINE_EXCLUDED" in reasons -> "ENGINE_EXCLUDED"
            else -> reject("MODEL_REQUEST_NOT_ADMITTED")
        }
        secondaryReasons = secondaryReasonOrder.filter { it in reasons }
        return terminal
    }
    fun punctuation() = local.viewState.candidates.filterIsInstance<CandidateUiItem.Punctuation>().singleOrNull()
    fun snapshot() = mapOf("editor" to editor.snapshot(), "sessionId" to controller.state.sessionId, "revision" to controller.state.revision,
        "contextText" to controller.state.contextText, "typedWord" to controller.state.composing?.typedWord,
        "leadingBoundary" to controller.state.composing?.leadingBoundary, "composingText" to controller.state.composing?.text,
        "ownsComposition" to controller.ownsCandidateComposition, "originalSelected" to controller.state.originalSelected,
        "view" to local.viewState.candidates.map { mapOf("id" to it.id, "text" to it.text, "kind" to it.javaClass.simpleName) },
        "lastAutoEdit" to controller.state.lastAutoEdit?.let { mapOf("original" to it.original, "applied" to it.applied) })
    fun reply(winner: Int, original: Double = -10.0, rival: Double = -10.0, wrongToken: Boolean = false) {
        val q = client.requests.single(); val token = if (wrongToken) ScoringToken(q.token.sessionId, q.token.revision, q.token.requestId + 1, q.token.candidateIds) else q.token
        val scores = q.token.candidateIds.map { id -> NumericScore(id, if (id == winner) -1.0 else if (id == 0) original else rival, 1) }
        model.onReply(ScoringReply(token, ScoringCode.OK, 12, scores))
    }
    override fun close() { if (!closed) { closed = true; local.close() } }
}

internal fun generationRecord(g: CandidateGeneration) = mapOf(
    "original" to g.original, "completion" to g.completion.name, "isValidWord" to g.isValidWord,
    "protectedReason" to g.protectedReason?.name, "prohibitsAutoReplace" to g.prohibitsAutoReplace,
    "inspectedStates" to g.inspectedStates, "verifiedTerminals" to g.verifiedTerminals,
    "alternatives" to g.alternatives.map { c -> mapOf("text" to c.text, "canonicalKey" to c.canonicalKey, "terminalKey" to c.terminalKey,
        "language" to c.language.locale.language, "isFallback" to c.isFallback, "languagePrior" to c.languagePrior,
        "frequencyRank" to c.frequencyRank, "unitDistance" to c.unitDistance, "editCost" to c.editFeatures.editCost,
        "repeatedCharacterEdits" to c.editFeatures.repeatedCharacterEdits, "repetitionBonus" to c.editFeatures.repetitionBonus,
        "lengthDifference" to c.lengthDifference, "casePattern" to c.casePattern.name, "kind" to c.kind.name,
        "canonicalCaseUnambiguous" to c.canonicalCaseUnambiguous, "canonicalCaseAutoEligible" to c.canonicalCaseAutoEligible) })

private fun syntheticLexicons(canonical: Boolean? = null, exhaust: Boolean = false): Pair<CandidateLexicon, CanonicalCaseLexicon> {
    val words = setOf("world", "hello", "paris", "ßwort", "café")
    val distance = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
    val lexicon = object : CandidateLexicon {
        override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
            check(control.inspectState())
            return if (language == KeyboardLanguage.ENGLISH && key in words) ExactMembership.PRESENT else ExactMembership.ABSENT
        }
        override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int, control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus {
            if (exhaust) { while (control.inspectState()) Unit; return LexiconScanStatus.UNAVAILABLE }
            if (language == KeyboardLanguage.ENGLISH) words.sorted().forEach { word ->
                if (!control.inspectState()) return LexiconScanStatus.UNAVAILABLE
                if (word != key && distance.features(key, word, language).editCost <= unitRadius && !visitor.visit(word, 1)) return LexiconScanStatus.UNAVAILABLE
            }
            return LexiconScanStatus.COMPLETE
        }
    }
    val cases = CanonicalCaseLexicon { language, key ->
        if (canonical != null && language == KeyboardLanguage.ENGLISH && key == "paris") CanonicalCase("Paris", canonical) else null
    }
    return lexicon to cases
}

internal fun syntheticSession(canonical: Boolean? = null, exhaust: Boolean = false): AttributionSession {
    val (lexicon, cases) = syntheticLexicons(canonical, exhaust)
    return AttributionSession(KeyboardLanguage.ENGLISH, lexicon, cases,
        PrevalidatedRoutes(KeyboardLanguage.entries.toSet(), "PUBLIC_SYNTHETIC_READERS"))
}

/** No source label, expected boundary, calibration split or semantic answer enters the JVM. */
object ContextualControllerAttribution {
    internal fun decode(value: String) = Charsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
        .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(Base64.getDecoder().decode(value))).toString()
    private data class Assets(val lexicon: CandidateLexicon, val cases: CanonicalCaseLexicon, val validatedLanguages: Set<KeyboardLanguage>)
    private fun assets(directory: File): Assets {
        fun mapped(file: File) = FileChannel.open(file.toPath(), StandardOpenOption.READ).use { it.map(FileChannel.MapMode.READ_ONLY, 0, it.size()) }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH).map { trust ->
            val language = trust.language.locale.language
            val loaded = PackedLexiconData.validate(trust, mapped(File(directory, "smarttyping/lexicon/$language.trie")),
                mapped(File(directory, "smarttyping/lexicon/$language.trie.lengths")), mapped(File(directory, "smarttyping/lexicon/frequency/$language.ranks")))
            check(loaded is PackedLexiconLoad.Ready) { "PACKED_ASSET_NOT_READY" }; trust.language to loaded.lexicon
        }
        val cases = KeyboardLanguage.entries.associateWith { language ->
            val trust = FrozenCanonicalCaseLexicons.forLanguage(language); val bytes = File(directory, trust.path).readBytes()
            val sha = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            check(bytes.size.toLong() == trust.bytes && sha == trust.sha256) { "CASE_HASH" }; CanonicalCaseData.validate(bytes)
        }
        System.err.println("ALL_12_PACKAGED_ASSETS_VALIDATED")
        return Assets(PackedCandidateLexicon(handles.map { it.second }), CanonicalCaseLexicon { language, key -> cases.getValue(language).lookup(key) },
            handles.map { it.first }.toSet().intersect(cases.keys))
    }
    private fun requestRecord(q: ScoringInput) = mapOf("prefix" to q.prefix, "candidateIds" to q.token.candidateIds, "continuations" to q.continuations,
        "sessionId" to q.token.sessionId, "revision" to q.token.revision, "requestId" to q.token.requestId)
    private fun row(fields: List<String>, lexicon: CandidateLexicon, cases: CanonicalCaseLexicon, response: List<String>?, routes: PrevalidatedRoutes): Map<String, Any?> {
        check(fields.size == 5) { "INPUT_COLUMNS" }
        val index = fields[0].toInt(); val id = decode(fields[1]); val language = KeyboardLanguage.entries.single { it.locale.language == fields[2] }
        val prefix = decode(fields[3]); val word = decode(fields[4]); val expected = "$prefix $word"
        val result = linkedMapOf<String, Any?>("schemaVersion" to 1, "scope" to "contextual-controller-attribution", "index" to index, "id" to id,
            "language" to fields[2], "inputExpected" to expected, "inputChanged" to false, "inputSteps" to emptyList<Any>(),
            "beforeCandidates" to null, "fullGeneration" to null, "requestGeneration" to null, "candidatesAccepted" to false,
            "routing" to "HARNESS_ERROR", "secondaryReasons" to emptyList<String>(), "gateFacts" to emptyMap<String, Any>(), "modelRequest" to null, "requestCount" to 0,
            "harnessError" to null, "responseStatus" to (response?.getOrNull(2) ?: "NOT_CONSUMED"), "replyDelivered" to false, "replyCurrent" to null,
            "afterReply" to null, "offer" to false, "decisionId" to null, "responseEdited" to false, "tapAttempted" to false, "tapResult" to null,
            "afterTap" to null, "tapEdits" to emptyList<Any>(), "allowedTapChange" to true, "duplicateResult" to null, "duplicateEdits" to 0)
        AttributionSession(language, lexicon, cases, routes).use { s ->
            var stage = "INPUT"
            try {
                s.type(expected)
                result["inputChanged"] = s.editor.text != expected
                result["beforeCandidates"] = s.snapshot()
                stage = "CANDIDATE_ADMISSION"
                result["fullGeneration"] = s.fullGeneration(word)
                val routing = s.retrieve(); result["routing"] = routing
                result["requestGeneration"] = s.generation?.let(::generationRecord); result["candidatesAccepted"] = s.accepted
                result["gateFacts"] = s.gates; result["secondaryReasons"] = s.secondaryReasons
                val q = s.client.requests.singleOrNull(); result["modelRequest"] = q?.let(::requestRecord)
                if (response != null) {
                    stage = "RESPONSE_ADMISSION"
                    check(response.size == 10 && response[0].toInt() == index && decode(response[1]) == id) { "RESPONSE_ROW" }
                    val status = response[2]
                    check(status in setOf("NO_CONTEXTUAL_REQUEST", "EXACT_CACHE_OK", "EXACT_CACHE_ERROR", "SUPPLEMENT_OK", "SUPPLEMENT_ERROR", "UNREPRESENTABLE_REPLY", "PAYLOAD_MISMATCH", "NEW_CONTEXTUAL_REQUEST", "MISSING_RESPONSE")) { "RESPONSE_STATUS" }
                    if (routing == "CONTEXTUAL_REQUEST") {
                        check(q != null && decode(response[3]) == q.prefix && response[4].split(',').map(String::toInt) == q.token.candidateIds &&
                            response[5].split(',').map(::decode) == q.continuations) { "RESPONSE_PAYLOAD" }
                    } else check(status == "NO_CONTEXTUAL_REQUEST") { "NO_QUERY_RESPONSE" }
                    val before = s.editor.snapshot(); val count = s.editor.edits.size
                    val numericOk = status == "EXACT_CACHE_OK" || status == "SUPPLEMENT_OK"
                    val numericError = status == "EXACT_CACHE_ERROR" || status == "SUPPLEMENT_ERROR"
                    if (numericOk || numericError && response[7] != "-") {
                        check(routing == "CONTEXTUAL_REQUEST" && q != null) { "DELIVERY_ROUTE" }
                        stage = "REPLY"
                        val code = if (numericOk) ScoringCode.OK else response[7].toInt()
                        val scores = if (code == ScoringCode.OK) response[9].split(',').map { encoded ->
                            val numeric = encoded.split(':'); check(numeric.size == 3)
                            NumericScore(numeric[0].toInt(), numeric[1].toDouble(), numeric[2].toInt())
                        } else emptyList()
                        val elapsed = if (response[8] == "-") 0L else java.math.BigDecimal(response[8]).toLong()
                        result["replyCurrent"] = s.model.isCurrentRequest(q.token)
                        check(result["replyCurrent"] == true) { "REPLY_NOT_CURRENT" }
                        s.model.onReply(ScoringReply(q.token, code, elapsed, scores)); result["replyDelivered"] = true
                    }
                    result["afterReply"] = s.snapshot()
                    result["responseEdited"] = before != s.editor.snapshot() || count != s.editor.edits.size
                    val item = s.punctuation(); result["offer"] = item != null
                    if (item != null) {
                        stage = "TAP"
                        check(q != null)
                        // UI contains the boundary glyph, not the full continuation. Reconstruct the
                        // actual engine variants and require the captured allowlist before matching it.
                        val variants = ContextualPunctuationEngine.variants(q.prefix, s.controller.state.composing!!.typedWord, language)
                        check(variants.map { it.id } == q.token.candidateIds && variants.map { it.continuation } == q.continuations) { "VISIBLE_ALLOWLIST" }
                        val selected = variants.withIndex().filter { it.value.boundary.trimEnd() == item.text }.single().index
                        check(selected in 1..6) { "PUNCTUATION_DECISION" }; result["decisionId"] = q.token.candidateIds[selected]
                        val start = s.editor.composingStart; val end = s.editor.composingEnd
                        check(start >= 0 && end == s.editor.text.length) { "TAP_OWNERSHIP" }
                        val expectedAfter = s.editor.text.substring(0, start) + q.continuations[selected]
                        val editsBefore = s.editor.edits.size
                        result["tapAttempted"] = true
                        val tapped = s.local.selectCandidate(item.id, s.editor::execute)
                        result["tapResult"] = tapped.name
                        if (tapped == TypingTextResult.HANDLED) s.ack()
                        val edits = s.editor.edits.drop(editsBefore); result["tapEdits"] = edits
                        result["allowedTapChange"] = if (tapped == TypingTextResult.HANDLED)
                            s.editor.text == expectedAfter && s.editor.caret == expectedAfter.length &&
                            s.editor.composingStart == start && s.editor.composingEnd == expectedAfter.length &&
                            edits.size == 1 && edits.single()["kind"] == "SetComposingText" && s.controller.state.lastAutoEdit == null
                            else before == s.editor.snapshot() && edits.isEmpty()
                        result["afterTap"] = s.snapshot()
                        val duplicateBefore = s.editor.snapshot(); val duplicateCount = s.editor.edits.size
                        stage = "DUPLICATE_TAP"
                        result["duplicateResult"] = s.local.selectCandidate(item.id, s.editor::execute).name
                        result["duplicateEdits"] = s.editor.edits.size - duplicateCount
                        if (duplicateBefore != s.editor.snapshot()) result["allowedTapChange"] = false
                    } else result["afterTap"] = s.snapshot()
                }
            } catch (e: Exception) {
                result["harnessError"] = mapOf("type" to e.javaClass.simpleName, "stage" to stage,
                    "code" to e.message?.takeIf { it.matches(Regex("[A-Z_]+")) })
            } finally {
                result["inputChanged"] = s.editor.text != expected && result["beforeCandidates"] == null || result["inputChanged"] == true
                result["inputSteps"] = s.inputSteps.toList(); result["requestCount"] = s.client.requests.size
            }
        }
        return result
    }
    internal fun syntheticObservation(response: List<String>?): Map<String, Any?> {
        fun encoded(s: String) = Base64.getEncoder().encodeToString(s.toByteArray())
        val (lexicon, cases) = syntheticLexicons()
        return row(listOf("0", encoded("public"), "en", encoded("ordinary left"), encoded("world")), lexicon, cases, response, PrevalidatedRoutes(KeyboardLanguage.entries.toSet(), "PUBLIC_SYNTHETIC_READERS"))
    }
    @JvmStatic fun main(args: Array<String>) {
        if (args.contentEquals(arrayOf("test"))) { hostSyntheticTests(); return }
        check(args.size in 3..4 && args[0] in setOf("prepare", "replay")) { "COMMAND" }
        check((args[0] == "prepare") == (args.size == 3)) { "COMMAND_ARGUMENTS" }
        val assets = assets(File(args[2])); val inputs = File(args[1]).readLines()
        val responses = if (args.size == 4) File(args[3]).readLines() else null
        check(responses == null || responses.size == inputs.size) { "RESPONSE_COUNT" }
        inputs.forEachIndexed { i, line ->
            val fields = line.split('\t'); check(fields[0].toInt() == i) { "INPUT_ORDER" }
            println(hostJson(row(fields, assets.lexicon, assets.cases, responses?.get(i)?.split('\t'),
                PrevalidatedRoutes(assets.validatedLanguages, "PACKAGED_TRIE_LENGTH_RANK_CASE_VALIDATED"))))
        }
    }
}
