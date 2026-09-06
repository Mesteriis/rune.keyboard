package io.github.mesteriis.rune.keyboard.smarttyping.session

import java.text.BreakIterator
import java.util.Locale

/** Independent editor model. All content comes from edits, never from controller state. */
internal class HostTypingEditExecutor {
    var text = ""; private set
    var caret = 0; private set
    var composingStart = -1; private set
    var composingEnd = -1; private set
    var refuse = false
    val edits = mutableListOf<Map<String, Any?>>()

    fun execute(edit: TypingEdit): Boolean {
        if (refuse) { edits.add(mapOf("kind" to "REFUSED")); return false }
        when (edit) {
            is TypingEdit.Batch -> {
                edits.add(mapOf("kind" to "Batch", "count" to edit.edits.size))
                for (item in edit.edits) if (!edit.isCurrent() || !execute(item)) return false
            }
            is TypingEdit.SetComposingText -> replace(edit.value, true)
            is TypingEdit.CommitText -> replace(edit.value, false)
            TypingEdit.FinishComposingText -> {
                edits.add(mapOf("kind" to "FinishComposingText"))
                composingStart = -1; composingEnd = -1
            }
            is TypingEdit.SetComposingRegion -> {
                check(edit.start >= 0 && edit.end <= text.length && edit.end > edit.start) { "EDITOR_REGION" }
                edits.add(mapOf("kind" to "SetComposingRegion", "start" to edit.start, "end" to edit.end))
                composingStart = edit.start; composingEnd = edit.end
            }
        }
        return true
    }
    private fun replace(value: String, composing: Boolean) {
        val start = if (composingStart >= 0) composingStart else caret
        val end = if (composingStart >= 0) composingEnd else caret
        edits.add(mapOf("kind" to if (composing) "SetComposingText" else "CommitText",
            "value" to value, "start" to start, "end" to end))
        text = text.substring(0, start) + value + text.substring(end)
        caret = start + value.length
        composingStart = if (composing && value.isNotEmpty()) start else -1
        composingEnd = if (composing && value.isNotEmpty()) caret else -1
    }
    fun snapshot() = mapOf("text" to text, "caret" to caret,
        "composingStart" to composingStart, "composingEnd" to composingEnd)
}

internal val hostGraphemes = GraphemeSegmenter { text ->
    val iterator = BreakIterator.getCharacterInstance(Locale.ROOT).apply { setText(text) }
    buildList { var point = iterator.first(); while (point != BreakIterator.DONE) { add(point); point = iterator.next() } }
}

internal fun hostJson(value: Any?): String = when (value) {
    null -> "null"
    is String -> buildString {
        append('"'); value.forEach { c -> when (c) {
            '"' -> append("\\\""); '\\' -> append("\\\\"); '\n' -> append("\\n")
            '\r' -> append("\\r"); '\t' -> append("\\t")
            else -> if (c.code < 32) append("\\u%04x".format(c.code)) else append(c)
        } }; append('"')
    }
    is Boolean, is Int, is Long -> value.toString()
    is Double -> { check(value.isFinite()); value.toString() }
    is Float -> { check(value.isFinite()); value.toString() }
    is Map<*, *> -> value.entries.joinToString(",", "{", "}") { hostJson(it.key.toString()) + ":" + hostJson(it.value) }
    is Iterable<*> -> value.joinToString(",", "[", "]") { hostJson(it) }
    else -> error("JSON_TYPE")
}

/** Public synthetic inputs only. Assertions exercise actual production admission and selection. */
internal fun hostSyntheticTests() {
    fun test(name: String, action: () -> Unit) {
        try { action(); println(hostJson(mapOf("case" to name, "passed" to true))) }
        catch (e: Throwable) {
            println(hostJson(mapOf("case" to name, "passed" to false, "errorType" to e.javaClass.simpleName)))
            throw e
        }
    }
    test("independent-editor") {
        val e = HostTypingEditExecutor()
        check(e.execute(TypingEdit.SetComposingText("ab")) && e.text == "ab")
        check(e.execute(TypingEdit.CommitText("cat ")) && e.text == "cat " && e.composingStart == -1)
        check(e.execute(TypingEdit.SetComposingRegion(3, 4)) && e.caret == 4)
        check(e.execute(TypingEdit.SetComposingText(" dog")) && e.text == "cat dog")
        check(!e.execute(TypingEdit.Batch(listOf(TypingEdit.CommitText("bad"))) { false }) && e.text == "cat dog")
        check(e.execute(TypingEdit.FinishComposingText) && e.composingStart == -1)
        var guards = 0
        check(!e.execute(TypingEdit.Batch(listOf(TypingEdit.CommitText("!"), TypingEdit.CommitText("bad"))) { guards++ == 0 }))
        check(e.text == "cat dog!")
        e.refuse = true
        check(!e.execute(TypingEdit.CommitText("?")) && e.text == "cat dog!")
    }
    for (winner in 1..6) test("boundary-tap-$winner") {
        syntheticSession().use { s ->
            s.type("ordinary left world"); check(s.retrieve() == "CONTEXTUAL_REQUEST")
            val q = s.client.requests.single()
            check(q.prefix == "ordinary left" && q.token.candidateIds == (0..6).toList())
            check(q.continuations == listOf(" world", ", world", ": world", "; world", ". World", "? World", "! World"))
            val before = s.editor.snapshot(); val commands = s.editor.edits.size
            s.reply(winner)
            check(s.editor.snapshot() == before && s.editor.edits.size == commands)
            val item = s.punctuation()!!
            s.reply(winner); check(s.punctuation() == item && s.editor.snapshot() == before)
            check(s.local.selectCandidate(item.id, s.editor::execute) == TypingTextResult.HANDLED)
            s.ack()
            check(s.editor.text == q.prefix + q.continuations[winner] && s.controller.state.lastAutoEdit == null)
            check(s.editor.edits.drop(commands).single()["kind"] == "SetComposingText")
            val after = s.editor.snapshot(); val count = s.editor.edits.size
            check(s.local.selectCandidate(item.id, s.editor::execute) == TypingTextResult.REJECTED)
            check(s.editor.snapshot() == after && s.editor.edits.size == count)
            check(s.controller.deletePrevious(s.editor::execute) == TypingTextResult.HANDLED)
            s.ack(); check(s.editor.text == (q.prefix + q.continuations[winner]).dropLast(1))
        }
    }
    test("original-and-thresholds") {
        for ((winner, original, rival, expected) in listOf(
            listOf(0.0, -1.0, -10.0, 0.0), listOf(1.0, -1.5, -10.0, 0.0),
            listOf(1.0, -1.50001, -5.0, 1.0), listOf(1.0, -2.0, -4.99999, 0.0))) {
            syntheticSession().use { s ->
                s.type("ordinary left world"); check(s.retrieve() == "CONTEXTUAL_REQUEST")
                s.reply(winner.toInt(), original = original, rival = rival)
                check((s.punctuation() != null) == (expected == 1.0))
            }
        }
    }
    test("spelling-precedence") {
        syntheticSession().use { s ->
            s.type("ordinary left helllo"); check(s.retrieve() == "SPELLING_REQUEST")
            check(s.client.requests.single().continuations.size in 2..4)
            check(s.punctuation() == null)
        }
    }
    test("canonical-precedence") {
        for (unambiguous in listOf(false, true)) syntheticSession(canonical = unambiguous).use { s ->
            s.type("ordinary left paris"); check(s.retrieve() == "CANONICAL_CASE_PRECEDENCE")
            check(s.generation!!.alternatives.single().canonicalCaseUnambiguous == unambiguous)
            check(s.client.requests.isEmpty() && !s.controller.canRequestContextualRanking)
        }
    }
    test("protected-unknown-exhausted") {
        syntheticSession().use { s -> s.type("ordinary left HTTP"); check(s.retrieve() == "PROTECTED"); check(s.client.requests.isEmpty()) }
        syntheticSession().use { s -> s.type("ordinary left zzzzzzz"); check(s.retrieve() == "UNKNOWN_NO_ALTERNATIVES"); check(s.client.requests.isEmpty()) }
        syntheticSession(exhaust = true).use { s ->
            s.type("ordinary left zzzzzzz"); check(s.retrieve() == "INCOMPLETE_GENERATION")
            check(s.generation!!.completion.name == "STATES_EXHAUSTED" && s.client.requests.isEmpty())
        }
    }
    test("stale-token-owner-and-session") {
        for (change in listOf("token", "owner", "session", "revision", "language", "contextualOff", "caret")) syntheticSession().use { s ->
            s.type("ordinary left world"); check(s.retrieve() == "CONTEXTUAL_REQUEST")
            val token = s.client.requests.single().token
            when (change) {
                "owner" -> s.owner = s.owner.copy(candidateStripEnabled = false)
                "session" -> s.controller.startSession(s.context, s.editor.caret, s.editor.caret)
                "revision" -> s.type("s")
                "language" -> s.owner = s.owner.copy(language = io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.SPANISH)
                "contextualOff" -> s.owner = s.owner.copy(contextualPunctuationEnabled = false)
                "caret" -> check(s.controller.updateSelection(s.editor.caret - 1, s.editor.caret - 1, -1, -1, s.editor::execute))
            }
            val before = s.editor.snapshot(); val count = s.editor.edits.size
            s.reply(1, wrongToken = change == "token")
            check(s.punctuation() == null && s.editor.snapshot() == before && s.editor.edits.size == count)
            if (change == "session" || change == "revision") check(!s.model.isCurrentRequest(token))
        }
    }
    test("refused-tap-and-hidden-strip") {
        for (hidden in listOf(false, true)) syntheticSession().use { s ->
            s.type("ordinary left world"); s.retrieve(); s.reply(1)
            val item = s.punctuation()!!; val before = s.editor.snapshot()
            if (hidden) s.owner = s.owner.copy(candidateStripEnabled = false) else s.editor.refuse = true
            check(s.local.selectCandidate(item.id, s.editor::execute) == TypingTextResult.REJECTED)
            check(s.editor.snapshot() == before)
        }
    }
    test("manual-original-veto") {
        syntheticSession().use { s ->
            s.type("ordinary left world"); s.retrieve()
            check(s.controller.selectOriginal(s.controller.originalCandidateId!!))
            s.model.candidatesChanged(); s.scheduler.drain()
            check(!s.controller.canRequestContextualRanking && s.client.requests.size == 1)
        }
    }
    test("uppercase-expansion-and-grapheme") {
        syntheticSession().use { s ->
            s.type("ordinary left ßwort"); check(s.retrieve() == "CONTEXTUAL_REQUEST")
            s.reply(4); val item = s.punctuation()!!
            check(s.local.selectCandidate(item.id, s.editor::execute) == TypingTextResult.HANDLED)
            s.ack(); check(s.editor.text == "ordinary left. SSwort")
        }
        syntheticSession().use { s ->
            s.type("ordinary left cafe\u0301")
            check(s.controller.deletePrevious(s.editor::execute) == TypingTextResult.HANDLED)
            s.ack(); check(s.editor.text == "ordinary left caf")
        }
    }
    test("reply-then-space-no-automatic-contextual-edit") {
        syntheticSession().use { s ->
            s.type("ordinary left world"); s.retrieve(); s.reply(1)
            s.type(" "); check(s.editor.text == "ordinary left world ")
        }
    }
    test("numeric-tsv-and-malformed-utf8") {
        fun encoded(s: String) = java.util.Base64.getEncoder().encodeToString(s.toByteArray())
        val variants = listOf(" world", ", world", ": world", "; world", ". World", "? World", "! World")
        val response = listOf("0", encoded("public"), "EXACT_CACHE_OK", encoded("ordinary left"), "0,1,2,3,4,5,6",
            variants.joinToString(",", transform = ::encoded), "-", "-", "12.75",
            (0..6).joinToString(",") { "$it:${if (it == 1) -1.0 else -10.0}:1" })
        val observed = ContextualControllerAttribution.syntheticObservation(response)
        check(observed["harnessError"] == null && observed["offer"] == true && observed["tapResult"] == "HANDLED")
        val supplemental = response.toMutableList().apply { this[2] = "SUPPLEMENT_OK" }
        val supplementalObserved = ContextualControllerAttribution.syntheticObservation(supplemental)
        check(supplementalObserved["harnessError"] == null && supplementalObserved["responseStatus"] == "SUPPLEMENT_OK" &&
            supplementalObserved["offer"] == true && supplementalObserved["tapResult"] == "HANDLED") { "SUPPLEMENT_DELIVERY" }
        val supplementalError = response.toMutableList().apply {
            this[2] = "SUPPLEMENT_ERROR"; this[6] = "SCORING_FAILED"; this[7] = "15"; this[8] = "-"; this[9] = "-"
        }
        val errorObserved = ContextualControllerAttribution.syntheticObservation(supplementalError)
        check(errorObserved["harnessError"] == null && errorObserved["responseStatus"] == "SUPPLEMENT_ERROR" &&
            errorObserved["replyDelivered"] == true && errorObserved["offer"] == false) { "SUPPLEMENT_ERROR_DELIVERY" }
        val bad = response.toMutableList().apply { this[3] = encoded("changed prefix") }
        check(ContextualControllerAttribution.syntheticObservation(bad)["harnessError"] != null)
        for (status in listOf("UNREPRESENTABLE_REPLY", "PAYLOAD_MISMATCH", "NEW_CONTEXTUAL_REQUEST", "MISSING_RESPONSE")) {
            val held = response.toMutableList().apply { this[2] = status }
            val unknown = ContextualControllerAttribution.syntheticObservation(held)
            check(unknown["harnessError"] == null && unknown["replyDelivered"] == false && unknown["offer"] == false)
        }
        var rejected = false
        try { ContextualControllerAttribution.decode("/w==") } catch (_: java.nio.charset.CharacterCodingException) { rejected = true }
        check(rejected)
    }
    test("candidate-owner-denial") {
        syntheticSession().use { s ->
            s.type("ordinary left world")
            s.owner = s.owner.copy(autocorrectionMode = io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode.OFF,
                candidateStripEnabled = false, contextualPunctuationEnabled = false)
            check(s.retrieve() == "OWNER_INELIGIBLE") { "OWNER_DENIAL_BYPASSED" }
            check(!s.accepted && s.generation == null && s.client.requests.isEmpty())
        }
    }
    test("candidate-route-denial-and-validated-readers") {
        val en = io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.ENGLISH
        val es = io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.SPANISH
        val route = io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRouter.route("world", en)
        val missing = PrevalidatedRoutes(setOf(en), "PUBLIC_SYNTHETIC_READERS")
        missing.readyLanguages = setOf(en, es)
        check(!missing.request(route)) { "UNVALIDATED_FALLBACK_ADMITTED" }
        for (denial in listOf("missing-fallback", "request-denied", "closed")) syntheticSession().use { s ->
            s.type("ordinary left world")
            when (denial) {
                "missing-fallback" -> s.routes.readyLanguages = setOf(en)
                "request-denied" -> s.routes.requestAllowed = false
                "closed" -> s.routes.close()
            }
            val terminal = s.retrieve()
            check(terminal == if (denial == "request-denied") "ROUTE_REQUEST_DENIED" else "ROUTE_NOT_READY")
            check(s.routes.requestCalls == 1 && s.generation == null && !s.accepted && s.client.requests.isEmpty())
        }
        syntheticSession().use { s ->
            s.type("ordinary left world"); check(s.retrieve() == "CONTEXTUAL_REQUEST")
            check(s.routes.requestCalls == 1 && s.accepted && s.secondaryReasons.isEmpty())
            val admission = s.gates["candidateAdmission"] as Map<*, *>
            val requested = admission["requestedRoute"] as Map<*, *>
            check(requested["primary"] == "en" && requested["fallback"] == "es")
            check((admission["replyGuards"] as Map<*, *>).values.all { it == true })
        }
    }
    test("candidate-reply-stale-and-unready") {
        val cases = linkedMapOf("reply-session" to "REPLY_SESSION_MISMATCH", "reply-revision" to "REPLY_REVISION_MISMATCH",
            "reply-request" to "REPLY_REQUEST_MISMATCH", "reply-original" to "ORIGINAL_TOKEN_MISMATCH",
            "session" to "LIVE_SESSION_MISMATCH", "revision" to "LIVE_REVISION_MISMATCH",
            "language" to "ACTIVE_LANGUAGE_CHANGED", "owner" to "OWNER_INELIGIBLE",
            "composition" to "COMPOSITION_CHANGED", "original-selected" to "ORIGINAL_SELECTED",
            "epoch" to "ADMISSION_EPOCH_CHANGED", "unready" to "ROUTE_NOT_READY", "closed" to "SESSION_CLOSED")
        for ((change, reason) in cases) syntheticSession().use { s ->
            s.type("ordinary left world")
            val terminal = s.retrieve { _, reply ->
                when (change) {
                    "reply-session" -> reply.copy(sessionId = reply.sessionId + 1)
                    "reply-revision" -> reply.copy(revision = reply.revision + 1)
                    "reply-request" -> reply.copy(requestId = reply.requestId + 1)
                    "reply-original" -> reply.copy(generation = reply.generation.copy(original = "different"))
                    else -> {
                        when (change) {
                            "session" -> s.controller.startSession(s.context, s.editor.caret, s.editor.caret)
                            "revision" -> s.type("s")
                            "language" -> s.owner = s.owner.copy(language = io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.SPANISH)
                            "owner" -> s.owner = s.owner.copy(inputViewActive = false)
                            "composition" -> check(s.controller.updateSelection(s.editor.caret - 1, s.editor.caret - 1, -1, -1, s.editor::execute))
                            "original-selected" -> check(s.controller.selectOriginal(s.controller.originalCandidateId!!))
                            "epoch" -> s.local.invalidate()
                            "unready" -> s.routes.readyLanguages = setOf(io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.ENGLISH)
                            "closed" -> s.close()
                        }
                        reply
                    }
                }
            }
            check(terminal == "CANDIDATES_REJECTED" && !s.accepted && s.client.requests.isEmpty()) { "STALE_CANDIDATE_ADMITTED" }
            check(reason in s.secondaryReasons) { "MISSING_CANDIDATE_REASON" }
            check(s.secondaryReasons == secondaryReasonOrder.filter { it in s.secondaryReasons })
        }
    }
    test("candidate-secondary-reasons-without-labels") {
        syntheticSession().use { s ->
            s.type("ordinary 2011 world")
            check(s.retrieve() == "ENGINE_EXCLUDED" && s.accepted && s.client.requests.isEmpty())
            check(s.secondaryReasons == listOf("ENGINE_EXCLUDED") && s.gates["contextualVariantCount"] == 0)
        }
        syntheticSession().use { s ->
            s.type("world"); check(s.retrieve() == "NO_OWNED_SPACE")
            check(s.secondaryReasons == listOf("NO_OWNED_SPACE", "ENGINE_EXCLUDED"))
        }
    }
    test("numeric-error-no-suggestion") {
        syntheticSession().use { s ->
            s.type("ordinary left world"); s.retrieve()
            s.model.onReply(io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply(s.client.requests.single().token, 9, 0, emptyList()))
            check(s.punctuation() == null && s.editor.text == "ordinary left world")
        }
    }
}
