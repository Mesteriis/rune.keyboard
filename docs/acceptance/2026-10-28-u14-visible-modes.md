# U14: current visible strip with manual expansion on and off

The label-free current-product replay now accepts an explicit manual-expansion
mode. `on` preserves the previous default; `off` withholds the supplementary
manual pool from both candidate replies, like the coordinator's disabled
setting. No product code or UI changed. Each mode was replayed twice on the
same 12,000 multilingual regression rows, with matching projections within
mode and zero native model calls. The new default-on projection also matched
the preceding 12,000-row U14 run byte for byte.

| Language | All rows | Visible text changes | Unambiguous typo rows | Target visible on / off | Gains / losses when on |
| --- | ---: | ---: | ---: | ---: | ---: |
| RU | 4,000 | 1,439 | 1,960 | 1,703 / 1,698 | 44 / 39 |
| EN | 4,000 | 0 | 1,990 | 1,849 / 1,849 | 0 / 0 |
| ES | 4,000 | 0 | 1,990 | 1,765 / 1,765 | 0 / 0 |

View comparison includes all visible roles and text; 1,467 Russian view objects
change when IDs and metadata are included. No selected-ID, post-space editor
snapshot or post-Undo snapshot differed across any of the 12,000 cases. Target
comparison ignores case, and the synthetic labels and source-bound local replay
are not a natural-use sample or physical-device proof. The manual setting itself
already changes the first two suggestions: its comparison is not the required
parity test for a new expandable UI.

The prior raw-pool [screen](2026-10-28-u14-candidate-pool-screen.md) was an
upper bound, not a validated hidden rank. Positions 3–7 of the controller's
validated and ordered pool still need measurement; the table does not justify a
claim that all 211 upper-bound cases become selectable. Any expansion UI still
needs current session/revision/epoch invalidation, no automatic admission from
the hidden portion, first-two parity against the matching setting, API 26
accessibility and Fold layout checks.

The [numeric evidence](2026-10-28-u14-visible-modes-evidence.json) binds both
receipts, observations, row labels, mappings and comparison code; the two report
runs were byte-identical. Four focused comparator tests pass. Replay harness
unit suites passed 27 tests with one conditional skip. Raw replay files and
receipts are in ignored `build/u14-expansion-{on,off}-v1/` and contain corpus
text and machine-specific paths; they are not committed.
