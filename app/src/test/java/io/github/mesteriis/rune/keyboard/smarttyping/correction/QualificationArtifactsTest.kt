package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test

class QualificationArtifactsTest {
    @Test fun `local policy rejects every changed manifest and policy version`() {
        val current = QualificationArtifacts.local()
        KeyboardLanguage.entries.forEach { language ->
            assertTrue(QualificationArtifacts.allowsLocal(language, current))
            assertFalse(QualificationArtifacts.allowsLocal(language, current.copy(policyVersion = 999)))
            assertFalse(QualificationArtifacts.allowsLocal(language, current.copy(
                lexicons = current.lexicons + (language to "0".repeat(64)))))
            assertFalse(SpellingQualification.CURRENT.allowsGeneralLocal(language))
        }
    }

    @Test fun `model rejects a change to any member of its complete fingerprint`() {
        val current = QualificationArtifacts.model()
        assertTrue(ModelRuntimeQualification.allows(current))
        listOf(current.copy(modelSha256 = "0".repeat(64)), current.copy(runtimeApi = 999),
            current.copy(runtimeBuildId = "other"), current.copy(spellingPolicyVersion = 999),
            current.copy(lexicons = emptyMap())).forEach { assertFalse(ModelRuntimeQualification.allows(it)) }
        KeyboardLanguage.entries.forEach { language ->
            assertFalse(ModelRuntimeQualification.allows(current.copy(
                lexicons = current.lexicons + (language to "0".repeat(64)))))
        }
    }
}
