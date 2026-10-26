package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Properties
import org.junit.Assert.*
import org.junit.Test

class ContextualCorrectionPolicyTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val candidate = GeneratedCandidate("слово", "слово", "слово", ru, false, 0, 100,
        1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
    private fun generation() = CandidateGeneration("сдово", listOf(candidate), CandidateCompletion.COMPLETE,
        false, null, 1, 1, jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE,
            listOf(candidate), 1, 1), jointEvaluated = true)
    private fun resource(name: String) = javaClass.classLoader!!
        .getResourceAsStream("context-feature-parity/$name")!!.use { it.readBytes() }
    private fun models(left: Float = -16f, right: Float = 16f) = ExperimentModels().apply {
        loadContext(File("src/main/assets/smarttyping/experiments/ru-ranking-context.bin").readBytes())
        val h = Properties().apply { resource("hashes.properties").inputStream().use(::load) }
        val bytes = ByteBuffer.allocate(40).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RET2".toByteArray()).putInt(146).putInt(1).putFloat(1f).putFloat(0f)
            putInt(1).putInt(0).putFloat(.1f).putFloat(left).putFloat(right)
        }.array()
        loadContextualRanker(ContextualRanker.create(bytes,
            WordPairFeatures.open(ByteBuffer.wrap(resource("wiki.bin")), h.getProperty("wiki"))!!,
            WordPairFeatures.open(ByteBuffer.wrap(resource("conversation.bin")), h.getProperty("conversation"))!!,
            GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("grammar.bin")), h.getProperty("grammar"))!!)!!)
    }
    private fun evaluate(model: ExperimentModels, baseline: JointCorrectionEvaluation, legacy: String? = null,
        generation: CandidateGeneration = generation(), admission: AutomaticAdmissionRefusal? = null) =
        ContextualCorrectionPolicy.evaluate(model, "", generation, ru, baseline, legacy) { admission }

    @Test fun acquisitionUsesOnlyTheCompletePoolAndExternalAdmission() {
        val baseline = JointCorrectionEvaluation(JointCorrectionChoice(null))
        val result = evaluate(models(), baseline)
        assertEquals(candidate, result.choice!!.candidate)
        assertTrue(result.choice.contextual)
        assertTrue(result.contextualAttempted)
        val vetoed = evaluate(models(), baseline, admission = AutomaticAdmissionRefusal.ORIGINAL_VALID)
        assertEquals(baseline.choice, vetoed.choice)
        assertEquals(AutomaticAdmissionRefusal.ORIGINAL_VALID, vetoed.contextualAdmissionRefusal)
        assertEquals(JointCorrectionRefusal.RESULT_NOT_READY,
            evaluate(models(), baseline, generation = generation().copy(jointEvaluated = false)).contextualRefusal)
        assertEquals(JointCorrectionRefusal.SEARCH_INCOMPLETE,
            evaluate(models(), baseline, generation = generation().copy(jointSearch = LocalSearchEvidence.NONE)).contextualRefusal)
        assertEquals(JointCorrectionRefusal.ORIGINAL_VALID,
            evaluate(models(), baseline, generation = generation().copy(isValidWord = true)).contextualRefusal)
    }

    @Test fun existingReplacementIsRetainedOrVetoedNeverChangedToAnotherWord() {
        val baseline = JointCorrectionEvaluation(JointCorrectionChoice(candidate))
        val retained = evaluate(models(), baseline)
        assertEquals(baseline.choice, retained.choice)
        assertFalse(retained.choice!!.contextual)
        val different = evaluate(models(), JointCorrectionEvaluation(), "снова")
        assertTrue(different.choice!!.contextual)
        assertNull(different.choice.candidate)
        assertEquals(JointCorrectionRefusal.REPLACEMENT_VETOED, different.contextualRefusal)
        val original = evaluate(models(16f, -16f), baseline)
        assertNull(original.choice!!.candidate)
        assertEquals(JointCorrectionRefusal.ORIGINAL_PREFERRED, original.contextualRefusal)
        // An explicit old veto means original is the baseline even if a raw legacy proposal exists.
        assertEquals(candidate, evaluate(models(), JointCorrectionEvaluation(JointCorrectionChoice(null)), "снова").choice!!.candidate)
    }

    @Test fun lowScoreMarginAndMissingResourcesLeaveBaselineUnchanged() {
        val baseline = JointCorrectionEvaluation(JointCorrectionChoice(candidate))
        for ((model, reason) in listOf(models(-16f, -16f) to JointCorrectionRefusal.SCORE_TOO_LOW,
                models(0f, 0f) to JointCorrectionRefusal.INSUFFICIENT_MARGIN,
                ExperimentModels() to JointCorrectionRefusal.RESOURCE_UNAVAILABLE)) {
            val result = evaluate(model, baseline)
            assertEquals(baseline.choice, result.choice)
            assertEquals(reason, result.contextualRefusal)
        }
    }

    @Test fun qualificationBindsPolicyModelFeatureInputsAndSource() {
        val f = ContextualQualification.fingerprint()
        assertTrue(ContextualQualification.allows(f))
        assertFalse(ContextualQualification.allows(f.copy(minimumMargin = f.minimumMargin + 0.001)))
        assertFalse(ContextualQualification.allows(f.copy(grammar = "0".repeat(64))))
        assertFalse(ContextualQualification.allows(f.copy(model = "0".repeat(64))))
        assertFalse(ContextualQualification.allows(f.copy(features = 108)))
        assertFalse(ContextualQualification.enabled(KeyboardLanguage.ENGLISH, 5))
        assertFalse(ContextualQualification.enabled(ru, 2))
    }
}
