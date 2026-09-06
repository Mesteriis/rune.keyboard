package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

/** A requested-width certificate is separate from exhaustive [LexiconScanStatus.COMPLETE]. */
enum class TopCandidateProof { NONE, REQUESTED_IN_GLOBAL_ORDER, FRONTIER_EXHAUSTED }

data class TopCandidateSelection(
    val completion: CandidateCompletion,
    val alternatives: List<GeneratedCandidate> = emptyList(),
    val proof: TopCandidateProof = TopCandidateProof.NONE,
    val maximumAlternatives: Int = CandidateGenerator.MAX_ALTERNATIVES,
) {
    init {
        require(maximumAlternatives in 1..CandidateGenerator.MAX_ALTERNATIVES)
        require(alternatives.size <= maximumAlternatives)
        require((completion == CandidateCompletion.COMPLETE) == (proof != TopCandidateProof.NONE))
        require(proof != TopCandidateProof.REQUESTED_IN_GLOBAL_ORDER || alternatives.size == maximumAlternatives)
    }
    override fun toString(): String = "TopCandidateSelection(completion=$completion, proof=$proof, redacted)"
}
