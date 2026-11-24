# Q6 cleaned training-text context audit

The existing text-exposure auditor now derives target/context identities from
complete words in each actual cleaned emitted fragment, using up to 128
preceding characters from that fragment. It measures lexical and regression
control overlaps and cross-partition context reuse. A word cut at the fragment
boundary is counted as truncated and is not represented as a complete target.
These identities describe cleaned training text; they do not establish every
original-article context or overall historical coverage. The audit remains
diagnostic and the existing unchecked-text refusal remains in force.

On the previously disclosed, intercepted word-ranking selector output, its
430 text fragments yield 12 distinct lexical context overlaps, two distinct
regression-control context overlaps and 555 pairwise cross-partition context
intersections. The inputs and registry snapshots are hash-bound in the raw
report. Two runs were byte-identical. The result describes previously exposed
public data, not an independent holdout or model qualification.

The focused 17-test suite passes, including explicit lexical/control collisions,
cross-partition reuse and truncated-word handling. Before this change the full
stdlib profile passed 797 tests without skips and the scientific profile passed
79 tests with one MLX skip. An initial scientific invocation in a different
environment failed because CatBoost was absent; it is not counted as a pass.
