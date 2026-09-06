package io.github.mesteriis.rune.keyboard.settings

import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.*
import org.junit.Test

class ContextualAvailabilityTest {
    @Test fun `preference and effective model availability stay independent`() {
        assertNull(ContextualAvailability.summaryResource(ContextualPunctuationMode.OFF, false))
        assertNull(ContextualAvailability.summaryResource(ContextualPunctuationMode.OFF, true))
        assertEquals(R.string.settings_contextual_unavailable,
            ContextualAvailability.summaryResource(ContextualPunctuationMode.SUGGESTIONS, false))
        assertEquals(R.string.settings_contextual_ready,
            ContextualAvailability.summaryResource(ContextualPunctuationMode.SUGGESTIONS, true))
    }
}
