package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.view.inputmethod.InputConnection
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.settings.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.*
import java.lang.reflect.Proxy
import org.junit.Assert.*
import org.junit.Test

/** Real controller + executor, with an independent editor document/selection model. No editor reads. */
class MechanicalTypingSessionTest {
    private val editor = EditorContext.from(1, 0)
    private val enabled = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, false)

    @Test fun `punctuation retains only boundary after committing old word`() {
        for (mark in listOf(",", ".", "?", "!", ":", ";")) {
            val f = Fixture(); f.type("hello"); f.calls.clear(); f.type(mark)
            assertEquals(listOf("finish", "set"), f.calls)
            assertEquals(ComposingSegment(mark), f.controller.state.composing)
            assertEquals(mark, f.sent.last())
            assertEquals("hello$mark", f.document)
        }
    }

    @Test fun `space before comma and missing after use one replacement each`() {
        val f = Fixture(); f.type("hello"); f.type(" "); f.calls.clear()
        f.type(","); assertEquals(listOf("set"), f.calls); assertEquals(",", f.sent.last())
        assertEquals("hello,", f.document)
        f.calls.clear(); f.type("world")
        assertEquals(listOf("set"), f.calls); assertEquals(", world", f.sent.last())
        f.undo(); assertEquals("hello,world", f.document)
        f.undo(); assertEquals("hello,worl", f.document)
        assertEquals(0, f.reads)
    }

    @Test fun `compound spaces caps and raw incoming text are one immediate undo`() {
        val f = Fixture(); f.raw("hello"); f.raw(" "); f.raw(" "); f.raw("!"); f.raw(" "); f.raw(" ")
        f.calls.clear(); f.type("world")
        assertEquals(listOf("set"), f.calls); assertEquals("! World", f.sent.last())
        assertEquals("hello! World", f.document)
        f.calls.clear(); f.undo()
        assertEquals(listOf("set"), f.calls); assertEquals("hello  !  world", f.document)
        assertNull(f.controller.state.lastAutoEdit)
        f.undo(); assertEquals("hello  !  worl", f.document)
    }

    @Test fun `explicit sentence space recases only first new letter and records undo only if changed`() {
        for (mark in listOf(".", "?", "!")) {
            val f = Fixture(); f.raw("hello"); f.raw(mark); f.raw(" "); f.type("world")
            assertEquals("hello$mark World", f.document)
            f.undo(); assertEquals("hello$mark world", f.document)
            val unchanged = Fixture(); unchanged.raw("hello"); unchanged.raw(mark); unchanged.raw(" ")
            unchanged.type("World"); assertNull(unchanged.controller.state.lastAutoEdit)
        }
    }

    @Test fun `locale expansion preserves remainder and respects rendered composing bound`() {
        val f = Fixture(); f.raw("hello"); f.raw("!"); f.type("ßeta")
        assertEquals("hello! SSeta", f.document)
        f.undo(); assertEquals("hello!ßeta", f.document)
        val ru = Fixture(); ru.keyboard = KeyboardState(KeyboardLanguage.RUSSIAN)
        ru.raw("готово"); ru.raw("?"); ru.type("ёлка"); assertEquals("готово? Ёлка", ru.document)
        val es = Fixture(); es.keyboard = KeyboardState(KeyboardLanguage.SPANISH)
        es.raw("listo"); es.raw("!"); es.type("ñandú"); assertEquals("listo! Ñandú", es.document)
        val bounded = Fixture(); bounded.raw("hello"); bounded.raw("!")
        repeat(125) { bounded.raw(" ") }
        bounded.type("ß") // proposed 2 + 2 fits; excessive raw span is rejected by planner first.
        assertEquals("hello! SS", bounded.document)
    }

    @Test fun `delayed pair of dots remains visible until ordinary next word after explicit spaces`() {
        val f = Fixture(); f.type("hello"); f.type("."); f.type(".")
        assertEquals("hello..", f.document); assertNull(f.controller.state.lastAutoEdit)
        f.type(" "); f.type(" "); assertEquals("hello..  ", f.document)
        f.calls.clear(); f.type("world")
        assertEquals(listOf("set"), f.calls); assertEquals(". World", f.sent.last())
        assertEquals("hello. World", f.document)
        f.undo(); assertEquals("hello..  world", f.document)
        f.undo(); assertEquals("hello..  worl", f.document)
    }

    @Test fun `third dot pause no whitespace numeric and technical continuations remain raw`() {
        for ((left, right) in listOf("hello... " to "world", "hello....  " to "world",
            "hello.." to "world", "hello.. " to "5", "camelCase.. " to "word",
            "a@example.. " to "word", "foo_bar.. " to "word", "name/path.. " to "word")) {
            val f = Fixture(); f.rawSequence(left); f.type(right)
            assertEquals(left + right, f.document); assertNull(f.controller.state.lastAutoEdit)
        }
        val f = Fixture(); f.type("hello"); f.type("."); f.type(".")
        assertEquals("hello..", f.document)
        f.type("."); f.type(" "); f.type("word")
        assertEquals("hello... word", f.document)
    }

    @Test fun `first dot outside live span cannot be adopted by deferred rule`() {
        val f = Fixture(); f.raw("hello"); f.raw("."); f.controller.finishComposition(f.execute)
        f.raw("."); f.raw(" "); f.type("world")
        assertEquals("hello.. world", f.document); assertNull(f.controller.state.lastAutoEdit)
        assertEquals(". world", f.sent.last())
    }

    @Test fun `ellipsis mixed expressive punctuation symbols technical and numeric forms stay raw`() {
        for ((left, right) in listOf("word?!" to "next", "word!? " to "next", "3." to "14",
            "1," to "5", "12:" to "30", "1.2." to "3", "example." to "com",
            "127.0.0." to "1", "http://x," to "next", "name@host," to "next",
            "/tmp/file," to "next", "x = value " to ",", "[word " to ",",
            "«word " to ",", "word😀 " to ",", "word\t" to ",", "word\u00a0" to ",")) {
            val f = Fixture(); f.rawSequence(left); f.type(right)
            assertEquals(left + right, f.document); assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `settings are independent and decoded changes affect very next action`() {
        val f = Fixture(); f.policy = enabled.copy(enabled = false, doubleSpaceEnabled = true)
        f.type("hello"); f.type(" "); f.type(" ", gesture = true)
        assertEquals("hello. ", f.document); assertTrue(f.controller.sentenceCapitalizationPending)
        f.undo(); assertEquals("hello ", f.document)
        f.policy = enabled.copy(enabled = true, doubleSpaceEnabled = false)
        f.type(" ", gesture = true); assertEquals("hello ", f.document)
        f.undo(); assertEquals("hello  ", f.document)
        val raw = mutableMapOf<String, Any?>(SettingsCodec.KEY_SCHEMA_VERSION to 3,
            SettingsCodec.KEY_AUTOCORRECTION_MODE to "OFF", SettingsCodec.KEY_CANDIDATE_STRIP to true,
            SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE to "OFF",
            SettingsCodec.KEY_DOUBLE_SPACE_PERIOD to false, SettingsCodec.KEY_MECHANICAL_PUNCTUATION to false)
        f.policy = f.policy.copy(enabled = SettingsCodec.decode(raw).mechanicalPunctuation)
        f.controller.discardUndo(); f.type(","); assertEquals("hello  ,", f.document)
        raw[SettingsCodec.KEY_MECHANICAL_PUNCTUATION] = true
        f.policy = f.policy.copy(enabled = SettingsCodec.decode(raw).mechanicalPunctuation)
        f.controller.discardUndo(); f.type("world"); assertEquals("hello, world", f.document)
        assertEquals(AutocorrectionMode.OFF, SettingsCodec.decode(raw).autocorrectionMode)
    }

    @Test fun `declined gesture inserts one ordinary space without old conversion bypass`() {
        for (word in listOf("3.14", "😀", "example.com")) {
            val f = Fixture(); f.policy = enabled.copy(doubleSpaceEnabled = true)
            f.rawSequence(word); f.type(" "); f.calls.clear(); f.type(" ", gesture = true)
            assertEquals(word + "  ", f.document)
            assertEquals(listOf("set"), f.calls); assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `manual lowercase once locked and auto use pre reducer keyboard state`() {
        val manualOff = KeyboardState.initial(KeyboardLanguage.ENGLISH, true).onShiftPressed(10)
        for ((keyboard, expected) in listOf(manualOff to "world",
            KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.ONCE) to "World",
            KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.LOCKED) to "World",
            KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.AUTO) to "World")) {
            val f = Fixture(); f.raw("hello"); f.raw("!"); f.raw(" "); f.keyboard = keyboard
            f.type("world"); assertEquals("hello! $expected", f.document)
            if (expected == "world") assertNull(f.controller.state.lastAutoEdit)
            else { f.undo(); assertEquals("hello! world", f.document) }
        }
        val f = Fixture(); f.raw("hello"); f.raw("!"); f.keyboard = manualOff
        f.type("world"); assertEquals("hello! world", f.document)
        f.undo(); assertEquals("hello!world", f.document)
        assertEquals(ShiftMode.AUTO, manualOff.afterTextCommitted().withAutomaticCapitalization(true).shiftMode)
    }

    @Test fun `manual lowercase suppression never lowercases explicitly supplied uppercase text`() {
        val f = Fixture(); f.raw("hello"); f.raw("."); f.raw(" ")
        f.keyboard = KeyboardState.initial(KeyboardLanguage.ENGLISH, true).onShiftPressed(1)
        f.type("World"); assertEquals("hello. World", f.document)
        assertNull(f.controller.state.lastAutoEdit)
    }

    @Test fun `disabled mechanics preserves legacy caps request after sentence and ordinary word spaces`() {
        for ((flags, punctuation) in listOf(0x4000 to ".", 0x2000 to "")) {
            val context = EditorContext.from(1 or flags, 0)
            val f = Fixture(context = context); f.policy = enabled.copy(enabled = false)
            f.type("hello"); if (punctuation.isNotEmpty()) f.type(punctuation); f.type(" ")
            var reads = 0
            val result = KeyboardSessionPolicy.withAutomaticCapitalization(f.keyboard, context,
                !f.controller.state.composing?.typedWord.isNullOrEmpty(),
                f.controller.sentenceCapitalizationPending) { reads++; flags }
            assertEquals(1, reads); assertEquals(ShiftMode.AUTO, result.shiftMode)
            assertEquals("hello" + punctuation + " ", f.document)
            assertNull(f.controller.state.lastAutoEdit)
        }
    }

    @Test fun `symbols layer never receives sentence capitalization`() {
        val f = Fixture(); f.raw("hello"); f.raw("!")
        f.keyboard = f.keyboard.copy(layer = KeyboardLayer.SYMBOLS)
        f.type("world"); assertEquals("hello! world", f.document)
    }

    @Test fun `rejected mechanical replacement freezes span without replay or publishing undo`() {
        val f = Fixture(); f.raw("hello"); f.raw(" "); f.calls.clear(); f.reject = true
        assertEquals(TypingTextResult.REJECTED, f.type(","))
        assertEquals(listOf("set", "finish"), f.calls)
        assertEquals("hello ", f.document); assertFalse(f.controller.state.enabled)
        assertNull(f.controller.state.lastAutoEdit)
        assertFalse(f.controller.sentenceCapitalizationPending)
    }

    @Test fun `reentrant session switch and external selection abort compound edit`() {
        for (newSession in listOf(false, true)) {
            val f = Fixture(); f.raw("hello"); f.raw("!"); f.calls.clear()
            f.afterSet = {
                if (newSession) f.controller.startSession(editor, 0, 0)
                else f.controller.updateSelection(25, 25, -1, -1) { true }
            }
            assertEquals(TypingTextResult.REJECTED, f.type("world"))
            assertEquals(listOf("set"), f.calls); assertNull(f.controller.state.lastAutoEdit)
            assertEquals("", f.controller.state.contextText)
        }
    }

    @Test fun `synchronous delayed and coalesced boundary callbacks preserve raw and undo`() {
        val f = Fixture(); f.synchronous = true
        f.type("hello"); f.type(" "); f.type(","); f.type("world")
        assertEquals("hello, world", f.document)
        f.synchronous = false; f.undo(); f.raw("x")
        assertFalse(f.controller.updateSelection(f.caret, f.caret, f.start, f.caret) { true })
        assertEquals("hello,worldx", f.document)
    }

    @Test fun `unknown prefix sliced word and long word cannot claim a complete owned token`() {
        val f = Fixture(initialCaret = 50); f.raw("hello"); f.raw(" "); f.type(",")
        assertEquals("x".repeat(50) + "hello ,", f.document); assertNull(f.controller.state.lastAutoEdit)
        f.raw(" "); f.raw("next"); f.raw(" "); f.type(",")
        assertTrue(f.document.endsWith("hello , next,"))
        val long = Fixture(); long.raw("a".repeat(300)); long.raw(" "); long.type(",")
        assertEquals("a".repeat(300) + " ,", long.document)
        assertNull(long.controller.state.lastAutoEdit)
    }

    @Test fun `bounded raw undo captures different eviction prefix than shorter applied value`() {
        val f = Fixture(); f.raw("x ".repeat(509) + "hello"); f.raw(" "); f.raw(" ")
        val before = f.controller.state.contextText
        val oracle = SessionTextContext(jvmGraphemes).apply { restore(before); append(",") }.text
        f.type(","); assertEquals("x ".repeat(509) + "hello,", f.document)
        f.undo(); assertEquals(oracle, f.controller.state.contextText)
        assertTrue(f.document.endsWith("hello  ,"))
        assertEquals(1_024, oracle.codePointCount(0, oracle.length))
    }

    @Test fun `boundary span overflow is raw bounded and later edits never readopt old prefix`() {
        val f = Fixture(); f.raw("hello"); repeat(257) { f.raw(".") }
        assertEquals("hello" + ".".repeat(257), f.document)
        assertEquals(".", f.controller.state.composing?.text)
        f.type("word"); assertEquals(".word", f.sent.last()); assertNull(f.controller.state.lastAutoEdit)
    }

    @Test fun `nontext sensitive and raw editors never enter mechanical composition`() {
        for (context in listOf(editor.copy(isPassword = true), editor.copy(noPersonalizedLearning = true),
            editor.copy(requiresRawKeyEvents = true), editor.copy(mode = EditorMode.NUMBER),
            editor.copy(mode = EditorMode.EMAIL), editor.copy(mode = EditorMode.URI))) {
            val f = Fixture(context = context)
            assertEquals(TypingTextResult.BYPASS, f.type("word")); assertTrue(f.calls.isEmpty())
            assertEquals("", f.controller.state.contextText)
        }
    }

    @Test fun `next input settings selection and lifecycle close mechanical undo and candidate ids`() {
        for (boundary in 0..4) {
            val f = Fixture(); f.raw("hello"); f.raw("!"); f.type("world")
            val id = checkNotNull(f.controller.originalCandidateId)
            when (boundary) {
                0 -> f.type("s")
                1 -> f.controller.discardUndo()
                2 -> f.controller.invalidate(f.execute)
                3 -> f.controller.endSession()
                4 -> f.controller.updateSelection(0, 0, -1, -1) { true }
            }
            assertNull(f.controller.state.lastAutoEdit)
            if (boundary != 1) assertFalse(f.controller.selectOriginal(id))
        }
    }

    @Test fun `original veto stays with same word and does not leak through punctuation boundary`() {
        val f = Fixture(); f.raw("hello")
        assertTrue(f.controller.selectOriginal(checkNotNull(f.controller.originalCandidateId)))
        f.type(","); assertFalse(f.controller.state.originalSelected)
        f.type("world"); val id = checkNotNull(f.controller.originalCandidateId)
        f.type("s"); assertFalse(f.controller.selectOriginal(id))
    }

    @Test fun `enter layer cursor and language owner boundaries finish without adding final period`() {
        for (await in listOf(false, true)) {
            val f = Fixture(); f.raw("hello"); f.raw(" "); f.calls.clear()
            if (await) f.controller.awaitEditorSelection(f.execute) else f.controller.invalidate(f.execute)
            assertEquals("hello ", f.document); assertEquals(listOf("finish"), f.calls)
            assertNull(f.controller.state.composing); assertNull(f.controller.state.lastAutoEdit)
            assertEquals("", f.controller.state.contextText)
        }
    }

    @Test fun `payload diagnostics remain redacted`() {
        val f = Fixture(); f.raw("sentinel"); f.raw("!"); f.type("privateword")
        for (value in listOf(f.controller.state, f.controller.state.composing, f.controller.state.lastAutoEdit)) {
            assertFalse(value.toString().contains("sentinel")); assertFalse(value.toString().contains("privateword"))
        }
    }

    private inner class Fixture(initialCaret: Int = 0, context: EditorContext = editor) {
        val controller = TypingSessionController(jvmGraphemes).apply { startSession(context, initialCaret, initialCaret) }
        var document = "x".repeat(initialCaret)
        var caret = initialCaret
        var start = -1
        var reject = false
        var synchronous = false
        var afterSet: (() -> Unit)? = null
        var reads = 0
        var policy = enabled
        var keyboard = KeyboardState(KeyboardLanguage.ENGLISH)
        val calls = mutableListOf<String>()
        val sent = mutableListOf<String>()
        private val connection = Proxy.newProxyInstance(InputConnection::class.java.classLoader,
            arrayOf(InputConnection::class.java)) { _, method, args ->
            when (method.name) {
                "setComposingText", "commitText" -> {
                    val value = args!![0].toString(); val composing = method.name == "setComposingText"
                    calls.add(if (composing) "set" else "commit"); sent.add(value)
                    if (!reject) {
                        val from = if (start < 0) caret else start
                        document = document.substring(0, from) + value + document.substring(caret)
                        caret = from + value.length; start = if (composing) from else -1
                        if (synchronous) assertFalse(controller.updateSelection(caret, caret, start,
                            if (start < 0) -1 else caret) { true })
                    }
                    if (composing) afterSet?.invoke()
                    !reject
                }
                "finishComposingText" -> { calls.add("finish"); start = -1
                    if (synchronous) assertFalse(controller.updateSelection(caret, caret, -1, -1) { true })
                    true
                }
                else -> { reads++; throw AssertionError("Unexpected editor operation") }
            }
        } as InputConnection
        val execute: (TypingEdit) -> Boolean = { edit ->
            EditorCommandExecutor.execute(when (edit) {
                is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
                is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
                TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
                else -> throw AssertionError("Unexpected correction command without qualification")
            }, connection, false, false).handled
        }
        fun type(text: String, gesture: Boolean = false) = controller.typeText(text, policy, keyboard, gesture, execute = execute)
        fun raw(text: String) = controller.typeText(text, execute)
        fun rawSequence(text: String) { text.codePoints().forEach { raw(String(Character.toChars(it))) } }
        fun undo() = controller.deletePrevious(execute)
    }
}
