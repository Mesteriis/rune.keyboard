package io.github.mesteriis.rune.keyboard.ime.model

import org.junit.Assert.*
import org.junit.Test

class ExternalEditContinuityTest {
    @Test fun sameFrameworkEditorRestartRetainsOnlyTheProtectiveFlag() {
        for (id in listOf(-1, 0, 42)) {
            val continuity = ExternalEditContinuity()
            assertFalse(continuity.onStart("qa.example", id, false))
            continuity.arm()
            assertTrue(continuity.onStart("qa.example", id, true))
            assertTrue(continuity.onStart("qa.example", id, true))
        }
    }

    @Test fun freshStartEvenWithReusedMetadataAndOtherFieldsNeverRetainTheFlag() {
        for (next in listOf(Triple("qa.example", 42, false), Triple("qa.example", 43, true),
            Triple("qa.other", 42, true), Triple("", 42, true))) {
            val continuity = ExternalEditContinuity()
            continuity.onStart("qa.example", 42, false)
            continuity.arm()
            assertFalse(continuity.onStart(next.first, next.second, next.third))
            assertFalse(continuity.onStart("qa.example", 42, true))
        }
    }

    @Test fun onlyAnEnabledControllerCanAcknowledgeItsOwnedBoundary() {
        val continuity = ExternalEditContinuity()
        continuity.onStart("qa.example", 42, false)
        continuity.arm()
        continuity.observe(false, false)
        assertTrue(continuity.onStart("qa.example", 42, true))
        continuity.observe(true, false)
        assertFalse(continuity.onStart("qa.example", 42, true))
    }
}
