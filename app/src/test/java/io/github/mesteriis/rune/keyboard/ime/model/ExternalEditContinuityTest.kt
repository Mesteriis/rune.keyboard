package io.github.mesteriis.rune.keyboard.ime.model

import org.junit.Assert.*
import org.junit.Test

class ExternalEditContinuityTest {
    @Test fun sameFrameworkEditorRestartRetainsOnlyTheProtectiveFlag() {
        for (id in listOf(-1, 0, 42)) {
            val continuity = ExternalEditContinuity()
            assertFalse(continuity.onStart("qa.example", id, false, 0, 0))
            continuity.arm()
            assertTrue(continuity.onStart("qa.example", id, true, 0, 0))
            assertTrue(continuity.onStart("qa.example", id, true, 0, 0))
        }
    }

    @Test fun freshStartEvenWithReusedMetadataAndOtherFieldsNeverRetainTheFlag() {
        for (next in listOf(Triple("qa.example", 42, false), Triple("qa.example", 43, true),
            Triple("qa.other", 42, true), Triple("", 42, true))) {
            val continuity = ExternalEditContinuity()
            continuity.onStart("qa.example", 42, false, 0, 0)
            continuity.arm()
            assertFalse(continuity.onStart(next.first, next.second, next.third, 0, 0))
            assertFalse(continuity.onStart("qa.example", 42, true, 0, 0))
        }
    }

    @Test fun onlyAnEnabledControllerCanAcknowledgeItsOwnedBoundary() {
        val continuity = ExternalEditContinuity()
        continuity.onStart("qa.example", 42, false, 0, 0)
        continuity.arm()
        continuity.observe(false, false)
        assertTrue(continuity.onStart("qa.example", 42, true, 0, 0))
        continuity.observe(true, false)
        assertFalse(continuity.onStart("qa.example", 42, true, 0, 0))
    }
    @Test fun coldStartsWithUnknownLeftContextRequireANewOwnedBoundary() {
        for (position in listOf(1, 12, Int.MAX_VALUE)) {
            for (restarting in listOf(false, true)) {
                val continuity = ExternalEditContinuity()
                assertTrue(continuity.onStart("qa.example", 42, restarting, position, position))
            }
        }
    }

    @Test fun unknownLeftContextDoesNotRequireReusableEditorIdentity() {
        for (pkg in listOf(null, "", "qa.example")) {
            val continuity = ExternalEditContinuity()
            assertTrue(continuity.onStart(pkg, 0, false, 4, 9))
            assertTrue(continuity.onStart(pkg, -1, true, 9, 4))
        }
    }

    @Test fun zeroLeftBoundaryOrUnknownPositionsDoNotInventPrecedingText() {
        for ((from, to) in listOf(0 to 0, 0 to 9, 9 to 0, -1 to -1, -1 to 12, 12 to -1)) {
            val continuity = ExternalEditContinuity()
            assertFalse(continuity.onStart("qa.example", 42, false, from, to))
        }
    }

    @Test fun newSessionDoesNotAdoptAnEarlierOwnedSpaceAsItsOwnBoundary() {
        val continuity = ExternalEditContinuity()
        continuity.onStart("qa.example", 42, false, 0, 0)
        continuity.observe(true, false)
        assertTrue(continuity.onStart("qa.example", 42, true, 12, 12))
        continuity.observe(true, false)
        assertFalse(continuity.onStart("qa.example", 42, false, 0, 0))
    }

}
