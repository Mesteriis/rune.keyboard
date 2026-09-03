package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditCostProfile
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein

/** Global covering frontier. Worker-confined fixed scratch, cleared after every selection. */
internal class PackedTopSeven(private val lookup: (KeyboardLanguage) -> PackedLexiconData?) {
    private val indices = arrayOfNulls<PackedLexiconData>(KeyboardLanguage.entries.size)
    private val parent = IntArray(CAPACITY)
    private val codepoint = IntArray(CAPACITY)
    private val depth = IntArray(CAPACITY)
    private val language = IntArray(CAPACITY)
    private val child = IntArray(CAPACITY)
    private val unitLower = IntArray(CAPACITY)
    private val weightedLower = IntArray(CAPACITY)
    private val frontier = IntArray(CAPACITY)
    private val path = IntArray(32)
    private val restore = IntArray(32)
    private val pending = IntArray(64)
    private val seen = IntArray(64)
    private val selected = IntArray(CandidateGenerator.MAX_ALTERNATIVES)
    private val candidates = arrayOfNulls<GeneratedCandidate>(64)
    private val prefix = PrefixDistance()
    private val unitVerifier = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
    private val weightedVerifier = WeightedDamerauLevenshtein()
    private var used = 0
    private var frontierSize = 0
    private var pendingSize = 0
    private var candidateCount = 0
    private var seenCount = 0
    private var selectedCount = 0
    private var fallbackCount = 0
    private var primaryPrior = 0
    private var fallbackPrior = 0

    fun select(key: String, route: LanguageRoute, pattern: CasePattern,
        control: CandidateSearchControl, maximumAlternatives: Int = CandidateGenerator.MAX_ALTERNATIVES): TopCandidateSelection {
        require(maximumAlternatives in 1..CandidateGenerator.MAX_ALTERNATIVES) { "CANDIDATE_WIDTH" }
        val primary = route.primary?.ordinal ?: return TopCandidateSelection(CandidateCompletion.UNAVAILABLE, maximumAlternatives = maximumAlternatives)
        val size = key.codePointCount(0, key.length)
        val radius = if (size < 5) 1 else 2
        val quota = route.fallbackCandidateLimit
        fun finish(status: CandidateCompletion, proof: TopCandidateProof = TopCandidateProof.NONE,
            alternatives: List<GeneratedCandidate> = emptyList()) = TopCandidateSelection(status, alternatives, proof, maximumAlternatives)
        fun stopped(): TopCandidateSelection {
            if (!control.cancellationCheckpoint()) return finish(CandidateCompletion.CANCELLED)
            val status = control.stop ?: CandidateCompletion.UNAVAILABLE
            if (status != CandidateCompletion.STATES_EXHAUSTED && status != CandidateCompletion.VERIFIED_EXHAUSTED) return finish(status)
            val partial = selectSubset((0 until candidateCount).map { candidates[it]!! }, quota, control, maximumAlternatives)
            return if (!control.cancellationCheckpoint()) finish(CandidateCompletion.CANCELLED) else finish(status, alternatives = partial)
        }
        try {
            primaryPrior = route.primaryPrior
            fallbackPrior = route.fallbackPrior
            // Snapshot immutable mappings for this selection only; no query survives the finally.
            for (lang in listOfNotNull(route.primary, route.fallback)) {
                if (!control.checkpoint()) return stopped()
                indices[lang.ordinal] = lookup(lang) ?: return finish(CandidateCompletion.UNAVAILABLE)
            }
            prefix.begin(key)
            for (lang in listOfNotNull(route.primary, route.fallback)) {
                val root = allocate(-1, 0, 0, lang.ordinal, indices[lang.ordinal]!!.child(0), 0, 0)
                if (child[root] != 0) pushFrontier(root, primary)
            }
            while (true) {
                if (!control.checkpoint()) return stopped()
                if (pendingSize != 0 && (frontierSize == 0 || precedesBound(candidates[pending[0]]!!,
                        weightedLower[frontier[0]], prior(frontier[0], primary)))) {
                    val id = popPending(); val candidate = candidates[id]!!
                    if (!control.cancellationCheckpoint()) return finish(CandidateCompletion.CANCELLED)
                    var duplicate = false
                    for (i in 0 until seenCount) if (candidates[seen[i]]!!.canonicalKey == candidate.canonicalKey) { duplicate = true; break }
                    if (!duplicate) {
                        seen[seenCount++] = id // including displays skipped by fallback quota
                        if (!candidate.isFallback || fallbackCount < quota) {
                            selected[selectedCount++] = id
                            if (candidate.isFallback) fallbackCount++
                        }
                    }
                    if (selectedCount == maximumAlternatives) {
                        if (!control.cancellationCheckpoint()) return finish(CandidateCompletion.CANCELLED)
                        return finish(CandidateCompletion.COMPLETE, TopCandidateProof.REQUESTED_IN_GLOBAL_ORDER,
                            (0 until selectedCount).map { candidates[selected[it]]!! })
                    }
                    continue
                }
                if (frontierSize == 0) {
                    check(pendingSize == 0) { "PENDING_COVERAGE" }
                    if (!control.cancellationCheckpoint()) return finish(CandidateCompletion.CANCELLED)
                    return finish(CandidateCompletion.COMPLETE, TopCandidateProof.FRONTIER_EXHAUSTED,
                        (0 until selectedCount).map { candidates[selected[it]]!! })
                }
                val region = popFrontier(primary)
                val lang = KeyboardLanguage.entries[language[region]]
                val index = indices[lang.ordinal]!!
                val parentDepth = depth[region]
                var ancestor = region
                while (depth[ancestor] > 0) { path[depth[ancestor] - 1] = codepoint[ancestor]; ancestor = parent[ancestor] }
                if (!prefix.restorePath(path, parentDepth, lang, control)) return stopped()
                prefix.saveLast(restore)
                var node = child[region]
                // This popped region remains logically active until its ENTIRE child list is expanded.
                // No certificate is evaluated inside this loop, including after a terminal is found.
                while (node != 0) {
                    if (!control.inspectState()) return stopped()
                    if (!control.checkpoint()) return stopped()
                    val sibling = index.sibling(node)
                    val gap = maxOf(0, index.minLength(node) - size, size - index.maxLength(node))
                    if (maxOf(unitLower[region], gap) <= radius) {
                        val cp = index.label(node)
                        path[parentDepth] = cp
                        prefix.restoreParent(parentDepth, restore)
                        if (!prefix.append(cp, lang, control)) return stopped()
                        val u = maxOf(unitLower[region], gap, prefix.unitMinimum)
                        val w = maxOf(weightedLower[region], prefix.weightedMinimum, 3 * u, 4 * gap)
                        if (u <= radius) {
                            val ordinal = index.terminal(node)
                            val descendants = index.child(node)
                            val slot = allocate(region, cp, parentDepth + 1, lang.ordinal, descendants, u, w)
                            if (ordinal != 0 && prefix.terminalUnit in 1..radius) {
                                if (!control.verifyTerminal()) return stopped()
                                if (!control.checkpoint()) return stopped()
                                val terminal = String(path, 0, parentDepth + 1)
                                val rank = index.rank(ordinal)
                                check(rank > 0 && terminal != key && TokenUnicode.folded(terminal) == terminal) { "TERMINAL_IDENTITY" }
                                val distance = unitVerifier.features(key, terminal, lang).editCost.toInt()
                                if (!control.checkpoint()) return stopped()
                                val features = weightedVerifier.features(key, terminal, lang)
                                check(distance in 1..radius && distance == prefix.terminalUnit &&
                                    (features.editCost * 4).toInt() == prefix.terminalWeighted) { "TERMINAL_RECURRENCE" }
                                if (!control.checkpoint()) return stopped()
                                val display = pattern.preserve(terminal)
                                if (display != null) {
                                    val displayKey = TokenUnicode.folded(display)
                                    if (displayKey != key) {
                                        val candidate = GeneratedCandidate(display, displayKey, terminal, lang, lang.ordinal != primary,
                                            if (lang.ordinal == primary) route.primaryPrior else route.fallbackPrior,
                                            rank, distance, features, kotlin.math.abs(size - parentDepth - 1), pattern)
                                        val id = candidateCount++; candidates[id] = candidate; pushPending(id)
                                    }
                                }
                            }
                            if (descendants != 0) pushFrontier(slot, primary)
                        }
                    }
                    node = sibling
                }
            }
        } finally { clear() }
    }

    private fun allocate(p: Int, cp: Int, d: Int, lang: Int, children: Int, u: Int, w: Int): Int {
        check(used < CAPACITY) { "SCRATCH_EXHAUSTED" }
        val id = used++
        parent[id] = p; codepoint[id] = cp; depth[id] = d; language[id] = lang
        child[id] = children; unitLower[id] = u; weightedLower[id] = w
        return id
    }
    private fun prior(id: Int, primary: Int) = if (language[id] == primary) primaryPrior else fallbackPrior
    private fun frontierLess(a: Int, b: Int, primary: Int): Boolean {
        if (weightedLower[a] != weightedLower[b]) return weightedLower[a] < weightedLower[b]
        if (prior(a, primary) != prior(b, primary)) return prior(a, primary) > prior(b, primary)
        if (language[a] != language[b]) return language[a] < language[b]
        return a < b // queue scheduling only, never a certificate tie-break
    }
    private fun pushFrontier(id: Int, primary: Int) {
        check(frontierSize < CAPACITY) { "FRONTIER_EXHAUSTED" }
        var pos = frontierSize++
        while (pos > 0) { val p = (pos - 1) / 2; if (!frontierLess(id, frontier[p], primary)) break; frontier[pos] = frontier[p]; pos = p }
        frontier[pos] = id
    }
    private fun popFrontier(primary: Int): Int {
        val answer = frontier[0]; val last = frontier[--frontierSize]; var pos = 0
        while (pos * 2 + 1 < frontierSize) {
            var c = pos * 2 + 1
            if (c + 1 < frontierSize && frontierLess(frontier[c + 1], frontier[c], primary)) c++
            if (!frontierLess(frontier[c], last, primary)) break
            frontier[pos] = frontier[c]; pos = c
        }
        if (frontierSize > 0) frontier[pos] = last
        return answer
    }
    private fun pushPending(id: Int) {
        check(pendingSize < 64) { "PENDING_LIMIT" }; var pos = pendingSize++
        while (pos > 0) { val p = (pos - 1) / 2; if (COMPARATOR.compare(candidates[id]!!, candidates[pending[p]]!!) >= 0) break; pending[pos] = pending[p]; pos = p }
        pending[pos] = id
    }
    private fun popPending(): Int {
        val answer = pending[0]; val last = pending[--pendingSize]; var pos = 0
        while (pos * 2 + 1 < pendingSize) {
            var c = pos * 2 + 1
            if (c + 1 < pendingSize && COMPARATOR.compare(candidates[pending[c + 1]]!!, candidates[pending[c]]!!) < 0) c++
            if (COMPARATOR.compare(candidates[pending[c]]!!, candidates[last]!!) >= 0) break
            pending[pos] = pending[c]; pos = c
        }
        if (pendingSize > 0) pending[pos] = last
        return answer
    }
    private fun clear() {
        parent.fill(0); codepoint.fill(0); depth.fill(0); language.fill(0); child.fill(0)
        unitLower.fill(0); weightedLower.fill(0); frontier.fill(0); path.fill(0); restore.fill(0)
        pending.fill(0); seen.fill(0); selected.fill(0); candidates.fill(null); prefix.clear(); indices.fill(null)
        used = 0; frontierSize = 0; pendingSize = 0; candidateCount = 0; seenCount = 0; selectedCount = 0
        fallbackCount = 0; primaryPrior = 0; fallbackPrior = 0
    }
    fun isClear(): Boolean = listOf(parent, codepoint, depth, language, child, unitLower, weightedLower,
        frontier, path, restore, pending, seen, selected).all { array -> array.all { it == 0 } } &&
        candidates.all { it == null } && indices.all { it == null } && prefix.isClear()

    companion object {
        const val CAPACITY = CandidateSearchControl.MAX_STATES + 2
        private val COMPARATOR = CandidateGenerator.COMPARATOR
        private fun quarters(c: GeneratedCandidate) = (c.editFeatures.editCost * 4).toInt()
        // Frequency and lexical bounds are deliberately bottom: equal cost/prior cannot certify.
        internal fun precedesBound(candidate: GeneratedCandidate, weighted: Int, prior: Int): Boolean =
            quarters(candidate) < weighted || (quarters(candidate) == weighted && candidate.languagePrior > prior)
        fun selectSubset(all: List<GeneratedCandidate>, quota: Int, control: CandidateSearchControl, maximumAlternatives: Int): List<GeneratedCandidate> {
            val seen = HashSet<String>(); val result = ArrayList<GeneratedCandidate>(maximumAlternatives); var fallbacks = 0
            for (candidate in all.sortedWith(COMPARATOR)) {
                if (!control.cancellationCheckpoint()) return emptyList()
                if (!seen.add(candidate.canonicalKey)) continue
                if (candidate.isFallback && fallbacks == quota) continue
                result.add(candidate); if (candidate.isFallback) fallbacks++
                if (result.size == maximumAlternatives) break
            }
            return result
        }
    }
}
