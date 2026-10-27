package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.view.inputmethod.EditorInfo
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingTextResult
import io.github.mesteriis.rune.keyboard.smarttyping.session.jvmGraphemes
import org.junit.Assert.*
import org.junit.Test

class IncognitoDiagnosticsTest {
    @Test fun incognitoCannotAdmitRecordReopenOrEditorOutcomeEvenWithAnEagerObserver() {
        val controller = TypingSessionController(jvmGraphemes)
        val observer = Observer()
        controller.setDiagnostics(observer)
        val editor = EditorContext.from(1, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING)
        controller.startSession(editor, 0, 0)
        assertTrue(controller.state.enabled)
        assertEquals(listOf(false), observer.admissions)
        val policy = MechanicalPunctuationPolicy(editor.inputPolicy, editor.mode, false, true, true)
        val keyboard = KeyboardState(KeyboardLanguage.ENGLISH)
        for (text in listOf("hello", " ", ",", "world")) {
            controller.reopenDiagnosticsForLetters(true, refreshEmpty = true)
            controller.recordInput(text, allowFreshDiagnostics = true)
            assertEquals(TypingTextResult.HANDLED, controller.typeText(text, policy, keyboard, execute = { true }))
        }
        assertTrue(controller.state.contextText.isNotEmpty())
        controller.deletePrevious { true }
        controller.endSession()
        assertEquals(listOf(false), observer.admissions)
        assertEquals(0, observer.records)
        assertEquals(0, observer.editorOutcomes)
    }

    @Test fun returningToNormalRestoresExplicitDiagnosticEligibility() {
        val controller = TypingSessionController(jvmGraphemes)
        val observer = Observer()
        controller.setDiagnostics(observer)
        controller.startSession(EditorContext.from(1, EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING), 0, 0)
        controller.startSession(EditorContext.from(1, 0), 0, 0)
        controller.recordInput("public")
        assertEquals(listOf(false, true), observer.admissions)
        assertTrue(observer.records > 0)
    }

    private class Observer : TypingDiagnostics {
        val admissions = mutableListOf<Boolean>()
        var records = 0
        var editorOutcomes = 0
        override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) { admissions += eligible }
        override fun invalidate() = Unit
        override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) { records++; text?.invoke() }
        override fun editorOutcome(event: DiagnosticEvent): ((Boolean) -> Unit)? { editorOutcomes++; return null }
    }
}
