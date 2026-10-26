package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.security.MessageDigest

class JointRescueQualificationTest {
    @Test fun sourcePinsItsOwnModelPolicyThresholdsAndAllDictionaries() {
        val f = JointRescueQualification.fingerprint()
        assertTrue(JointRescueQualification.allows(f))
        assertTrue(JointRescueQualification.enabled(KeyboardLanguage.RUSSIAN))
        assertFalse(JointRescueQualification.enabled(KeyboardLanguage.ENGLISH))
        assertFalse(JointRescueQualification.allows(JointQualification.fingerprint()))
        for (changed in listOf(f.copy(searchVersion = 2), f.copy(rankerSha256 = "changed"),
            f.copy(policySha256 = "changed"), f.copy(contextSha256 = "changed"),
            f.copy(morphologySha256 = "changed"), f.copy(rareWordsSha256 = "changed"),
            f.copy(lexiconSha256 = "changed"), f.copy(thresholds = RecoveryThresholds(.9, .9))))
            assertFalse(JointRescueQualification.allows(changed))
        val bytes = File("src/main/assets/smarttyping/experiments/ru-joint-rescue-ranker.bin").readBytes()
        assertEquals(JointRescueQualification.RANKER_BYTES, bytes.size)
        assertEquals(JointRescueQualification.RANKER_SHA256, MessageDigest.getInstance("SHA-256")
            .digest(bytes).joinToString("") { "%02x".format(it) })
        val policy = File("src/main/assets/smarttyping/experiments/ru-joint-rescue-policy.json").readBytes()
        assertEquals(JointRescueQualification.POLICY_SHA256, MessageDigest.getInstance("SHA-256")
            .digest(policy).joinToString("") { "%02x".format(it) })
    }
}
