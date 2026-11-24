# A2 empty-prefix current-controller probe

The disclosed synthetic input `молоо` was replayed with an empty prefix through
the current-product host controller, twice, without model calls. The timing-free
projections matched. In this model-free path the controller formed no model
request; `молоко` was not in either the ordinary three or the expanded seven
candidate lists. This does not test a model-enabled Android session or establish
that the earlier [two-candidate scorer counterexample](2026-10-29-a2-empty-prefix-scorer.md)
is an actual request from the keyboard.

The complete projection and sanitized source/asset receipt are retained in
`tools/typing_experiments/a2-empty-controller-v1/`. All 42 distinct observed
candidate, input and intended-target contexts, including internal local and
neighbor pools, are added to both public registries. The check verifies the
pinned projection, the prior synthetic source registration and the exact entries;
it runs without `build/`. These disclosed contexts are not an independent
holdout and no accuracy, admission, device or feature-enablement claim follows.
