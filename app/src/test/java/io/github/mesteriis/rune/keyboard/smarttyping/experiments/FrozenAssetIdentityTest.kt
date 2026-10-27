package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.smarttyping.correction.ContextualQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.InfinitiveRevisionQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.NounCaseRevisionQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.security.MessageDigest

/** Source-tree identity checks; packaged APK and runtime readiness have separate gates. */
class FrozenAssetIdentityTest {
    private data class Asset(val name: String, val bytes: Long, val sha256: String)
    private data class Policy(val name: String, val modelSha256: String, val score: Double, val margin: Double)
    private val directory = File("src/main/assets/smarttyping/experiments")
    private val assets = listOf(
        Asset("ru-ranker.bin", FrozenExperimentAssets.RANK_BYTES.toLong(), FrozenExperimentAssets.RANK_SHA256),
        Asset("ru-ranker-auto-v1.bin", FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_BYTES.toLong(), FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_SHA256),
        Asset("ru-context.bin", FrozenExperimentAssets.CONTEXT_BYTES.toLong(), FrozenExperimentAssets.CONTEXT_SHA256),
        Asset("ru-ranking-context.bin", FrozenExperimentAssets.RANKING_CONTEXT_BYTES.toLong(), FrozenExperimentAssets.RANKING_CONTEXT_SHA256),
        Asset("ru-neighbor-ranker.bin", RecoveryQualification.RANKER_BYTES.toLong(), RecoveryQualification.RANKER_SHA256),
        Asset("ru-joint-ranker.bin", JointQualification.RANKER_BYTES.toLong(), JointQualification.RANKER_SHA256),
        Asset("ru-joint-rescue-ranker.bin", JointRescueQualification.RANKER_BYTES.toLong(), JointRescueQualification.RANKER_SHA256),
        // Rescue has a runtime hash pin but no size constant; freeze its observed size here.
        Asset("ru-joint-rescue-policy.json", 1314L, JointRescueQualification.POLICY_SHA256),
        Asset("ru-contextual-ranker.bin", FrozenContextualAssets.MODEL_BYTES.toLong(), FrozenContextualAssets.MODEL_SHA256),
        Asset("ru-contextual-policy.json", FrozenContextualAssets.POLICY_BYTES.toLong(), FrozenContextualAssets.POLICY_SHA256),
        Asset("ru-wiki.ctx", FrozenContextualAssets.WIKI_BYTES, FrozenContextualAssets.WIKI_SHA256),
        Asset("ru-conversation.ctx", FrozenContextualAssets.CONVERSATION_BYTES, FrozenContextualAssets.CONVERSATION_SHA256),
        Asset("ru-context.gram", FrozenContextualAssets.GRAMMAR_BYTES, FrozenContextualAssets.GRAMMAR_SHA256),
        Asset("ru-infinitive-revision-ranker.bin", FrozenInfinitiveRevisionAssets.MODEL_BYTES.toLong(), FrozenInfinitiveRevisionAssets.MODEL_SHA256),
        Asset("ru-infinitive-revision-policy.json", FrozenInfinitiveRevisionAssets.POLICY_BYTES.toLong(), FrozenInfinitiveRevisionAssets.POLICY_SHA256),
        Asset("ru-noun-case-ranker.bin", FrozenNounCaseAssets.MODEL_BYTES.toLong(), FrozenNounCaseAssets.MODEL_SHA256),
        Asset("ru-noun-case-policy.json", FrozenNounCaseAssets.POLICY_BYTES.toLong(), FrozenNounCaseAssets.POLICY_SHA256),
    )
    private val policies = listOf(
        Policy("ru-joint-rescue-policy.json", JointRescueQualification.RANKER_SHA256,
            JointRescueQualification.thresholds.minimumScore, JointRescueQualification.thresholds.minimumMargin),
        Policy("ru-contextual-policy.json", FrozenContextualAssets.MODEL_SHA256,
            ContextualQualification.MINIMUM_SCORE, ContextualQualification.MINIMUM_MARGIN),
        Policy("ru-infinitive-revision-policy.json", FrozenInfinitiveRevisionAssets.MODEL_SHA256,
            InfinitiveRevisionQualification.MINIMUM_SCORE, InfinitiveRevisionQualification.MINIMUM_MARGIN),
        Policy("ru-noun-case-policy.json", FrozenNounCaseAssets.MODEL_SHA256,
            NounCaseRevisionQualification.MINIMUM_SCORE, NounCaseRevisionQualification.MINIMUM_MARGIN),
    )

    @Test fun everyFrozenRuntimeAssetHasExactlyOnePinAndMatchesItsBytes() {
        inventory(directory, assets)
        assets.forEach { verify(File(directory, it.name), it) }
    }

    @Test fun everyFrozenPolicyMatchesItsRuntimeModelAndThresholds() {
        assertEquals(assets.filter { it.name.endsWith("-policy.json") }.map { it.name }.toSet(),
            policies.map { it.name }.toSet())
        policies.forEach { policy -> policyFields(File(directory, policy.name).readText(), policy) }
    }

    @Test fun currentFingerprintsStillMatchTheirIndependentAdmissionPins() {
        assertTrue("ru-neighbor-ranker.bin fingerprint", RecoveryQualification.allows(RecoveryQualification.fingerprint()))
        assertTrue("ru-joint-ranker.bin fingerprint", JointQualification.allows(JointQualification.fingerprint()))
        assertTrue("ru-joint-rescue-ranker.bin fingerprint", JointRescueQualification.allows(JointRescueQualification.fingerprint()))
        assertTrue("ru-contextual-ranker.bin fingerprint", ContextualQualification.allows(ContextualQualification.fingerprint()))
        assertTrue("ru-infinitive-revision-ranker.bin fingerprint", InfinitiveRevisionQualification.allows(InfinitiveRevisionQualification.fingerprint()))
        assertTrue("ru-noun-case-ranker.bin fingerprint", NounCaseRevisionQualification.allows(NounCaseRevisionQualification.fingerprint()))
    }

    @Test fun aChangedByteInATemporaryAssetIsRejectedWithItsName() {
        val pin = assets.single { it.name == "ru-neighbor-ranker.bin" }
        temporaryDirectory { root ->
            val bytes = File(directory, pin.name).readBytes()
            bytes[bytes.size / 2] = (bytes[bytes.size / 2].toInt() xor 1).toByte()
            val file = File(root, pin.name).apply { writeBytes(bytes) }
            rejected(pin.name) { verify(file, pin) }
        }
    }

    @Test fun changedHashOrSizeConstantsAreRejectedWithTheAssetName() {
        val pin = assets.single { it.name == "ru-neighbor-ranker.bin" }
        val file = File(directory, pin.name)
        rejected(pin.name) { verify(file, pin.copy(sha256 = "0".repeat(64))) }
        rejected(pin.name) { verify(file, pin.copy(bytes = pin.bytes + 1)) }
    }

    @Test fun orphanedAndMissingRuntimeAssetsAreRejected() {
        val pin = assets.first()
        temporaryDirectory { root ->
            File(root, pin.name).writeBytes(byteArrayOf(0))
            File(root, "orphan.bin").writeBytes(byteArrayOf(0))
            rejected("orphan.bin") { inventory(root, listOf(pin)) }
            File(root, "orphan.bin").delete()
            File(root, pin.name).delete()
            rejected(pin.name) { inventory(root, listOf(pin)) }
        }
    }

    @Test fun changingAnyPolicyModelOrThresholdConstantIsRejected() {
        policies.forEach { policy ->
            val json = File(directory, policy.name).readText()
            rejected(policy.name) { policyFields(json, policy.copy(modelSha256 = "0".repeat(64))) }
            rejected(policy.name) { policyFields(json, policy.copy(score = policy.score + .01)) }
            rejected(policy.name) { policyFields(json, policy.copy(margin = policy.margin + .01)) }
        }
    }

    @Test fun changingPolicyJsonFieldsIsRejectedIndependentlyOfItsFileHash() {
        policies.forEach { policy ->
            val json = File(directory, policy.name).readText()
            val score = Regex("(\"minimumScore\"\\s*:\\s*)[^,}\\r\\n]+")
                .replace(json) { it.groupValues[1] + (policy.score + .01) }
            rejected(policy.name) { policyFields(score, policy) }
            val margin = Regex("(\"minimumMargin\"\\s*:\\s*)[^,}\\r\\n]+")
                .replace(json) { it.groupValues[1] + (policy.margin + .01) }
            rejected(policy.name) { policyFields(margin, policy) }
            rejected(policy.name) { policyFields(json.replace(policy.modelSha256, "0".repeat(64)), policy) }
        }
    }

    @Test fun duplicatePolicyFieldsCannotMaskThresholdDrift() {
        policies.forEach { policy ->
            val json = File(directory, policy.name).readText().trimEnd().dropLast(1) +
                ",\"minimumScore\":0}"
            rejected(policy.name) { policyFields(json, policy) }
        }
    }

    private fun inventory(root: File, pins: List<Asset>) {
        assertTrue("Frozen asset directory: $root", root.isDirectory)
        assertEquals("Duplicate frozen asset pins", pins.size, pins.map { it.name }.toSet().size)
        val actual = root.listFiles()!!.filter { it.isFile &&
            (it.extension in setOf("bin", "ctx", "gram") || it.name.endsWith("-policy.json")) }
            .map { it.name }.toSet()
        assertEquals("Frozen runtime asset inventory", pins.map { it.name }.toSet(), actual)
    }

    private fun verify(file: File, pin: Asset) {
        assertTrue("${pin.name}: missing asset", file.isFile)
        assertEquals("${pin.name}: byte length", pin.bytes, file.length())
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        assertEquals("${pin.name}: SHA-256", pin.sha256,
            digest.digest().joinToString("") { "%02x".format(it) })
    }

    private fun policyFields(json: String, policy: Policy) {
        // Only three flat scalar fields are inspected; the complete policy bytes
        // are separately SHA-bound, so no general JSON dependency is needed here.
        fun scalar(field: String): String {
            val matches = Regex("\"${Regex.escape(field)}\"\\s*:\\s*([^,}\\r\\n]+)").findAll(json).toList()
            assertEquals("${policy.name}: $field occurrences", 1, matches.size)
            return matches.single().groupValues[1].trim()
        }
        fun number(field: String): Double {
            val value = scalar(field).toDoubleOrNull()
            assertTrue("${policy.name}: $field finite number", value != null && value.isFinite())
            return value!!
        }
        assertEquals("${policy.name}: modelSha256", "\"${policy.modelSha256}\"", scalar("modelSha256"))
        assertEquals("${policy.name}: minimumScore", policy.score, number("minimumScore"), 0.0)
        assertEquals("${policy.name}: minimumMargin", policy.margin, number("minimumMargin"), 0.0)
    }

    private fun rejected(asset: String, action: () -> Unit) {
        val failure = try { action(); null } catch (error: AssertionError) { error }
        assertNotNull("Expected rejection naming $asset", failure)
        assertTrue("Rejection must name $asset: ${failure!!.message}", failure.message.orEmpty().contains(asset))
    }

    private fun temporaryDirectory(action: (File) -> Unit) {
        val root = Files.createTempDirectory("rune-frozen-identity-").toFile()
        try { action(root) } finally { root.deleteRecursively() }
    }
}
