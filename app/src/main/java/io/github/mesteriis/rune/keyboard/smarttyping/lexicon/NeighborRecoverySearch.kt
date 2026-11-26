package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.KeyboardDistance
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein

/** Independent RU retrieval certificate. No baseline radius, budget or ranking is changed. */
internal class NeighborRecoverySearch(
    private val handle: () -> PackedLexiconData?,
    private val nanoTime: () -> Long = System::nanoTime,
    private val maximumStates: Int = MAX_STATES,
    private val maximumTerminals: Int = MAX_TERMINALS,
) {
    fun search(token: String, cancellation: CandidateCancellation): LocalSearchEvidence {
        if (ProtectedTokenPolicy.isProtected(token)) return LocalSearchEvidence.NONE
        val pattern = CasePattern.analyze(token)
        val key = TokenUnicode.folded(token)
        if (pattern !in listOf(CasePattern.LOWER, CasePattern.TITLE) || key.length !in 5..32 ||
            key.any { it !in 'а'..'я' && it != 'ё' }) return LocalSearchEvidence.NONE
        val index = handle() ?: return LocalSearchEvidence.NONE
        val radius = if (key.length >= 7) 3 else 2
        val started = nanoTime()
        val path = CharArray(32)
        // Offset input positions by one and use an unreachable row outside the query.
        val alignmentCosts = Array(path.size + 2) { position ->
            key.getOrNull(position - 1)?.let { SUBSTITUTION_COSTS[it - 'а'] } ?: UNREACHABLE
        }
        val next = IntArray(33)
        // Each depth has four alignments: substitutions only, one output insertion,
        // one input deletion, or one exact adjacent transposition. Fixed O(word length) scratch.
        val plain = IntArray(33) { INF }
        val inserted = IntArray(33) { INF }
        val deleted = IntArray(33) { INF }
        val transposed = IntArray(33) { INF }
        plain[0] = 0
        deleted[0] = 1
        var states = 0
        val candidates = ArrayList<GeneratedCandidate>()
        var completion = CandidateCompletion.COMPLETE
        val searchThread = Thread.currentThread()
        fun checkpoint(checkTime: Boolean = true): Boolean {
            if (searchThread.isInterrupted || cancellation.isCancelled()) {
                completion = CandidateCompletion.CANCELLED
            } else if (checkTime && nanoTime() - started !in 0 until MAX_NANOS) {
                completion = CandidateCompletion.STATES_EXHAUSTED
            }
            return completion == CandidateCompletion.COMPLETE
        }
        try {
            var depth = 0
            next[0] = index.child(0)
            // Sample time during traversal and always before verifying a terminal or returning.
            // Cancellation remains per edge. No complete certificate can cross the deadline.
            while (depth >= 0 && checkpoint(checkTime = states % TIME_CHECK_INTERVAL == 0)) {
                val node = next[depth]
                if (node == 0) { depth--; continue }
                if (states == maximumStates) { completion = CandidateCompletion.STATES_EXHAUSTED; break }
                states++
                next[depth] = index.sibling(node)
                if (index.minLength(node) > key.length + 1 || index.maxLength(node) < key.length - 1) continue
                val letter = index.label(node).toChar()
                path[depth] = letter
                val length = depth + 1
                val column = (letter - 'а').let { if (it in 0 until ALPHABET_SIZE) it else ALPHABET_SIZE }
                val substitution = alignmentCosts[length][column]
                plain[length] = plain[depth] + substitution
                inserted[length] = minOf(inserted[depth] + alignmentCosts[depth][column], plain[depth] + 1)
                deleted[length] = minOf(deleted[depth] + alignmentCosts[length + 1][column], plain[length] + 1)
                transposed[length] = transposed[depth] + substitution
                if (depth > 0 && depth < key.length && path[depth - 1] == key[depth] && letter == key[depth - 1]) {
                    transposed[length] = minOf(transposed[length], plain[depth - 1] + 1)
                }
                // The first half of a transposition may mismatch a non-neighbour. Do not prune it.
                val pendingTranspose = if (length < key.length && letter == key[length]) plain[depth] + 1 else INF
                if (plain[length] > radius && inserted[length] > radius && deleted[length] > radius &&
                    transposed[length] > radius && pendingTranspose > radius) continue
                val distance = when (length - key.length) {
                    0 -> minOf(plain[length], transposed[length])
                    1 -> inserted[length]
                    -1 -> deleted[length]
                    else -> INF
                }
                val terminal = if (distance in 2..radius) index.terminal(node) else 0
                if (terminal != 0) {
                    if (!checkpoint()) break
                    if (candidates.size == maximumTerminals) { completion = CandidateCompletion.VERIFIED_EXHAUSTED; break }
                    val word = String(path, 0, length)
                    val display = pattern.preserve(word) ?: continue
                    candidates.add(GeneratedCandidate(display, TokenUnicode.folded(display), word,
                        KeyboardLanguage.RUSSIAN, false, 0, index.rank(terminal), distance,
                        WeightedDamerauLevenshtein().features(key, word, KeyboardLanguage.RUSSIAN),
                        kotlin.math.abs(length - key.length), pattern))
                }
                val child = if (length < 32) index.child(node) else 0
                if (child != 0) {
                    depth++
                    next[depth] = child
                }
            }
            checkpoint()
        } catch (_: Exception) {
            completion = CandidateCompletion.READER_FAILURE
            checkpoint()
        } finally {
            alignmentCosts.fill(UNREACHABLE)
            path.fill('\u0000'); next.fill(0); plain.fill(0)
            inserted.fill(0); deleted.fill(0); transposed.fill(0)
        }
        return LocalSearchEvidence(completion,
            if (completion == CandidateCompletion.CANCELLED) emptyList() else candidates.sortedWith(
                compareBy<GeneratedCandidate> { it.unitDistance }.thenBy { it.frequencyRank }.thenBy { it.terminalKey }),
            states, candidates.size)
    }

    companion object {
        const val VERSION = 1
        const val MAX_STATES = 32_768
        const val MAX_TERMINALS = 64
        const val MAX_NANOS = 100_000_000L
        private const val INF = 128
        private const val TIME_CHECK_INTERVAL = 32
        private const val ALPHABET_SIZE = 'ё' - 'а' + 1
        private val UNREACHABLE = IntArray(ALPHABET_SIZE + 1) { INF }
        private val SUBSTITUTION_COSTS = Array(ALPHABET_SIZE) { source ->
            IntArray(ALPHABET_SIZE + 1) { target ->
                when {
                    source == target -> 0
                    target == ALPHABET_SIZE -> INF
                    KeyboardDistance.areAdjacent('а'.code + source, 'а'.code + target, KeyboardLanguage.RUSSIAN) -> 1
                    else -> INF
                }
            }
        }
    }
}
