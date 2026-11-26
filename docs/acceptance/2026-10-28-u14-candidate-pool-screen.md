# U14: initial hidden-candidate utility screen

The current controller's local product replay ran twice on the existing 12,000
multilingual regression rows. Both projections matched (SHA-256
`fab02fa792f3a8ebc0721dff33e30f05d14cc30615b85e89963e7a13d6b4c1ec`);
the replay receipt bound 173 input files and recorded zero model calls. It used
noun-case-production mode and passed manual candidate generation to the
controller. These old, synthetic regression labels are not a natural-use sample.

For unambiguous typo rows, the table counts target matches case-insensitively.
The upper bound is the number of rows where the labelled target was absent from
the two visible corrections but appeared anywhere in the union of the raw
baseline and manual generation pools. The manual-only subset was absent from
the raw baseline pool. These are *not* counts of selectable positions 3–7:
the controller may reject, deduplicate or reorder candidates, and a future
expanded strip has not been implemented. The full raw union is deliberately
retained to avoid understating that upper bound.

| Language | Typo rows | Target visible | Hidden pool upper bound | Of which manual-only |
| --- | ---: | ---: | ---: | ---: |
| RU | 1,960 | 1,703 | 211 | 60 |
| EN | 1,990 | 1,849 | 22 | 0 |
| ES | 1,990 | 1,765 | 39 | 0 |

This supports investigating RU utility, but does not establish a benefit or
choose UI behavior. A separate expansion-off/on replay with the controller's
validated full display order, first-two parity, tap invalidation, API 26
accessibility and Fold layout remain required by U14. No UI, policy or APK was
changed.

The [numeric receipt](2026-10-28-u14-candidate-pool-screen-evidence.json)
binds the corpus, opaque identity mapping, source-bound replay receipt, raw
observations and audit script. Two audit runs matched byte for byte. The local
replay outputs remain under ignored `build/u14-current-product-replay-v1/`;
they contain corpus text. Two focused audit tests cover the upper-bound logic,
identity, missing observations, request mismatch and invalid labels. No hosted
CI or physical-device test was run.
