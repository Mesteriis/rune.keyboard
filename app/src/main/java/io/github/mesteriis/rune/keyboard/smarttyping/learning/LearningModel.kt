package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale

enum class FeedbackSource { ACCEPTED, CONFIRMED, MANUAL_RETYPE, REJECTED }
enum class TypoPattern { INSERTION, DELETION, SUBSTITUTION, TRANSPOSITION, REPETITION }

data class LearningEvidence(
    val language: KeyboardLanguage, val originalHash: String, val expectedHash: String,
    val source: FeedbackSource, val pattern: TypoPattern?, val holdout: Boolean,
    val trains: Boolean, val original: String? = null, val expected: String? = null,
    val conflicted: Boolean = false,
) {
    override fun toString() = "LearningEvidence(redacted)"
}
data class LearningSnapshot(val evidence: List<LearningEvidence> = emptyList()) {
    val examples get() = evidence.filter { it.original != null }
    /** Contradictory originals and all explicit vetoes abstain, including previously learned evidence. */
    fun counts(): Map<Pair<KeyboardLanguage, TypoPattern>, Int> {
        val safe = evidence.groupBy { it.language to it.originalHash }.values.filter { rows ->
            rows.none { it.source == FeedbackSource.REJECTED || it.conflicted } && rows.map { it.expectedHash }.distinct().size == 1
        }.flatten().filter { it.trains && !it.holdout && it.pattern != null }
        return safe.groupBy { it.language to it.pattern!! }.mapValues { (_, rows) ->
            rows.map { it.expectedHash }.distinct().size.coerceAtMost(LearningModel.MAX_EVIDENCE)
        }
    }
}

/** Explicit feedback only. The bridge must configure current editor eligibility before every event. */
class LearningModel {
    private var collect = false
    private var learn = false
    private var eligible = false
    private val evidence = ArrayList<LearningEvidence>()
    fun configure(collectExamples: Boolean, learnPatterns: Boolean, eligible: Boolean) {
        collect = collectExamples; learn = learnPatterns; this.eligible = eligible
    }
    fun record(original: String, expected: String, language: KeyboardLanguage, source: FeedbackSource,
        dictionaryContains: (String, KeyboardLanguage) -> Boolean = { _, _ -> false }): Boolean {
        if (!eligible || (!collect && !learn)) return false
        val from = normalize(original) ?: return false
        val to = normalize(expected) ?: return false
        val pattern = classify(from, to)
        if (source == FeedbackSource.MANUAL_RETYPE) {
            if (pattern == null) return false
            val valid = try { dictionaryContains(to, language) } catch (_: Exception) { false }
            if (!valid) return false
        }
        if (source == FeedbackSource.CONFIRMED && from != to) return false
        val fromHash = digest(language.name + ":" + from)
        val toHash = digest(language.name + ":" + to)
        val rejected = source == FeedbackSource.REJECTED
        if (evidence.any { it.language == language && it.originalHash == fromHash && it.expectedHash == toHash &&
                (it.source == FeedbackSource.REJECTED) == rejected }) return false
        if (evidence.size == MAX_EVIDENCE) {
            // Capacity must never prevent a new contradiction/veto from retracting old learning.
            var changed = false
            evidence.indices.forEach { index ->
                val row = evidence[index]
                if (row.language == language && row.originalHash == fromHash && !row.conflicted &&
                    (rejected || row.expectedHash != toHash)) {
                    evidence[index] = row.copy(conflicted = true, trains = false)
                    changed = true
                }
            }
            return changed
        }
        val holdout = holdout(language, to)
        evidence += LearningEvidence(language, fromHash, toHash, source, pattern, holdout,
            learn && !holdout && !rejected, if (collect) from else null, if (collect) to else null)
        return true
    }
    fun preference(original: String, candidate: String, language: KeyboardLanguage): Double =
        if (!eligible || !learn) 0.0 else preference(snapshot(), original, candidate, language)
    fun snapshot() = LearningSnapshot(evidence.toList())
    fun restore(snapshot: LearningSnapshot) { evidence.clear(); evidence.addAll(snapshot.evidence) }
    fun reset() { evidence.clear() }
    companion object {
        const val MAX_EVIDENCE = 512
        const val MIN_EVIDENCE = 3
        const val MAX_BONUS = 0.15
        fun normalize(word: String): String? {
            if (word.length > 96 || word.codePointCount(0, word.length) !in 1..48 || !word.codePoints().allMatch { Character.isLetter(it) }) return null
            val value = Normalizer.normalize(word, Normalizer.Form.NFC).lowercase(Locale.ROOT)
            return value.takeIf { it.codePointCount(0, it.length) in 1..48 && it.codePoints().allMatch { point -> Character.isLetter(point) } }
        }
        internal fun digest(value: String) = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
        fun holdout(language: KeyboardLanguage, expected: String): Boolean =
            digest(language.name + ":" + checkNotNull(normalize(expected))).take(8).toLong(16) % 5L == 0L
        fun preference(snapshot: LearningSnapshot, original: String, candidate: String, language: KeyboardLanguage): Double {
            val from = normalize(original) ?: return 0.0
            val to = normalize(candidate) ?: return 0.0
            val pattern = classify(from, to) ?: return 0.0
            val count = snapshot.counts()[language to pattern] ?: 0
            return if (count < MIN_EVIDENCE) 0.0 else (count * 0.025).coerceAtMost(MAX_BONUS)
        }
        /** Exactly one unambiguous edit. Multiple deletion positions in a run form one repetition. */
        fun classify(original: String, expected: String): TypoPattern? {
            val a = original.codePoints().toArray().toList(); val b = expected.codePoints().toArray().toList()
            if (a.size !in 1..48 || b.size !in 1..48 || a == b) return null
            if (a.size == b.size) {
                val diff = a.indices.filter { a[it] != b[it] }
                if (diff.size == 1) return TypoPattern.SUBSTITUTION
                if (diff.size == 2 && diff[1] == diff[0] + 1 && a[diff[0]] == b[diff[1]] && a[diff[1]] == b[diff[0]]) return TypoPattern.TRANSPOSITION
                return null
            }
            if (kotlin.math.abs(a.size - b.size) != 1) return null
            val larger = if (a.size > b.size) a else b
            val smaller = if (a.size > b.size) b else a
            val positions = larger.indices.filter { index -> larger.filterIndexed { i, _ -> i != index } == smaller }
            if (positions.isEmpty()) return null
            if (positions.size > 1) return if (positions.zipWithNext().all { (x, y) -> y == x + 1 && larger[x] == larger[y] }) TypoPattern.REPETITION else null
            return if (a.size < b.size) TypoPattern.INSERTION else TypoPattern.DELETION
        }
    }
}
