package io.github.mesteriis.rune.keyboard.smarttyping.telemetry

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class SmartTypingTraceTest {
    @Test fun `trace vocabulary is the complete fixed release set`() {
        assertEquals(
            listOf(
                "Rune#composeUpdate",
                "Rune#candidateGenerate",
                "Rune#candidateRank",
                "Rune#modelRequest",
                "Rune#modelResult",
                "Rune#candidateRender",
                "Rune#correctionCommit",
                "Rune#correctionUndo",
                "Rune#punctuationRule",
            ),
            SmartTypingTraceSection.entries.map { it.sectionName },
        )
    }

    @Test fun `section balances trace sink after failure`() {
        val events = mutableListOf<String>()
        val trace = object : SmartTypingTracer {
            override fun begin(section: SmartTypingTraceSection) { events += "begin:${section.sectionName}" }
            override fun end() { events += "end" }
        }

        assertThrows(IllegalStateException::class.java) {
            trace.section(SmartTypingTraceSection.MODEL_RESULT) { error("synthetic") }
        }
        assertEquals(listOf("begin:Rune#modelResult", "end"), events)
    }
}
