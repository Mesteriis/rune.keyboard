package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.SpellingQualification
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import java.lang.reflect.Proxy
import java.util.ArrayDeque

/** Independent editor document; callbacks are delivered after the controller command returns. */
internal class EditorSimulator(initial: String = "outside") {
    enum class Profile { NORMAL, NO_CALLBACK_ON_NOOP_CURSOR, SELECTION_THEN_COMPOSITION,
        SHIFTED_SPAN_AFTER_PREFIX_INSERT, SPAN_DROPPED_SILENTLY }
    data class Selection(val caret: Int, val start: Int, val end: Int)
    data class Snapshot(val text: String, val selection: Selection)

    val controller = TypingSessionController(jvmGraphemes, SpellingQualification { _, _ -> true })
    var profile = Profile.NORMAL
    var document = initial
        private set
    private var caret = initial.length
    private var start = -1
    private var end = -1
    private var batchDepth = 0
    private var executeDepth = 0
    private var shifted = false
    private var requestId = 0L
    val calls = mutableListOf<String>()
    val callbacks = mutableListOf<Selection>()
    val pending = ArrayDeque<Selection>()
    var suppressedCallbacks = 0
        private set
    var autoFlush = true
    var refuseFinish = false
    var throwOnFinish = false
    var afterFinish: (() -> Unit)? = null
    private val policy = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, false)
    private val keyboard = KeyboardState(KeyboardLanguage.ENGLISH)

    init { controller.startSession(EditorContext.from(1, 0), caret, caret) }

    fun snapshot() = Snapshot(document, selection())
    private fun selection() = Selection(caret, start, end)
    private val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
        arrayOf(InputConnection::class.java)) { _, method, args ->
        calls += method.name
        when (method.name) {
            "beginBatchEdit" -> { batchDepth++; true }
            "endBatchEdit" -> { batchDepth--; check(batchDepth >= 0); true }
            "setComposingRegion" -> {
                start = args!![0] as Int; end = args[1] as Int
                check(start in 0..end && end <= document.length)
                if (profile == Profile.SHIFTED_SPAN_AFTER_PREFIX_INSERT && !shifted) {
                    shifted = true
                    document = "X " + document; caret += 2; start += 2; end += 2
                }
                true
            }
            "setComposingText", "commitText" -> {
                val value = args!![0].toString()
                check(args[1] == 1)
                val from = if (start >= 0) start else caret
                val to = if (start >= 0) end else caret
                document = document.substring(0, from) + value + document.substring(to)
                caret = from + value.length
                start = if (method.name == "setComposingText") from else -1
                end = if (start >= 0) caret else -1
                true
            }
            "finishComposingText" -> {
                if (throwOnFinish) throw IllegalStateException("Controlled finish failure")
                if (refuseFinish) false else { start = -1; end = -1; afterFinish?.invoke(); true }
            }
            else -> error("Forbidden read or unsupported editor operation: ${method.name}")
        }
    } as InputConnection

    private fun command(edit: TypingEdit): EditorCommand = when (edit) {
        is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
        is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
        TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
        is TypingEdit.SetComposingRegion -> EditorCommand.SetComposingRegion(edit.start, edit.end)
        is TypingEdit.Batch -> EditorCommand.Batch(edit.edits.map(::command), edit.isCurrent)
    }

    val execute: (TypingEdit) -> Boolean = { edit ->
        val before = selection()
        executeDepth++
        val handled = try { EditorCommandExecutor.execute(command(edit), connection, false, false).handled }
            finally { executeDepth-- }
        if (executeDepth == 0) {
            check(batchDepth == 0)
            val after = selection()
            when {
                profile == Profile.NO_CALLBACK_ON_NOOP_CURSOR && before.caret == after.caret -> suppressedCallbacks++
                profile == Profile.SELECTION_THEN_COMPOSITION && after.start >= 0 -> {
                    pending.addLast(Selection(after.caret, -1, -1)); pending.addLast(after)
                }
                before != after -> pending.addLast(after)
            }
        }
        handled
    }

    fun deliverNext() {
        val value = pending.removeFirst(); callbacks += value
        controller.updateSelection(value.caret, value.caret, value.start, value.end, execute)
    }
    fun flush() {
        var count = 0
        while (pending.isNotEmpty()) { check(++count < 100); deliverNext() }
    }
    fun type(value: String): TypingTextResult {
        val result = controller.typeText(value, policy, keyboard, false, AutocorrectionMode.HIGH_CONFIDENCE, execute)
        if (result == TypingTextResult.BYPASS) check(execute(TypingEdit.CommitText(value)))
        if (autoFlush) flush()
        return result
    }
    fun finish() { check(controller.finishComposition(execute)); if (autoFlush) flush() }
    fun undo() { controller.deletePrevious(execute); if (autoFlush) flush() }
    fun dropSpanSilently() { check(profile == Profile.SPAN_DROPPED_SILENTLY); start = -1; end = -1 }

    fun publishCommon(target: String) {
        val request = checkNotNull(controller.beginCandidateRequest(++requestId, keyboard.language))
        val lexicon = object : CandidateLexicon {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
                if (language == keyboard.language && key == target) ExactMembership.PRESENT else ExactMembership.ABSENT
            override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                control: CandidateSearchControl, visitor: CandidateVisitor) = LexiconScanStatus.COMPLETE
        }
        val generation = CandidateGenerator(lexicon).generate(request.token, keyboard.language)
        check(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision,
            request.requestId, generation)))
    }
}
