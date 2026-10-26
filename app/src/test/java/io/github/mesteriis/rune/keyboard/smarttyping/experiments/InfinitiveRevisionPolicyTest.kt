package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingPersonalization
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.util.Properties
import org.junit.Assert.*
import org.junit.Test

class InfinitiveRevisionPolicyTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val original = "научищься"
    private fun candidate(word: String) = GeneratedCandidate(word, word, word, ru, false, 0, 100,
        1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
    private val finite = candidate("научишься")
    private val infinitive = candidate("научиться")
    private val baseline = JointCorrectionEvaluation(JointCorrectionChoice(finite, contextual = true))
    private val morphology = MorphologyLexicon { _, key ->
        if (key == original) MorphologyMembership.ABSENT else MorphologyMembership(true, true, 100)
    }
    private fun generation() = CandidateGeneration(original, listOf(finite, infinitive), CandidateCompletion.COMPLETE,
        false, null, 1, 2, jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE,
            listOf(finite, infinitive), 1, 2), jointEvaluated = true)
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream("context-feature-parity/$name")!!.use { it.readBytes() }
    private fun models(other: Float = 0f, inf: Float = 4f) = ExperimentModels().apply {
        loadContext(File("src/main/assets/smarttyping/experiments/ru-ranking-context.bin").readBytes())
        val h = Properties().apply { resource("hashes.properties").inputStream().use(::load) }
        val bytes = ByteBuffer.allocate(40).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RET2".toByteArray()).putInt(146).putInt(1).putFloat(1f).putFloat(0f)
            putInt(1).putInt(114).putFloat(.5f).putFloat(other).putFloat(inf)
        }.array()
        loadContextualRanker(ContextualRanker.create(bytes,
            WordPairFeatures.open(ByteBuffer.wrap(resource("wiki.bin")), h.getProperty("wiki"))!!,
            WordPairFeatures.open(ByteBuffer.wrap(resource("conversation.bin")), h.getProperty("conversation"))!!,
            GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("grammar.bin")), h.getProperty("grammar"))!!)!!)
        loadGrammarRevisionRanker(bytes)
    }
    private fun evaluate(model: ExperimentModels = models(), previous: JointCorrectionEvaluation = baseline,
        context: String = "тебе надо ", gen: CandidateGeneration = generation(), lexicon: MorphologyLexicon = morphology,
        refusal: AutomaticAdmissionRefusal? = null, legacy: String? = null) =
        InfinitiveRevisionPolicy.evaluate(model, context, gen, ru, previous, legacy, lexicon) { refusal }

    @Test fun learnedRevisionUsesTheExistingPoolAndIndependentSourceAdmission() {
        val result = evaluate()
        assertEquals(infinitive, result.choice!!.candidate)
        assertTrue(result.choice.grammarRevision)
        assertFalse(result.choice.contextual)
        assertTrue(result.grammarRevisionAttempted)
        val refused = evaluate(refusal = AutomaticAdmissionRefusal.WINNER_AMBIGUOUS)
        assertEquals(baseline.choice, refused.choice)
        assertEquals(AutomaticAdmissionRefusal.WINNER_AMBIGUOUS, refused.grammarRevisionAdmissionRefusal)
        assertFalse(object : TypingPersonalization {}.grammarRevisionAutomaticDecision(generation(), infinitive, ru).allowed)
    }

    @Test fun originalAndExplicitOldVetoAreNeverTurnedIntoNewAcquisition() {
        val veto = JointCorrectionEvaluation(JointCorrectionChoice(null))
        assertEquals(veto.choice, evaluate(previous = veto, legacy = finite.text).choice)
        assertEquals(JointCorrectionRefusal.ORIGINAL_PREFERRED, evaluate(previous = veto).grammarRevisionRefusal)
        assertEquals(infinitive, evaluate(previous = JointCorrectionEvaluation(), legacy = finite.text).choice!!.candidate)
    }

    @Test fun protectedKnownAndUnavailableOriginalEvidenceKeepTheBaseline() {
        assertEquals(JointCorrectionRefusal.ORIGINAL_VALID, evaluate(gen = generation().copy(isValidWord = true)).grammarRevisionRefusal)
        assertEquals(JointCorrectionRefusal.PROTECTED_FORM, evaluate(gen = generation().copy(protectedReason = ProtectedTokenReason.MIXED_SCRIPT)).grammarRevisionRefusal)
        assertEquals(JointCorrectionRefusal.ORIGINAL_VALID,
            evaluate(lexicon = MorphologyLexicon { _, _ -> MorphologyMembership(true, true, 100) }).grammarRevisionRefusal)
        val unavailable = evaluate(lexicon = MorphologyLexicon.UNAVAILABLE)
        assertEquals(baseline.choice, unavailable.choice)
        assertEquals(AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE, unavailable.grammarRevisionAdmissionRefusal)
    }

    @Test fun absentOrIncompleteResourcesAndPoolsDoNotSuppressTheInstalledReplacement() {
        for ((result, reason) in listOf(
            evaluate(model = ExperimentModels()) to JointCorrectionRefusal.RESOURCE_UNAVAILABLE,
            evaluate(gen = generation().copy(jointEvaluated = false)) to JointCorrectionRefusal.RESULT_NOT_READY,
            evaluate(gen = generation().copy(jointSearch = LocalSearchEvidence.NONE)) to JointCorrectionRefusal.SEARCH_INCOMPLETE,
        )) {
            assertEquals(baseline.choice, result.choice)
            assertEquals(reason, result.grammarRevisionRefusal)
        }
    }

    @Test fun inappropriateContextAndWeakScoresRetainTheInstalledResult() {
        for ((result, reason) in listOf(
            evaluate(context = "ты ") to JointCorrectionRefusal.NO_INFINITIVE_CUE,
            evaluate(model = models(inf = 1f)) to JointCorrectionRefusal.SCORE_TOO_LOW,
            evaluate(model = models(other = 4f)) to JointCorrectionRefusal.INSUFFICIENT_MARGIN,
        )) {
            assertEquals(baseline.choice, result.choice)
            assertEquals(reason, result.grammarRevisionRefusal)
        }
    }

    @Test fun fingerprintsBindBothModelsScopeFeatureResourcesAndThresholds() {
        val f = InfinitiveRevisionQualification.fingerprint()
        assertTrue(InfinitiveRevisionQualification.allows(f))
        val drift = listOf(f.copy(version = 2), f.copy(scope = 2), f.copy(features = 95),
            f.copy(model = ""), f.copy(policy = ""), f.copy(referenceModel = ""), f.copy(referencePolicy = ""),
            f.copy(wiki = ""), f.copy(conversation = ""), f.copy(grammar = ""), f.copy(morphology = ""),
            f.copy(minimumScore = f.minimumScore + .01), f.copy(minimumMargin = 0.0))
        for (value in drift) assertFalse(InfinitiveRevisionQualification.allows(value))
        assertFalse(InfinitiveRevisionQualification.enabled(KeyboardLanguage.ENGLISH, 9))
        assertFalse(InfinitiveRevisionQualification.enabled(ru, 2))
    }

    @Test fun packagedWeightsAndPolicyMatchTheirFrozenIdentities() {
        for ((name, count, hash) in listOf(
            Triple("ru-infinitive-revision-ranker.bin", FrozenInfinitiveRevisionAssets.MODEL_BYTES, FrozenInfinitiveRevisionAssets.MODEL_SHA256),
            Triple("ru-infinitive-revision-policy.json", FrozenInfinitiveRevisionAssets.POLICY_BYTES, FrozenInfinitiveRevisionAssets.POLICY_SHA256),
        )) {
            val bytes = File("src/main/assets/smarttyping/experiments/$name").readBytes()
            assertEquals(count, bytes.size)
            assertEquals(hash, MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) })
        }
    }
}
