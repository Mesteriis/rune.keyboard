package io.github.mesteriis.rune.keyboard.smarttyping.correction

import org.junit.Assert.*
import org.junit.Test

class RecoveryQualificationTest {
    @Test fun `only independently frozen local artifacts are qualified`() {
        val current = RecoveryQualification.fingerprint()
        assertTrue(RecoveryQualification.allows(current))
        for (changed in listOf(current.copy(searchVersion = 2), current.copy(rankerSha256 = "changed"),
            current.copy(policySha256 = "changed"), current.copy(thresholds = null), current.copy(contextSha256 = "changed"),
            current.copy(morphologySha256 = "changed"), current.copy(rareWordsSha256 = "changed"),
            current.copy(lexiconSha256 = "changed"))) assertFalse(RecoveryQualification.allows(changed))
        assertFalse(RecoveryQualification.MODEL_QUALIFIED)
    }
}
