package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.security.MessageDigest

class JointQualificationTest {
    @Test fun sourcesHaveTheirOwnIdentityAndBoundedRussianScope() {
        val fingerprint = JointQualification.fingerprint()
        assertTrue(JointQualification.allows(fingerprint))
        val bytes = File("src/main/assets/smarttyping/experiments/ru-joint-ranker.bin").readBytes()
        assertEquals(JointQualification.RANKER_BYTES, bytes.size)
        assertEquals(JointQualification.RANKER_SHA256, MessageDigest.getInstance("SHA-256")
            .digest(bytes).joinToString("") { "%02x".format(it) })
        assertTrue(JointQualification.enabled(KeyboardLanguage.RUSSIAN, 3))
        assertTrue(JointQualification.enabled(KeyboardLanguage.RUSSIAN, 4))
        assertFalse(JointQualification.enabled(KeyboardLanguage.RUSSIAN, 2))
        assertTrue(JointQualification.enabled(KeyboardLanguage.RUSSIAN, 5))
        assertTrue(JointQualification.enabled(KeyboardLanguage.RUSSIAN, 32))
        assertFalse(JointQualification.enabled(KeyboardLanguage.RUSSIAN, 33))
        assertFalse(JointQualification.enabled(KeyboardLanguage.ENGLISH, 3))
        assertTrue(SpellingQualification.CURRENT.allows(KeyboardLanguage.RUSSIAN, SpellingSource.JOINT_LONG))
        assertFalse(JointQualification.allowsLong(fingerprint, JointQualification.thresholds.retention))
        assertTrue(JointQualification.allowsLong(JointQualification.longFingerprint(), JointQualification.thresholds.retention))
        assertFalse(JointQualification.allowsLong(JointQualification.longFingerprint(), RecoveryThresholds(.5, .5)))
    }
    @Test fun sourceSearchThresholdAndEveryDictionaryAreBoundIndependently() {
        val f = JointQualification.fingerprint()
        for (changed in listOf(f.copy(searchVersion = f.searchVersion + 1), f.copy(rankerSha256 = "changed"),
            f.copy(policySha256 = "changed"), f.copy(contextSha256 = "changed"),
            f.copy(morphologySha256 = "changed"), f.copy(rareWordsSha256 = "changed"),
            f.copy(lexiconSha256 = "changed"), f.copy(thresholds = RecoveryThresholds(0.9, 0.9)))) {
            assertFalse(JointQualification.allows(changed))
        }
    }
}
