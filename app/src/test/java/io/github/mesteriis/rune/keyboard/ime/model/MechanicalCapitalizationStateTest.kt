package io.github.mesteriis.rune.keyboard.ime.model

import org.junit.Assert.*
import org.junit.Test

class MechanicalCapitalizationStateTest {
    @Test fun `manual lowercase survives automatic hint until next text action`() {
        val off = KeyboardState.initial(KeyboardLanguage.ENGLISH, true).onShiftPressed(100)
        assertEquals(ShiftMode.OFF, off.withAutomaticCapitalization(true).shiftMode)
        val transition = KeyboardReducer.reduce(off, KeyboardAction.CommitLetter("Word"), EditorContext.from(1, 0), 200)
        assertEquals(EditorCommand.CommitText("word"), transition.command)
        assertEquals(ShiftMode.AUTO, transition.state.withAutomaticCapitalization(true).shiftMode)
        // Controller renders against off, not transition.state whose one-action suppression ended.
        assertEquals(ShiftMode.OFF, off.withAutomaticCapitalization(true).shiftMode)
    }

    @Test fun `explicit off from once or locked suppresses while explicit uppercase clears it`() {
        val initial = KeyboardState(KeyboardLanguage.ENGLISH)
        for (off in listOf(initial.onShiftPressed(0).onShiftPressed(1_000),
            initial.copy(shiftMode = ShiftMode.LOCKED).onShiftPressed(0))) {
            assertEquals(ShiftMode.OFF, off.withAutomaticCapitalization(true).shiftMode)
            assertEquals(ShiftMode.ONCE, off.onShiftPressed(2_000).withAutomaticCapitalization(false).shiftMode)
            assertEquals(ShiftMode.AUTO, off.afterTextCommitted().withAutomaticCapitalization(true).shiftMode)
        }
    }

    @Test fun `automatic off double tap preserves lock timing and manual lock persists across text`() {
        val off = KeyboardState.initial(KeyboardLanguage.ENGLISH, true).onShiftPressed(100)
            .withAutomaticCapitalization(true)
        val locked = off.onShiftPressed(200)
        assertEquals(ShiftMode.LOCKED, locked.shiftMode)
        assertEquals(ShiftMode.LOCKED, locked.afterTextCommitted().withAutomaticCapitalization(false).shiftMode)
        assertEquals(ShiftMode.ONCE, off.onShiftPressed(1_000).shiftMode)
    }

    @Test fun `actual language or layer transition clears suppression but same language swipe preserves it`() {
        val off = KeyboardState.initial(KeyboardLanguage.ENGLISH, true,
            enabledLanguages = listOf(KeyboardLanguage.ENGLISH)).onShiftPressed(1)
        assertEquals(ShiftMode.OFF, off.switchLanguage(LanguageDirection.NEXT).withAutomaticCapitalization(true).shiftMode)
        assertEquals(ShiftMode.AUTO, off.useLanguage(KeyboardLanguage.RUSSIAN).withAutomaticCapitalization(true).shiftMode)
        assertEquals(ShiftMode.AUTO, off.toggleSymbols().toggleSymbols().withAutomaticCapitalization(true).shiftMode)
        assertEquals(ShiftMode.AUTO, off.withEnabledLanguages(listOf(KeyboardLanguage.SPANISH)).withAutomaticCapitalization(true).shiftMode)
    }

    @Test fun `legacy sentence and word caps lookup stays available with mechanical punctuation disabled`() {
        for (mode in listOf(0x4000, 0x2000)) { // TYPE_TEXT_FLAG_CAP_SENTENCES / CAP_WORDS
            val editor = EditorContext.from(1 or mode, 0)
            var reads = 0
            val settings = io.github.mesteriis.rune.keyboard.settings.KeyboardSettings.DEFAULT.copy(mechanicalPunctuation = false)
            val state = KeyboardSessionPolicy.withAutomaticCapitalization(
                KeyboardState(KeyboardLanguage.ENGLISH), editor, hasComposingWord = false,
                ownedSentenceBoundary = false,
            ) { reads++; mode }
            assertFalse(settings.mechanicalPunctuation)
            assertEquals(1, reads)
            assertEquals(ShiftMode.AUTO, state.shiftMode)
            val manualOff = state.onShiftPressed(1)
            assertEquals(ShiftMode.OFF, KeyboardSessionPolicy.withAutomaticCapitalization(
                manualOff, editor, false, false) { reads++; mode }.shiftMode)
            assertEquals(2, reads)
        }
    }

    @Test fun `owned gesture composing word and guarded modes never add a caps lookup`() {
        var reads = 0
        val state = KeyboardState(KeyboardLanguage.ENGLISH)
        val editor = EditorContext.from(1, 0)
        fun caps(context: EditorContext, word: Boolean, boundary: Boolean) =
            KeyboardSessionPolicy.withAutomaticCapitalization(state, context, word, boundary) { reads++; 0 }
        assertEquals(ShiftMode.AUTO, caps(editor, false, true).shiftMode)
        assertEquals(ShiftMode.OFF, caps(editor, true, false).shiftMode)
        for (context in listOf(editor.copy(isPassword = true), editor.copy(noPersonalizedLearning = true),
            editor.copy(requiresRawKeyEvents = true), editor.copy(mode = EditorMode.NUMBER))) {
            assertEquals(ShiftMode.OFF, caps(context, false, true).shiftMode)
        }
        assertEquals(0, reads)
        assertEquals(state, KeyboardSessionPolicy.withAutomaticCapitalization(state, editor, false, false) { null })
    }

    @Test fun `gesture consumes old lowercase suppression before priming next action`() {
        val off = KeyboardState.initial(KeyboardLanguage.ENGLISH, true).onShiftPressed(1)
        val transition = KeyboardReducer.reduce(off, KeyboardAction.DoubleSpaceTap, EditorContext.from(1, 0), 2)
        assertEquals(EditorCommand.ConvertPrecedingSpaceToPeriod, transition.command)
        assertEquals(ShiftMode.AUTO, transition.state.withAutomaticCapitalization(true).shiftMode)
    }
}
