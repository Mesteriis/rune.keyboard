package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern

/** Static diagnostic, without query text or a query-bearing exception cause. */
class PackedReaderException internal constructor() : Exception("PACKED_READER_FAILURE")

/** Worker-confined scratch over immutable handles; exhaustive scan and separately certified global top-N. */
class PackedCandidateLexicon(handles: Collection<PackedLexiconData>) : CandidateLexicon {
    private val indices = arrayOfNulls<PackedLexiconData>(KeyboardLanguage.entries.size)
    private val query = IntArray(32)
    private val path = IntArray(32)
    private val last = IntArray(32)
    private val savedLast = IntArray(33 * 32)
    private val distance = IntArray(34 * 34)
    private val next = IntArray(33)
    private val lower = IntArray(33)
    private val topSeven by lazy(LazyThreadSafetyMode.NONE) { PackedTopSeven(::handle) }

    internal fun handle(language: KeyboardLanguage): PackedLexiconData? = indices[language.ordinal]

    override fun selectTop(key: String, route: LanguageRoute, pattern: CasePattern,
        control: CandidateSearchControl, maximumAlternatives: Int): TopCandidateSelection = topSeven.select(key, route, pattern, control, maximumAlternatives)

    init {
        require(handles.size <= indices.size) { "PACKED_HANDLE_COUNT" }
        for (handle in handles) {
            require(indices[handle.language.ordinal] == null) { "PACKED_DUPLICATE_LANGUAGE" }
            indices[handle.language.ordinal] = handle
        }
    }

    override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
        try {
            if (!control.checkpoint()) return ExactMembership.UNAVAILABLE
            val index = indices[language.ordinal] ?: return ExactMembership.UNAVAILABLE
            val size = prepareQuery(key)
            if (size == 0) return ExactMembership.UNAVAILABLE
            var parent = 0
            for (i in 0 until size) {
                var node = index.child(parent)
                var found = 0
                while (node != 0) {
                    if (!control.inspectState()) return ExactMembership.UNAVAILABLE
                    val label = index.label(node)
                    if (label == query[i]) {
                        found = node
                        break
                    }
                    if (label > query[i]) break
                    node = index.sibling(node)
                }
                if (found == 0) return if (control.checkpoint()) ExactMembership.ABSENT else ExactMembership.UNAVAILABLE
                parent = found
            }
            if (!control.checkpoint()) return ExactMembership.UNAVAILABLE
            return if (index.terminal(parent) != 0) ExactMembership.PRESENT else ExactMembership.ABSENT
        } catch (_: InterruptedException) {
            Thread.currentThread().interrupt()
            throw InterruptedException("PACKED_READER_INTERRUPTED")
        } catch (_: Exception) {
            throw PackedReaderException()
        } finally {
            clearScratch()
        }
    }

    override fun scan(
        language: KeyboardLanguage,
        key: String,
        unitRadius: Int,
        control: CandidateSearchControl,
        visitor: CandidateVisitor,
    ): LexiconScanStatus {
        try {
            if (!control.checkpoint() || unitRadius !in 1..2) return LexiconScanStatus.UNAVAILABLE
            val index = indices[language.ordinal] ?: return LexiconScanStatus.UNAVAILABLE
            val size = prepareQuery(key)
            if (size == 0) return LexiconScanStatus.UNAVAILABLE
            distance.fill(INFINITY)
            for (j in 0..size) distance[STRIDE + j + 1] = j
            var depth = 0
            next[0] = index.child(0)
            while (depth >= 0) {
                if (!control.checkpoint()) return LexiconScanStatus.UNAVAILABLE
                val node = next[depth]
                if (node == 0) {
                    depth--
                    if (depth >= 0) for (j in 0 until size) last[j] = savedLast[depth * 32 + j]
                    continue
                }
                // Charge before touching this child, even if its length or DP bound prunes it.
                if (!control.inspectState()) return LexiconScanStatus.UNAVAILABLE
                next[depth] = index.sibling(node)
                val lengthLow = maxOf(0, index.minLength(node) - size, size - index.maxLength(node))
                if (maxOf(lower[depth], lengthLow) > unitRadius) continue
                val cp = index.label(node)
                path[depth] = cp
                val row = depth + 1
                if (!control.checkpoint()) return LexiconScanStatus.UNAVAILABLE
                val rowLow = evaluateRow(cp, row, size)
                val bound = maxOf(lower[depth], lengthLow, rowLow)
                if (bound > unitRadius) continue
                val terminal = index.terminal(node)
                if (terminal != 0 && distance[(row + 1) * STRIDE + size + 1] in 1..unitRadius) {
                    // Generator owns verification charging. False visitor / shared stop ends retrieval.
                    if (!visitor.visit(String(path, 0, row), index.rank(terminal))) return LexiconScanStatus.UNAVAILABLE
                    if (!control.checkpoint()) return LexiconScanStatus.UNAVAILABLE
                }
                val child = index.child(node)
                if (child != 0) {
                    for (j in 0 until size) {
                        savedLast[depth * 32 + j] = last[j]
                        if (query[j] == cp) last[j] = row
                    }
                    depth++
                    next[depth] = child
                    lower[depth] = bound
                }
            }
            return if (control.checkpoint()) LexiconScanStatus.COMPLETE else LexiconScanStatus.UNAVAILABLE
        } catch (_: InterruptedException) {
            Thread.currentThread().interrupt()
            throw InterruptedException("PACKED_READER_INTERRUPTED")
        } catch (_: Exception) {
            // Keep cancellation precedence in CandidateGenerator while never exposing visitor payloads.
            throw PackedReaderException()
        } finally {
            clearScratch()
        }
    }

    private fun prepareQuery(key: String): Int {
        if (key.isEmpty() || !TokenUnicode.bounded(key)) return 0
        val canonical = try { TokenUnicode.folded(key) == key } catch (_: IllegalArgumentException) { false }
        if (!canonical) return 0
        var offset = 0
        var size = 0
        while (offset < key.length) {
            val cp = key.codePointAt(offset)
            query[size++] = cp
            offset += Character.charCount(cp)
        }
        return size
    }

    /** Unit unrestricted last-occurrence DL. Parent rows remain in the fixed depth matrix. */
    private fun evaluateRow(cp: Int, row: Int, size: Int): Int {
        val base = (row + 1) * STRIDE
        distance[base] = INFINITY
        distance[base + 1] = row
        var lastMatch = 0
        var minimum = row
        for (j in 1..size) {
            val priorRow = last[j - 1]
            val priorColumn = lastMatch
            val cost = if (cp == query[j - 1]) { lastMatch = j; 0 } else 1
            val value = minOf(
                minOf(distance[row * STRIDE + j] + cost, distance[base + j] + 1),
                minOf(distance[row * STRIDE + j + 1] + 1,
                    distance[priorRow * STRIDE + priorColumn] + row - priorRow + j - priorColumn - 1),
            )
            distance[base + j + 1] = value
            minimum = minOf(minimum, value)
        }
        return minimum
    }

    private fun clearScratch() {
        query.fill(0)
        path.fill(0)
        last.fill(0)
        savedLast.fill(0)
        distance.fill(0)
        next.fill(0)
        lower.fill(0)
    }

    companion object {
        private const val STRIDE = 34
        private const val INFINITY = 1_024
        const val PRIMITIVE_SCRATCH_BYTES = (32 * 3 + 33 * 32 + 34 * 34 + 33 * 2) * 4
    }
}
