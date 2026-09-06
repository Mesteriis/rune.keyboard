package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.session.ComposingSegment
import io.github.mesteriis.rune.keyboard.smarttyping.session.UndoableTextEdit
import org.junit.Assert.*
import org.junit.Test

class MechanicalPunctuationPlannerTest {
    private val policy = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, true, false)
    private fun owned(text: String, composing: String? = text, complete: Boolean = true) =
        OwnedPunctuationSuffix(text, composing, complete, 17, 29)
    private fun plan(text: String, next: String, composing: String? = text) =
        MechanicalPunctuationPlanner.plan(owned(text, composing), PunctuationAction.Text(next), policy)
    private fun replacement(result: MechanicalPunctuationPlan) = result as MechanicalPunctuationPlan.Replace
    private fun reason(result: MechanicalPunctuationPlan) = (result as MechanicalPunctuationPlan.Unchanged).reason

    @Test fun `space before punctuation edits only pending span and consumes punctuation once`() {
        for (punctuation in listOf(",", ".", "?", "!", ":", ";")) {
            val edit = replacement(plan("Привет ", punctuation, " "))
            assertEquals(" ", edit.expectedComposing)
            assertEquals(punctuation, edit.replacementComposing)
            assertEquals(" " + punctuation, edit.undoOriginal)
            assertEquals(MechanicalEditKind.SPACE_BEFORE, edit.kind)
            assertEquals("Привет" + punctuation, "Привет" + edit.replacementComposing)
        }
    }

    @Test fun `compound comma cleanup produces one suffix transaction without replaying previous word`() {
        val edit = replacement(plan("Привет ,", "как", " ,"))
        assertEquals(", как", edit.replacementComposing)
        assertEquals(" ,как", edit.undoOriginal)
        assertEquals("Привет, как", "Привет" + edit.replacementComposing)
        assertEquals(17L, edit.sessionId)
        assertEquals(29L, edit.revision)
    }

    @Test fun `comma semicolon and Cyrillic colon insert missing space for ordinary next word`() {
        for ((before, next) in listOf("hello," to "world", "готово;" to "дальше", "важно:" to "слово")) {
            val edit = replacement(plan(before, next, before.takeLast(1)))
            assertEquals(before.takeLast(1) + " " + next, edit.replacementComposing)
            assertNull(edit.sentenceCapsForNewTextAt)
        }
    }

    @Test fun `question and exclamation request existing caps only for new action text`() {
        for (punctuation in listOf("?", "!")) {
            val edit = replacement(plan("Готово" + punctuation, "завтра", punctuation))
            assertEquals(punctuation + " завтра", edit.replacementComposing)
            assertEquals(2, edit.sentenceCapsForNewTextAt)
            assertEquals(punctuation + "завтра", edit.undoOriginal)
        }
        val late = replacement(plan("Готово?з", "а", "?з"))
        assertEquals("? за", late.replacementComposing)
        assertNull(late.sentenceCapsForNewTextAt) // never recase previously entered letters
    }

    @Test fun `double space gesture has priority even when mechanical cleanup is disabled`() {
        val edit = replacement(MechanicalPunctuationPlanner.plan(owned("hello ", " "),
            PunctuationAction.DoubleSpaceGesture, policy.copy(doubleSpaceEnabled = true, enabled = false)))
        assertEquals(MechanicalEditKind.DOUBLE_SPACE_PERIOD, edit.kind)
        assertEquals(". ", edit.replacementComposing)
        assertEquals(" ", edit.undoOriginal) // existing gesture Undo restores its pending first space
        assertTrue(edit.requestsSentenceCaps)
    }

    @Test fun `ordinary repeated spaces collapse without inventing gesture timing`() {
        val timedOut = replacement(MechanicalPunctuationPlanner.plan(owned("текст ", " "),
            PunctuationAction.Text(" "), policy.copy(doubleSpaceEnabled = true)))
        assertEquals(" ", timedOut.replacementComposing)
        assertEquals(MechanicalEditKind.REPEATED_SPACE, timedOut.kind)
        val second = replacement(plan("текст  ", "текст", "  "))
        assertEquals(" текст", second.replacementComposing)
        assertEquals("  текст", second.undoOriginal)
        assertEquals("текст текст", "текст" + second.replacementComposing)
    }

    @Test fun `disabled double space falls through to mechanical space cleanup`() {
        val edit = replacement(MechanicalPunctuationPlanner.plan(owned("hello ", " "),
            PunctuationAction.DoubleSpaceGesture, policy))
        assertEquals(MechanicalEditKind.REPEATED_SPACE, edit.kind)
        assertEquals(" ", edit.replacementComposing)
        assertEquals(UnchangedPunctuationReason.DISABLED, reason(MechanicalPunctuationPlanner.plan(
            owned("hello ", " "), PunctuationAction.DoubleSpaceGesture, policy.copy(enabled = false))))
    }

    @Test fun `single comma or semicolon duplication is one immediately reversible edit`() {
        for (punctuation in listOf(",", ";")) {
            val edit = replacement(plan("hello" + punctuation, punctuation, punctuation))
            assertEquals(punctuation, edit.replacementComposing)
            assertEquals(punctuation + punctuation, edit.undoOriginal)
            assertEquals(MechanicalEditKind.DUPLICATE_PUNCTUATION, edit.kind)
        }
        assertEquals(UnchangedPunctuationReason.OUTSIDE_COMPOSING_SPAN, reason(plan("hello,", ",", null)))
    }

    @Test fun `decimal time version URL email host IP path and code stay unchanged`() {
        val cases = listOf(
            "3." to "14", "1," to "5", "12:" to "30", "1.2." to "3",
            "example." to "com", "пример." to "рф", "127.0.0." to "1", "2001:db8:" to "ab",
            "dead:" to "beef", "https://example," to "hello", "name@example," to "com",
            "/tmp/value," to "name", "C:\\tmp\\value," to "name", "x = value " to ",",
            "call(value," to "next", "some_id " to ",", "camelCase " to ",", "value42 " to ",",
            "foo-bar " to ",", "urn:" to "example",
        )
        for ((before, next) in cases) assertTrue(plan(before, next) is MechanicalPunctuationPlan.Unchanged)
        for (before in listOf("3.14 ", "example.com ", "x = value ", "name@example.com ", "😀 ")) {
            assertTrue(MechanicalPunctuationPlanner.plan(owned(before), PunctuationAction.DoubleSpaceGesture,
                policy.copy(doubleSpaceEnabled = true)) is MechanicalPunctuationPlan.Unchanged)
        }
    }

    @Test fun `ambiguous dots never become sentence boundaries from unsupported inference`() {
        for (before in listOf("Хорошо.", "hello.", "example.")) {
            assertEquals(UnchangedPunctuationReason.AMBIGUOUS_DOT, reason(plan(before, "завтра")))
        }
        assertEquals(UnchangedPunctuationReason.AMBIGUOUS_COLON, reason(plan("hello:", "world")))
        // Explicitly entered sentence whitespace is distinguishable; only collapse surplus spaces.
        val edit = replacement(plan("Хорошо.  ", "завтра", ".  "))
        assertEquals(". завтра", edit.replacementComposing)
        assertEquals(2, edit.sentenceCapsForNewTextAt)
    }

    @Test fun `standalone command dot arguments keep their whitespace across later input`() {
        for (prefix in listOf("", "The reference lists ", "В справочнике найдено ", "La referencia indica ")) {
            for (command in listOf("find", "cd", "ls", "du", "stat", "cp", "mv", "rm", "chmod", "chown", "git", "rg", "grep", "echo", "printf")) {
                val before = "$prefix$command "
                assertEquals(UnchangedPunctuationReason.PROTECTED_TOKEN, reason(plan(before, ".", " ")))
                assertTrue(plan("$before.", " ", " .") is MechanicalPunctuationPlan.Unchanged)
                assertTrue(plan("$before. ", "w", " . ") is MechanicalPunctuationPlan.Unchanged)
            }
        }
        // A different word and a non-dot boundary retain ordinary punctuation behavior.
        assertEquals(MechanicalEditKind.SPACE_BEFORE, replacement(plan("hello ", ".", " ")).kind)
        assertEquals(MechanicalEditKind.SPACE_BEFORE, replacement(plan("find ", ",", " ")).kind)
        assertEquals(MechanicalEditKind.SPACE_BEFORE, replacement(plan("find .\nhello ", ".", " ")).kind)
    }

    @Test fun `ellipsis expressive punctuation quotes brackets and emoji are preserved`() {
        for ((before, next) in listOf("word." to ".", "word.." to ".", "word..." to "next",
            "word?!" to "next", "word!?" to "next", "word!" to "!", "word?" to "?",
            "[word " to ",", "word] " to ",", "«word " to ",", "word» " to ",",
            "word 👩🏽‍💻 " to ",", "word \u00A0" to ",", "word\t" to ",")) {
            assertTrue(plan(before, next) is MechanicalPunctuationPlan.Unchanged)
        }
    }

    @Test fun `SEND and all policy exclusions decline before touching malformed payload`() {
        val invalid = owned("\uD800", "mismatch")
        assertEquals(UnchangedPunctuationReason.SEND, reason(MechanicalPunctuationPlanner.plan(invalid, PunctuationAction.Send, policy)))
        assertEquals(UnchangedPunctuationReason.INPUT_POLICY, reason(MechanicalPunctuationPlanner.plan(invalid,
            PunctuationAction.Text(","), policy.copy(inputPolicy = InputPolicy.SENSITIVE))))
        for (mode in EditorMode.entries.filter { it != EditorMode.TEXT }) {
            assertEquals(UnchangedPunctuationReason.NON_TEXT_MODE, reason(MechanicalPunctuationPlanner.plan(invalid,
                PunctuationAction.Text(","), policy.copy(mode = mode))))
        }
        assertEquals(UnchangedPunctuationReason.RAW_EDITOR, reason(MechanicalPunctuationPlanner.plan(invalid,
            PunctuationAction.Text(","), policy.copy(requiresRawKeyEvents = true))))
        assertEquals(UnchangedPunctuationReason.NON_TEXT_ACTION, reason(MechanicalPunctuationPlanner.plan(
            owned("hello"), PunctuationAction.Other, policy)))
    }

    @Test fun `read only owned context is never replayed or silently adopted as composition`() {
        assertEquals(UnchangedPunctuationReason.OUTSIDE_COMPOSING_SPAN, reason(plan("hello ", ",", null)))
        assertEquals(UnchangedPunctuationReason.OUTSIDE_COMPOSING_SPAN, reason(plan("hello ,", "world", ",")))
        assertEquals(UnchangedPunctuationReason.OWNERSHIP_MISMATCH, reason(plan("hello,", "world", "other")))
        val fresh = replacement(plan("hello,", "world", null))
        assertNull(fresh.expectedComposing)
        assertEquals(" world", fresh.replacementComposing) // old "hello," is read-only and is not resent
    }

    @Test fun `bounded truncated and malformed contexts fail closed without normalization`() {
        assertEquals(UnchangedPunctuationReason.TRUNCATED_CONTEXT, reason(MechanicalPunctuationPlanner.plan(
            owned("word ", " ", false), PunctuationAction.Text(","), policy)))
        for (before in listOf("a".repeat(257), "\uD800")) {
            assertEquals(UnchangedPunctuationReason.INVALID_BOUNDS, reason(plan(before, ",")))
        }
        assertEquals(UnchangedPunctuationReason.INVALID_BOUNDS, reason(plan("hello,", "a".repeat(33))))
        val edit = replacement(plan("cafe\u0301 ", ",", " "))
        assertEquals(",", edit.replacementComposing)
        assertEquals("cafe\u0301,", "cafe\u0301" + edit.replacementComposing) // no NFC rewrite of old text
    }

    @Test fun `proposal adapts to existing single UndoableTextEdit without parallel storage`() {
        val edit = replacement(plan("Привет ,", "как", " ,"))
        val transaction = UndoableTextEdit(edit.undoOriginal, edit.replacementComposing,
            edit.sessionId, edit.revision + 1,
            ComposingSegment(leadingBoundary = " ,", typedWord = "как"), "Привет ,как")
        assertEquals(" ,как", transaction.original)
        assertEquals(", как", transaction.applied)
        assertEquals(transaction.original, transaction.restoreComposition.text)
        assertFalse(transaction.toString().contains("как"))
        assertFalse(edit.toString().contains("как"))
        assertFalse(owned("private").toString().contains("private"))
        assertFalse(PunctuationAction.Text("private").toString().contains("private"))
    }
}
