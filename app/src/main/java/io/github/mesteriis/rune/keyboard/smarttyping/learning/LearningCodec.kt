package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.InputStream

/** Strict bounded binary codec. Digests are dedup identifiers, not encryption of words. */
object LearningCodec {
    // 512 maximum raw rows: 8 + 512 * (148 + 2 * (2 + 48 * 6)) = 372,744.
    // Modified UTF encodes supplementary letters as two three-byte surrogate units.
    const val MAX_BYTES = 512 * 1024
    fun readBounded(input: InputStream): ByteArray {
        val out = ByteArrayOutputStream()
        val buffer = ByteArray(4096)
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            require(out.size() + read <= MAX_BYTES) { "LEARNING_SIZE" }
            out.write(buffer, 0, read)
        }
        return out.toByteArray()
    }
    fun encode(snapshot: LearningSnapshot): ByteArray {
        validate(snapshot)
        val bytes = ByteArrayOutputStream()
        DataOutputStream(bytes).use { out ->
            out.writeInt(MAGIC_V2); out.writeInt(snapshot.evidence.size)
            snapshot.evidence.forEach { e ->
                out.writeInt(e.language.ordinal); out.writeUTF(e.originalHash); out.writeUTF(e.expectedHash)
                out.writeInt(e.source.ordinal); out.writeInt(e.pattern?.ordinal ?: -1)
                out.writeBoolean(e.holdout); out.writeBoolean(e.trains); out.writeBoolean(e.conflicted); out.writeBoolean(e.original != null)
                if (e.original != null) { out.writeUTF(e.original); out.writeUTF(checkNotNull(e.expected)) }
            }
            writePolicy(out, snapshot.activePolicy)
            out.writeBoolean(snapshot.rollbackPolicy != null)
            snapshot.rollbackPolicy?.let { writePolicy(out, it) }
        }
        return bytes.toByteArray().also { require(it.size <= MAX_BYTES) }
    }
    fun decode(bytes: ByteArray): LearningSnapshot {
        require(bytes.size <= MAX_BYTES)
        return DataInputStream(ByteArrayInputStream(bytes)).use { input ->
            val magic = input.readInt(); require(magic == MAGIC_V1 || magic == MAGIC_V2)
            val size = input.readInt(); require(size in 0..LearningModel.MAX_EVIDENCE)
            val rows = List(size) {
                val language = KeyboardLanguage.entries.getOrNull(input.readInt()) ?: error("LEARNING_LANGUAGE")
                val fromHash = input.readUTF(); val toHash = input.readUTF()
                val source = FeedbackSource.entries.getOrNull(input.readInt()) ?: error("LEARNING_SOURCE")
                val patternIndex = input.readInt(); require(patternIndex in -1 until TypoPattern.entries.size)
                val pattern = TypoPattern.entries.getOrNull(patternIndex)
                fun flag(): Boolean { val value = input.readUnsignedByte(); require(value in 0..1); return value == 1 }
                val holdout = flag(); val trains = flag(); val conflicted = flag(); val raw = flag()
                LearningEvidence(language, fromHash, toHash, source, pattern, holdout, trains,
                    if (raw) input.readUTF() else null, if (raw) input.readUTF() else null, conflicted)
            }
            val snapshot = if (magic == MAGIC_V1) {
                val legacy = LearningSnapshot(rows)
                legacy.copy(activePolicy = legacy.candidatePolicy())
            } else {
                val active = readPolicy(input)
                val hasRollback = input.readUnsignedByte().also { require(it in 0..1) } == 1
                LearningSnapshot(rows, active, if (hasRollback) readPolicy(input) else null)
            }
            require(input.read() == -1)
            snapshot.also(::validate)
        }
    }

    private fun writePolicy(out: DataOutputStream, policy: LearningPatternPolicy) {
        val entries = policy.counts.entries.sortedWith(compareBy({ it.key.first.ordinal }, { it.key.second.ordinal }))
        out.writeInt(entries.size)
        entries.forEach { (key, count) ->
            out.writeInt(key.first.ordinal); out.writeInt(key.second.ordinal); out.writeInt(count)
        }
    }

    private fun readPolicy(input: DataInputStream): LearningPatternPolicy {
        val size = input.readInt(); require(size in 0..MAX_POLICY_ENTRIES)
        val counts = LinkedHashMap<Pair<KeyboardLanguage, TypoPattern>, Int>()
        repeat(size) {
            val language = KeyboardLanguage.entries.getOrNull(input.readInt()) ?: error("LEARNING_POLICY_LANGUAGE")
            val pattern = TypoPattern.entries.getOrNull(input.readInt()) ?: error("LEARNING_POLICY_PATTERN")
            val count = input.readInt(); require(count in 1..LearningModel.MAX_EVIDENCE)
            require(counts.put(language to pattern, count) == null)
        }
        return LearningPatternPolicy(counts)
    }

    private fun validate(snapshot: LearningSnapshot) {
        require(snapshot.evidence.size <= LearningModel.MAX_EVIDENCE)
        val keys = HashSet<String>()
        snapshot.evidence.forEach { e ->
            require(e.originalHash.matches(Regex("[0-9a-f]{64}")) && e.expectedHash.matches(Regex("[0-9a-f]{64}")))
            require(e.holdout == (e.expectedHash.take(8).toLong(16) % 5L == 0L))
            require(!e.trains || (!e.holdout && !e.conflicted && e.source != FeedbackSource.REJECTED))
            require((e.original == null) == (e.expected == null))
            require(keys.add("${e.language}:${e.originalHash}:${e.expectedHash}:${e.source == FeedbackSource.REJECTED}"))
            if (e.source == FeedbackSource.CONFIRMED) require(e.originalHash == e.expectedHash && e.pattern == null)
            if (e.source == FeedbackSource.MANUAL_RETYPE) require(e.pattern != null)
            if (e.original != null) {
                val expected = checkNotNull(e.expected)
                require(LearningModel.normalize(e.original) == e.original && LearningModel.normalize(expected) == expected)
                require(LearningModel.digest(e.language.name + ":" + e.original) == e.originalHash)
                require(LearningModel.digest(e.language.name + ":" + expected) == e.expectedHash)
                require(LearningModel.classify(e.original, expected) == e.pattern)
            }
        }
        validatePolicy(snapshot.activePolicy)
        snapshot.rollbackPolicy?.let(::validatePolicy)
    }

    private fun validatePolicy(policy: LearningPatternPolicy) {
        require(policy.counts.size <= MAX_POLICY_ENTRIES)
        require(policy.counts.values.all { it in 1..LearningModel.MAX_EVIDENCE })
    }

    private const val MAGIC_V1 = 0x524c4231
    private const val MAGIC_V2 = 0x524c4232
    private val MAX_POLICY_ENTRIES = KeyboardLanguage.entries.size * TypoPattern.entries.size
}
