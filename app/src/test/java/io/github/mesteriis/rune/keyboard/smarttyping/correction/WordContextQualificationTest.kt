package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test

class WordContextQualificationTest {
    @Test fun finiteSourcePinsExactRuleSearchAndDictionaries() {
        val f = WordContextQualification.fingerprint()
        assertTrue(WordContextQualification.allows(f))
        assertTrue(WordContextQualification.enabled(KeyboardLanguage.RUSSIAN))
        assertFalse(WordContextQualification.enabled(KeyboardLanguage.ENGLISH))
        for (changed in listOf(f.copy(policyVersion = 5), f.copy(searchVersion = 2),
            f.copy(ruleIdentity = "changed"), f.copy(morphologySha256 = "changed"),
            f.copy(rareWordsSha256 = "changed"), f.copy(lexiconSha256 = "changed")))
            assertFalse(WordContextQualification.allows(changed))
    }
}
