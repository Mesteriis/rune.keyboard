# Q6 original source contexts of emitted training text

The diagnostic text auditor now also maps complete emitted words back to the
source article. For each mapped token it derives the selector-segment prefix
(up to 128 characters) from the original spelling and punctuation, then checks
lexical and regression-control context keys and cross-partition reuse. Mapping
is refused for a source whose lowercased word sequence differs from the original
word sequence; truncated final words are not treated as complete targets. This
is a source-context diagnostic, not an independent corpus admission gate.

On the previously disclosed intercepted word-ranking output, all 430 fragments
mapped without a sequence mismatch. The resulting original-source contexts had
2,169 distinct lexical and 12 regression-control overlaps; the three partition
pairs shared 1,580 context identities. Two executions produced byte-identical
reports with source, inputs, dictionary and current registry hashes. These
numbers are specific to exposed data, not an estimate of a new corpus.

The focused test suite covers punctuation/case preservation, registry collisions,
cross-partition context reuse and truncated words. Overall source and registry
coverage remain incomplete; the collectors still refuse unchecked text, and no
new holdout or model qualification is claimed.
