package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CompactAutoCorrectionPolicyTest {
    @Test fun `abstains only for an unresolved single е э difference`() {
        assertTrue(CompactAutoCorrectionPolicy.hasUnresolvedRussianEEhRival(
            "грейсон", listOf("грейсон", "грэйсон")))
        assertTrue(CompactAutoCorrectionPolicy.hasUnresolvedRussianEEhRival(
            "тест", listOf("тест", "тэст", "текст")))
        assertFalse(CompactAutoCorrectionPolicy.hasUnresolvedRussianEEhRival(
            "ворами", listOf("ворами", "ерами", "эрами")))
        assertFalse(CompactAutoCorrectionPolicy.hasUnresolvedRussianEEhRival(
            "догнал", listOf("догнал", "погнал", "согнал")))
        assertFalse(CompactAutoCorrectionPolicy.hasUnresolvedRussianEEhRival(
            "грэйсон", listOf("грэйсон", "греисон")))
        assertFalse(CompactAutoCorrectionPolicy.hasUnresolvedRussianEEhRival(
            "это", listOf("это", "етоо")))
    }
}
