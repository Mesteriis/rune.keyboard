package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.KeyboardDistance
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode

/** Trie-left/query-right unrestricted recurrence. UNIT matrix uses EDIT units; INITIAL uses quarters. */
internal class PrefixDistance {
    private val query = IntArray(32)
    private val last = IntArray(32)
    private val path = IntArray(32)
    private val lastByDepth = IntArray(33 * 32)
    private var pathLanguage: KeyboardLanguage? = null
    private val unit = IntArray(34 * 34)
    private val weighted = IntArray(34 * 34)
    var size = 0; private set
    var depth = 0; private set
    var unitMinimum = 0; private set
    var weightedMinimum = 0; private set
    var rows = 0L; private set
    var cells = 0L; private set
    val terminalUnit get() = unit[(depth + 1) * 34 + size + 1]
    val terminalWeighted get() = weighted[(depth + 1) * 34 + size + 1]

    fun begin(key: String) {
        check(TokenUnicode.bounded(key)) { "PREFIX_BOUNDS" }
        size = 0
        var offset = 0
        while (offset < key.length) {
            val cp = key.codePointAt(offset); query[size++] = cp; offset += Character.charCount(cp)
        }
        rows = 0; cells = 0; resetPath()
    }

    fun resetPath() {
        unit.fill(1024); weighted.fill(1024); last.fill(0); depth = 0
        path.fill(0); lastByDepth.fill(0); pathLanguage = null
        for (j in 0..size) { unit[34 + j + 1] = j; weighted[34 + j + 1] = j * 4 }
        unitMinimum = 0; weightedMinimum = 0
    }

    fun saveLast(target: IntArray) { last.copyInto(target) }
    fun restoreParent(parentDepth: Int, source: IntArray) { source.copyInto(last); depth = parentDepth }

    /** Reuse only equal scalar prefixes with the same adjacency language in this query. */
    fun restorePath(target: IntArray, targetDepth: Int, language: KeyboardLanguage,
        control: CandidateSearchControl): Boolean {
        if (!control.checkpoint()) return false
        check(targetDepth in 0..32 && target.size >= targetDepth) { "PREFIX_DEPTH" }
        var common = 0
        if (pathLanguage == language) {
            while (common < minOf(depth, targetDepth) && path[common] == target[common]) common++
        }
        lastByDepth.copyInto(last, 0, common * 32, (common + 1) * 32)
        depth = common
        // Rows at and above the common prefix are unchanged. Deeper stale rows are overwritten
        // before use; unrestricted transposition references only earlier rows and last occurrences.
        unitMinimum = common; weightedMinimum = common * 4
        for (j in 1..size) {
            unitMinimum = minOf(unitMinimum, unit[(common + 1) * 34 + j + 1])
            weightedMinimum = minOf(weightedMinimum, weighted[(common + 1) * 34 + j + 1])
        }
        for (i in common until targetDepth) if (!append(target[i], language, control)) return false
        return control.checkpoint()
    }

    fun append(cp: Int, language: KeyboardLanguage, control: CandidateSearchControl): Boolean {
        if (!control.checkpoint()) return false
        check(depth < 32) { "PREFIX_DEPTH" }
        check(depth == 0 || pathLanguage == language) { "PREFIX_LANGUAGE" }
        pathLanguage = language
        path[depth] = cp
        val row = ++depth
        val base = (row + 1) * 34
        unit[base] = 1024; weighted[base] = 1024
        unit[base + 1] = row; weighted[base + 1] = row * 4
        var match = 0
        unitMinimum = row; weightedMinimum = row * 4
        for (j in 1..size) {
            val priorRow = last[j - 1]; val priorColumn = match
            val same = cp == query[j - 1]
            if (same) match = j
            val substitution = if (same) 0 else if (KeyboardDistance.areAdjacent(cp, query[j - 1], language)) 3 else 4
            val u = minOf(minOf(unit[row * 34 + j] + if (same) 0 else 1, unit[base + j] + 1),
                minOf(unit[row * 34 + j + 1] + 1,
                    unit[priorRow * 34 + priorColumn] + row - priorRow + j - priorColumn - 1))
            val w = minOf(minOf(weighted[row * 34 + j] + substitution, weighted[base + j] + 4),
                minOf(weighted[row * 34 + j + 1] + 4,
                    weighted[priorRow * 34 + priorColumn] + (row - priorRow - 1) * 4 + 5 + (j - priorColumn - 1) * 4))
            unit[base + j + 1] = u; weighted[base + j + 1] = w
            unitMinimum = minOf(unitMinimum, u); weightedMinimum = minOf(weightedMinimum, w)
        }
        for (j in 0 until size) if (query[j] == cp) last[j] = row
        last.copyInto(lastByDepth, row * 32)
        rows += 2; cells += size * 2L
        return control.checkpoint()
    }

    fun clear() { query.fill(0); last.fill(0); path.fill(0); lastByDepth.fill(0); pathLanguage = null; unit.fill(0); weighted.fill(0); size = 0; depth = 0; rows = 0; cells = 0; unitMinimum = 0; weightedMinimum = 0 }
    fun isClear() = query.all { it == 0 } && last.all { it == 0 } && path.all { it == 0 } &&
        lastByDepth.all { it == 0 } && pathLanguage == null && unit.all { it == 0 } && weighted.all { it == 0 }
}
