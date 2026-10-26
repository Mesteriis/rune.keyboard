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
        fun checkpoint(): Boolean {
            if (Thread.currentThread().isInterrupted || cancellation.isCancelled()) {
                completion = CandidateCompletion.CANCELLED
            } else if (nanoTime() - started !in 0 until MAX_NANOS) {
                completion = CandidateCompletion.STATES_EXHAUSTED
            }
            return completion == CandidateCompletion.COMPLETE
        }
        fun cost(position: Int, letter: Char): Int = when {
            position !in key.indices -> INF
            key[position] == letter -> 0
            KeyboardDistance.areAdjacent(key[position].code, letter.code, KeyboardLanguage.RUSSIAN) -> 1
            else -> INF
        }
        try {
            var depth = 0
            next[0] = index.child(0)
            while (depth >= 0 && checkpoint()) {
                val node = next[depth]
                if (node == 0) { depth--; continue }
                if (states == maximumStates) { completion = CandidateCompletion.STATES_EXHAUSTED; break }
                states++
                next[depth] = index.sibling(node)
                if (index.minLength(node) > key.length + 1 || index.maxLength(node) < key.length - 1) continue
                val letter = index.label(node).toChar()
                path[depth] = letter
                val length = depth + 1
                plain[length] = plain[depth] + cost(depth, letter)
                inserted[length] = minOf(inserted[depth] + cost(depth - 1, letter), plain[depth] + 1)
                deleted[length] = minOf(deleted[depth] + cost(depth + 1, letter), plain[length] + 1)
                transposed[length] = transposed[depth] + cost(depth, letter)
                if (depth > 0 && depth < key.length && path[depth - 1] == key[depth] && letter == key[depth - 1]) {
                    transposed[length] = minOf(transposed[length], plain[depth - 1] + 1)
                }
                // The first half of a transposition may mismatch a non-neighbour. Do not prune it.
                val pendingTranspose = if (length < key.length && letter == key[length]) plain[depth] + 1 else INF
                if (minOf(plain[length], inserted[length], deleted[length], transposed[length], pendingTranspose) > radius) continue
                val terminal = index.terminal(node)
                val distance = when (length - key.length) {
                    0 -> minOf(plain[length], transposed[length])
                    1 -> inserted[length]
                    -1 -> deleted[length]
                    else -> INF
                }
                if (terminal != 0 && distance in 2..radius) {
                    if (!checkpoint()) break
                    if (candidates.size == maximumTerminals) { completion = CandidateCompletion.VERIFIED_EXHAUSTED; break }
                    val word = String(path, 0, length)
                    val display = pattern.preserve(word) ?: continue
                    candidates.add(GeneratedCandidate(display, TokenUnicode.folded(display), word,
                        KeyboardLanguage.RUSSIAN, false, 0, index.rank(terminal), distance,
                        WeightedDamerauLevenshtein().features(key, word, KeyboardLanguage.RUSSIAN),
                        kotlin.math.abs(length - key.length), pattern))
                }
                if (length < 32 && index.child(node) != 0) {
                    depth++
                    next[depth] = index.child(node)
                }
            }
            checkpoint()
        } catch (_: Exception) {
            completion = CandidateCompletion.READER_FAILURE
            checkpoint()
        } finally {
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
    }
}
