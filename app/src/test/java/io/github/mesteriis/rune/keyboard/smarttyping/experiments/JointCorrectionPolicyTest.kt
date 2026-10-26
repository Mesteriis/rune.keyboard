package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class JointCorrectionPolicyTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val candidate = GeneratedCandidate("слово", "слово", "слово", ru, false, 2, 100,
        1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
    private fun generation(original: String = "сдово") = CandidateGeneration(original, listOf(candidate),
        CandidateCompletion.COMPLETE, false, null, 1, 1,
        jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(candidate), 1, 1), jointEvaluated = true)
    private fun model(context: Boolean = true) = ExperimentModels().apply {
        // Distance feature separates the original from all replacement candidates.
        val b = ByteBuffer.allocate(40).order(ByteOrder.LITTLE_ENDIAN)
        b.put("RET2".toByteArray()).putInt(95).putInt(1).putFloat(1f).putFloat(0f)
        b.putInt(1).putInt(0).putFloat(.1f).putFloat(-16f).putFloat(16f)
        loadJointRanker(b.array())
        if (context) loadContext(File("src/main/assets/smarttyping/experiments/ru-ranking-context.bin").readBytes())
    }
    private val open = RecoveryThresholds(-2.0, .01)
    private val closed = RecoveryThresholds(2.0, 2.0)

    @Test fun refusalSeparatesScoreMarginSearchAndResourcesWithoutChangingChoice() {
        val g = generation(); val model = model()
        assertEquals(JointCorrectionRefusal.SCORE_TOO_LOW,
            JointCorrectionPolicy.evaluate(model, "", g, ru, JointCorrectionThresholds(closed, closed)).refusal)
        val margin = RecoveryThresholds(-2.0, 3.0)
        assertEquals(JointCorrectionRefusal.INSUFFICIENT_MARGIN,
            JointCorrectionPolicy.evaluate(model, "", g, ru, JointCorrectionThresholds(margin, margin)).refusal)
        assertEquals(JointCorrectionRefusal.RESOURCE_UNAVAILABLE,
            JointCorrectionPolicy.evaluate(model(false), "", g, ru, JointCorrectionThresholds(open, open)).refusal)
        assertEquals(JointCorrectionRefusal.RESULT_NOT_READY,
            JointCorrectionPolicy.evaluate(model, "", g.copy(jointEvaluated = false), ru,
                JointCorrectionThresholds(open, open)).refusal)
        assertEquals(JointCorrectionRefusal.SEARCH_INCOMPLETE,
            JointCorrectionPolicy.evaluate(model, "", g.copy(jointSearch = LocalSearchEvidence.NONE), ru,
                JointCorrectionThresholds(open, open)).refusal)
    }

    @Test fun existingReplacementCanOnlyBeRetainedOrVetoed() {
        val model = model();val g = generation();val thresholds = JointCorrectionThresholds(open, open, open)
        assertEquals(candidate, JointCorrectionPolicy.select(model, "", g, ru, thresholds)?.candidate)
        assertEquals(candidate, JointCorrectionPolicy.select(model, "", g, ru, thresholds, "слово")?.candidate)
        assertNull(JointCorrectionPolicy.select(model, "", g, ru, thresholds, "снова")!!.candidate)
        assertNull(JointCorrectionPolicy.select(model, "", g, ru,
            JointCorrectionThresholds(open, open, closed), "слово"))
    }
    @Test fun shortAcquisitionLongAcquisitionAndRetentionHaveSeparateThresholds() {
        val model = model()
        assertEquals(candidate, JointCorrectionPolicy.select(model, "", generation("сдов"), ru,
            JointCorrectionThresholds(open, closed, closed))?.candidate)
        assertNull(JointCorrectionPolicy.select(model, "", generation(), ru,
            JointCorrectionThresholds(open, closed, open)))
        assertEquals(candidate, JointCorrectionPolicy.select(model, "", generation(), ru,
            JointCorrectionThresholds(open, closed, open), "слово")?.candidate)
    }
    @Test fun incompleteEvidenceValidOriginalUnsupportedLanguageOrMissingResourcesCannotDecide() {
        val thresholds = JointCorrectionThresholds(open, open)
        val model = model();val g = generation()
        assertNull(JointCorrectionPolicy.select(ExperimentModels(), "", g, ru, thresholds))
        assertNull(JointCorrectionPolicy.select(model(false), "", g, ru, thresholds))
        assertNull(JointCorrectionPolicy.select(model, "", g, KeyboardLanguage.ENGLISH, thresholds))
        assertNull(JointCorrectionPolicy.select(model, "", g.copy(isValidWord = true), ru, thresholds))
        assertNull(JointCorrectionPolicy.select(model, "", g.copy(jointSearch = LocalSearchEvidence.NONE), ru, thresholds))
    }
}
