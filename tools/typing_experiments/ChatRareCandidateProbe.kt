package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedRareWordLexicon
import java.io.File
import java.nio.ByteBuffer
import java.security.MessageDigest

/** Host-only inspection of an isolated post-hoc candidate; never changes qualification. */
object ChatRareCandidateProbe {
    @JvmStatic fun main(args: Array<String>) {
        require(args.size == 5)
        val baseBytes = File(args[0]).readBytes()
        val candidateBytes = File(args[1]).readBytes()
        val expected = args[4]
        fun hash(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
        check(hash(candidateBytes) == expected)
        val original = PackedRareWordLexicon.validate(ByteBuffer.wrap(baseBytes), hash(baseBytes))
        val candidate = PackedRareWordLexicon.validate(ByteBuffer.wrap(candidateBytes), expected)
        val words = File(args[2]).readLines()
        val candidateWords = File(args[3]).readLines()
        check(words.size == 288246 && candidateWords.size == words.size + 7)
        val oldSet = words.toHashSet()
        val added = candidateWords.filter { it !in oldSet }
        check(added.size == 7)
        for (word in words) {
            val old = original.lookup(word); val updated = candidate.lookup(word)
            check(old.available && old.present && updated.available && updated.present && old.rank == updated.rank)
        }
        for ((index, word) in added.withIndex()) {
            val old = original.lookup(word)
            check(old.available && !old.present)
            val updated = candidate.lookup(word)
            check(updated.available && updated.present && updated.rank == words.size + index + 1)
        }
        val corrupted = candidateBytes.copyOf(); corrupted[corrupted.lastIndex] = (corrupted.last().toInt() xor 1).toByte()
        check(!PackedRareWordLexicon.validate(ByteBuffer.wrap(corrupted), expected).lookup("слово").available)
        val compact = QualificationArtifacts.compactPublic()
        check(QualificationArtifacts.allowsCompactPublic(KeyboardLanguage.RUSSIAN, compact))
        check(!QualificationArtifacts.allowsCompactPublic(KeyboardLanguage.RUSSIAN, compact.copy(rareWordsSha256 = expected)))
        val joint = JointQualification.fingerprint()
        check(JointQualification.allows(joint) && !JointQualification.allows(joint.copy(rareWordsSha256 = expected)))
        val jointLong = JointQualification.longFingerprint()
        check(JointQualification.allowsLong(jointLong, JointQualification.thresholds.retention) &&
            !JointQualification.allowsLong(jointLong.copy(rareWordsSha256 = expected), JointQualification.thresholds.retention))
        val rescue = JointRescueQualification.fingerprint()
        check(JointRescueQualification.allows(rescue) && !JointRescueQualification.allows(rescue.copy(rareWordsSha256 = expected)))
        val context = WordContextQualification.fingerprint()
        check(WordContextQualification.allows(context) && !WordContextQualification.allows(context.copy(rareWordsSha256 = expected)))
        val recovery = RecoveryQualification.fingerprint()
        check(RecoveryQualification.allows(recovery) && !RecoveryQualification.allows(recovery.copy(rareWordsSha256 = expected)))
        println("{\"originalWordsChecked\":${words.size},\"addedWordsChecked\":${added.size},\"oldRanksPreserved\":true,\"corruptRefused\":true,\"changedFingerprintRefusals\":6}")
    }
}
