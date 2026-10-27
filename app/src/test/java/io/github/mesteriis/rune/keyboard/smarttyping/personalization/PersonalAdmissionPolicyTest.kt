package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.controls.ProtectedWord
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlSnapshot
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import org.junit.Assert.*
import org.junit.Test

class PersonalAdmissionPolicyTest {
    @Test fun protectedWordAndUnavailableControlsHaveDistinctReasonsWithTheSameVeto() {
        for (enabled in listOf(false, true)) for (ready in listOf(false, true)) {
            for (present in listOf(false, true)) {
                val snapshot = TypingControlSnapshot(words = if (present)
                    listOf(ProtectedWord(KeyboardLanguage.ENGLISH, "helloo")) else emptyList())
                var reads = 0
                val refusal = PersonalAdmissionPolicy.protectedOriginalRefusal(enabled, ready) {
                    reads++
                    snapshot.contains("Helloo", KeyboardLanguage.ENGLISH)
                }
                val expected = when {
                    !enabled -> null
                    !ready -> AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE
                    present -> AutomaticAdmissionRefusal.PROTECTED_WORD
                    else -> null
                }
                assertEquals(expected, refusal)
                assertEquals(enabled && (!ready || present), refusal != null)
                assertEquals(if (enabled && ready) 1 else 0, reads)
            }
        }
    }

    @Test fun personalConfirmationAndPairRejectionKeepTheirExistingReadinessGate() {
        val language = KeyboardLanguage.ENGLISH
        for (ready in listOf(false, true)) for (confirmed in listOf(false, true)) {
            for (rejected in listOf(false, true)) {
                val model = PersonalTypingModel { _, _ -> false }
                if (confirmed) assertTrue(model.recordConfirmedWord("helloo", language))
                if (rejected) model.recordRejected("helloo", "hello", language)
                val before = model.snapshot()
                val refusal = PersonalAdmissionPolicy.personalRefusal(ready, model, "Helloo", "Hello", language)
                assertEquals(if (ready && (confirmed || rejected)) AutomaticAdmissionRefusal.PERSONAL_VETO else null,
                    refusal)
                assertEquals(before, model.snapshot())
                // Evidence remains scoped to its actual language.
                assertNull(PersonalAdmissionPolicy.personalRefusal(ready, model, "helloo", "hello",
                    KeyboardLanguage.SPANISH))
            }
        }
    }

    @Test fun pairRejectionDoesNotProtectOtherReplacements() {
        val model = PersonalTypingModel { _, _ -> false }
        model.recordRejected("helloo", "hello", KeyboardLanguage.ENGLISH)
        assertEquals(AutomaticAdmissionRefusal.PERSONAL_VETO,
            PersonalAdmissionPolicy.personalRefusal(true, model, "helloo", "hello", KeyboardLanguage.ENGLISH))
        assertNull(PersonalAdmissionPolicy.personalRefusal(true, model, "helloo", "help", KeyboardLanguage.ENGLISH))
    }
}
