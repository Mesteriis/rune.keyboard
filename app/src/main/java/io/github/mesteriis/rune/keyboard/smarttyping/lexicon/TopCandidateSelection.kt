package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

/** A top-seven certificate is separate from exhaustive [LexiconScanStatus.COMPLETE]. */
enum class TopCandidateProof { NONE, SEVEN_IN_GLOBAL_ORDER, FRONTIER_EXHAUSTED }

data class TopCandidateSelection(
    val completion: CandidateCompletion,
    val alternatives: List<GeneratedCandidate> = emptyList(),
    val proof: TopCandidateProof = TopCandidateProof.NONE,
) {
    init {
        require(alternatives.size <= CandidateGenerator.MAX_ALTERNATIVES)
        require((completion == CandidateCompletion.COMPLETE) == (proof != TopCandidateProof.NONE))
        require(proof != TopCandidateProof.SEVEN_IN_GLOBAL_ORDER || alternatives.size == CandidateGenerator.MAX_ALTERNATIVES)
    }
    override fun toString(): String = "TopCandidateSelection(completion=$completion, proof=$proof, redacted)"
}
