package io.github.mesteriis.rune.keyboard.smarttyping.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class SmartTypingViewStateTest {
    private val original = CandidateUiItem.Original("session:1:original", "teh")
    private val correction = CandidateUiItem.Correction("session:1:correction", "the")

    @Test
    fun visibleSetIncludesOriginalAndSelectsById() {
        val state = SmartTypingViewState(true, listOf(original, correction), correction.id)
        assertEquals(2, state.candidates.size)
        assertEquals(correction.id, state.selectedCandidateId)
    }

    @Test
    fun hiddenAndEmptyAreDistinctAndRetainNoText() {
        assertFalse(SmartTypingViewState.HIDDEN.enabled)
        assertTrue(SmartTypingViewState.EMPTY.enabled)
        assertTrue(SmartTypingViewState.HIDDEN.candidates.isEmpty())
        assertTrue(SmartTypingViewState.EMPTY.candidates.isEmpty())
        assertThrows(IllegalArgumentException::class.java) { SmartTypingViewState(false, listOf(original)) }
    }

    @Test
    fun rejectsMoreThanThreeOrMissingOriginalOrDuplicateIds() {
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, listOf(original, correction, correction, correction))
        }
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, listOf(correction))
        }
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, listOf(original, original.copy(id = "another")))
        }
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, listOf(original, correction.copy(id = original.id)))
        }
    }

    @Test
    fun rejectsMissingOrDanglingSelection() {
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, listOf(original), "stale")
        }
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, listOf(original), null)
        }
        assertThrows(IllegalArgumentException::class.java) {
            SmartTypingViewState(true, emptyList(), original.id)
        }
    }

    @Test
    fun makesImmutableSnapshotOfCallerList() {
        val source = mutableListOf<CandidateUiItem>(original)
        val state = SmartTypingViewState(true, source)
        source.clear()
        assertEquals(listOf(original), state.candidates)
        assertThrows(UnsupportedOperationException::class.java) {
            (state.candidates as MutableList<CandidateUiItem>).clear()
        }
    }

    @Test
    fun candidatePayloadsAndIdsAreBounded() {
        assertThrows(IllegalArgumentException::class.java) { CandidateUiItem.Original("", "text") }
        assertThrows(IllegalArgumentException::class.java) { CandidateUiItem.Correction("id", " ") }
        assertThrows(IllegalArgumentException::class.java) {
            CandidateUiItem.Punctuation("id", "x".repeat(CandidateUiItem.MAX_TEXT_UTF16 + 1))
        }
        assertThrows(IllegalArgumentException::class.java) {
            CandidateUiItem.Original("x".repeat(CandidateUiItem.MAX_ID_LENGTH + 1), "text")
        }
    }

    @Test
    fun diagnosticsRedactTextAndOpaqueIds() {
        val text = "private-token"
        val id = "private-session"
        val items = listOf(
            CandidateUiItem.Original(id, text),
            CandidateUiItem.Correction("correction", text),
            CandidateUiItem.Punctuation("punctuation", text),
        )
        val diagnostic = items.toString() + SmartTypingViewState(true, items, id)
        assertFalse(diagnostic.contains(text))
        assertFalse(diagnostic.contains(id))
    }
}
