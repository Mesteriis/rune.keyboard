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

class NounCaseRevisionPolicyTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val original = "фотографие"
    private fun candidate(word: String) = GeneratedCandidate(word, word, word, ru, false, 0, 100,
        1, EditFeatures(1.0, 0, 0.0), 0, CasePattern.LOWER)
    private val instrumental = candidate("фотографией")
    private val accusative = candidate("фотографию")
    private val baseline = JointCorrectionEvaluation(JointCorrectionChoice(instrumental, contextual = true))
    private val morphology = MorphologyLexicon { _, key ->
        if (key == original) MorphologyMembership.ABSENT else MorphologyMembership(true, true, 100)
    }
    private fun generation() = CandidateGeneration(original, listOf(instrumental, accusative), CandidateCompletion.COMPLETE,
        false, null, 1, 2, jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE,
            listOf(instrumental, accusative), 1, 2), jointEvaluated = true)
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream("context-feature-parity/$name")!!.use { it.readBytes() }
    private fun models(other: Float = 0f, acc: Float = 6f) = ExperimentModels().apply {
        loadContext(File("src/main/assets/smarttyping/experiments/ru-ranking-context.bin").readBytes())
        val h = Properties().apply { resource("hashes.properties").inputStream().use(::load) }
        val bytes = ByteBuffer.allocate(40).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RET2".toByteArray()).putInt(146).putInt(1).putFloat(1f).putFloat(0f)
            putInt(1).putInt(124).putFloat(.5f).putFloat(other).putFloat(acc)
        }.array()
        loadContextualRanker(ContextualRanker.create(bytes,
            WordPairFeatures.open(ByteBuffer.wrap(resource("wiki.bin")), h.getProperty("wiki"))!!,
            WordPairFeatures.open(ByteBuffer.wrap(resource("conversation.bin")), h.getProperty("conversation"))!!,
            GrammarFeatureDictionary.open(ByteBuffer.wrap(resource("grammar.bin")), h.getProperty("grammar"))!!)!!)
        loadNounCaseRanker(bytes)
    }
    private fun evaluate(model: ExperimentModels = models(), previous: JointCorrectionEvaluation = baseline,
        context: String = "том показал мне ", gen: CandidateGeneration = generation(), lexicon: MorphologyLexicon = morphology,
        refusal: AutomaticAdmissionRefusal? = null, legacy: String? = null) =
        NounCaseRevisionPolicy.evaluate(model, context, gen, ru, previous, legacy, lexicon) { refusal }

    @Test fun learnedRevisionUsesTheExistingPoolAndIndependentSourceAdmission() {
        val result = evaluate()
        assertEquals(accusative, result.choice!!.candidate)
        assertTrue(result.choice.nounCaseRevision)
        assertFalse(result.choice.contextual)
        assertTrue(result.nounCaseAttempted)
        val refused = evaluate(refusal = AutomaticAdmissionRefusal.WINNER_AMBIGUOUS)
        assertEquals(baseline.choice, refused.choice)
        assertEquals(AutomaticAdmissionRefusal.WINNER_AMBIGUOUS, refused.nounCaseAdmissionRefusal)
        assertFalse(object : TypingPersonalization {}.nounCaseAutomaticDecision(generation(), accusative, ru).allowed)
    }

    @Test fun originalAndExplicitOldVetoAreNeverTurnedIntoNewAcquisition() {
        val veto = JointCorrectionEvaluation(JointCorrectionChoice(null))
        assertEquals(veto.choice, evaluate(previous = veto, legacy = instrumental.text).choice)
        assertEquals(JointCorrectionRefusal.ORIGINAL_PREFERRED, evaluate(previous = veto).nounCaseRefusal)
        assertEquals(accusative, evaluate(previous = JointCorrectionEvaluation(), legacy = instrumental.text).choice!!.candidate)
    }

    @Test fun protectedKnownAndUnavailableOriginalEvidenceKeepTheBaseline() {
        assertEquals(JointCorrectionRefusal.ORIGINAL_VALID, evaluate(gen = generation().copy(isValidWord = true)).nounCaseRefusal)
        assertEquals(JointCorrectionRefusal.PROTECTED_FORM, evaluate(gen = generation().copy(protectedReason = ProtectedTokenReason.MIXED_SCRIPT)).nounCaseRefusal)
        assertEquals(JointCorrectionRefusal.ORIGINAL_VALID,
            evaluate(lexicon = MorphologyLexicon { _, _ -> MorphologyMembership(true, true, 100) }).nounCaseRefusal)
        val unavailable = evaluate(lexicon = MorphologyLexicon.UNAVAILABLE)
        assertEquals(baseline.choice, unavailable.choice)
        assertEquals(AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE, unavailable.nounCaseAdmissionRefusal)
    }

    @Test fun absentOrIncompleteResourcesAndPoolsDoNotSuppressTheInstalledReplacement() {
        for ((result, reason) in listOf(
            evaluate(model = ExperimentModels()) to JointCorrectionRefusal.RESOURCE_UNAVAILABLE,
            evaluate(gen = generation().copy(jointEvaluated = false)) to JointCorrectionRefusal.RESULT_NOT_READY,
            evaluate(gen = generation().copy(jointSearch = LocalSearchEvidence.NONE)) to JointCorrectionRefusal.SEARCH_INCOMPLETE,
        )) {
            assertEquals(baseline.choice, result.choice)
            assertEquals(reason, result.nounCaseRefusal)
        }
    }

    @Test fun inappropriateContextAndWeakScoresRetainTheInstalledResult() {
        for ((result, reason) in listOf(
            evaluate(context = "он ") to JointCorrectionRefusal.NO_ACCUSATIVE_CUE,
            evaluate(model = models(acc = 1f)) to JointCorrectionRefusal.SCORE_TOO_LOW,
            evaluate(model = models(other = 6f)) to JointCorrectionRefusal.INSUFFICIENT_MARGIN,
        )) {
            assertEquals(baseline.choice, result.choice)
            assertEquals(reason, result.nounCaseRefusal)
        }
    }

    @Test fun aHighScoreCannotBorrowAnOldWordOutsideTheCertifiedPoolOrAnotherLanguage() {
        val missingPrevious = generation().copy(jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE,
            listOf(accusative), 1, 1))
        val unsupported = generation().copy(jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE,
            listOf(instrumental, accusative.copy(language = KeyboardLanguage.ENGLISH)), 1, 2))
        val distant = generation().copy(jointSearch = LocalSearchEvidence(CandidateCompletion.COMPLETE,
            listOf(instrumental, accusative.copy(unitDistance = 4)), 1, 2))
        for (gen in listOf(missingPrevious, unsupported, distant)) {
            val result = evaluate(gen = gen)
            assertEquals(baseline.choice, result.choice)
            assertEquals(JointCorrectionRefusal.NOT_QUALIFIED, result.nounCaseRefusal)
        }
    }

    @Test fun fingerprintsBindBothModelsScopeFeatureResourcesAndThresholds() {
        val f = NounCaseRevisionQualification.fingerprint()
        assertTrue(NounCaseRevisionQualification.allows(f))
        val drift = listOf(f.copy(version = 2), f.copy(scope = 2), f.copy(features = 95),
            f.copy(model = ""), f.copy(policy = ""), f.copy(referenceModel = ""), f.copy(referencePolicy = ""),
            f.copy(referenceInfinitiveModel = ""), f.copy(referenceInfinitivePolicy = ""), f.copy(character = ""), f.copy(wiki = ""), f.copy(conversation = ""), f.copy(grammar = ""), f.copy(morphology = ""),
            f.copy(minimumScore = f.minimumScore + .01), f.copy(minimumMargin = 0.0))
        for (value in drift) assertFalse(NounCaseRevisionQualification.allows(value))
        assertFalse(NounCaseRevisionQualification.enabled(KeyboardLanguage.ENGLISH, 9))
        assertFalse(NounCaseRevisionQualification.enabled(ru, 2))
    }

    @Test fun packagedWeightsAndPolicyMatchTheirFrozenIdentities() {
        for ((name, count, hash) in listOf(
            Triple("ru-noun-case-ranker.bin", FrozenNounCaseAssets.MODEL_BYTES, FrozenNounCaseAssets.MODEL_SHA256),
            Triple("ru-noun-case-policy.json", FrozenNounCaseAssets.POLICY_BYTES, FrozenNounCaseAssets.POLICY_SHA256),
        )) {
            val bytes = File("src/main/assets/smarttyping/experiments/$name").readBytes()
            assertEquals(count, bytes.size)
            assertEquals(hash, MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) })
        }
    }
}
