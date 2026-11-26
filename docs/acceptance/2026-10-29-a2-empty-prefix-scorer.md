# A2 empty-prefix host scorer controls

Five disclosed synthetic two-candidate requests were sent twice to the pinned
host scorer and Rune Text 0.1 model. Four requests returned
`INSUFFICIENT_CONTEXT`; the request with an empty prefix and `молоко`/`молоо`
returned two finite scores. Both runs produced exactly the same response after
excluding duration. This is possible because the scorer compares common
candidate-token prefixes; an empty text prefix alone does not guarantee an
error. Suppressing all empty-prefix requests therefore changes potential model
behavior and requires qualification rather than being assumed equivalent.

These are artificial controls, not evidence of natural input frequency, model
quality, automatic correction or actual Android behavior. The five requests and
10 candidate contexts are retained in both applicable public ledgers; only the
Russian contexts are in the Russian lexical registry. No global single-word
exclusion is inferred. The [numeric receipt](2026-10-29-a2-empty-prefix-scorer-evidence.json)
binds the original model, host runner, source, registries and scores. The host
probe is reproducible with `python3 tools/ci/a2_empty_prefix_screen.py --output
build/<fresh-directory>` when those pinned local assets are present.

CI verifies disclosure and response validation without requiring the host model.
Tests cover both registries, malformed score responses and a checkout without
`build/`. A2 remains disabled until the independent long-context quality,
Android native and physical-device performance checks are complete.
