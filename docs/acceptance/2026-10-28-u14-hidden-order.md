# U14: validated hidden candidate order

A replay-only controller observer now obtains the actual validated candidate
selection and computes its full contextual order. It preserves the already
visible correction IDs and order first, then appends remaining ranked
candidates. It does not make those hidden IDs selectable. The existing view
still limits itself to two corrections; automatic admission remains unchanged.
A controller test checks visible-prefix parity, rejection of a hidden ID and
literal Space behavior for a manual-only pool.

The current-product replay ran twice per manual-expansion setting on the
existing 12,000-row multilingual regression corpus. Its complete observed
projections were deterministic. Compared against the immediately preceding
matching-setting baselines, all 12,000 rows matched per mode after explicitly
excluding only the new `fullCandidateOrder` observation. Every row's visible
corrections were also verified to equal the prefix of the new full order.

| Language | Unambiguous typo rows | Target at 3–7, expansion on | Target at 3–7, expansion off |
| --- | ---: | ---: | ---: |
| RU | 1,960 | 211 (10.77%) | 125 (6.38%) |
| EN | 1,990 | 22 (1.11%) | 22 (1.11%) |
| ES | 1,990 | 39 (1.96%) | 39 (1.96%) |

The target comparison is case-insensitive and excludes a target already in the
first two corrections. These are synthetic regression rows, not measured user
benefit, independent qualification or device acceptance. The earlier on/off
[visible comparison](2026-10-28-u14-visible-modes.md) shows 44 target gains and
39 losses in the existing Russian first two when the setting changes; new UI
must preserve the first two for its corresponding setting.

The first instrumented replay attempted an unchanged baseline comparison and
failed on all rows because the new observation field was present. The retained
failure reports showed `/fullCandidateOrder` as the only differing path in
both modes. A corrected comparison explicitly excludes that field only for
baseline parity while retaining it for same-mode determinism; two fresh runs
then passed. The local failed and passing artifacts remain in ignored build
output, including their raw receipts and corpus text.

The [numeric receipt](2026-10-28-u14-hidden-order-evidence.json) binds both
source-bound replays, their opaque mappings, source rows and analyzer. Two
analyzer runs matched byte for byte. All 1,356 JVM tests passed with no skips;
the replay Python suite passed 28 tests with one conditional skip, and two
hidden-order analyzer tests passed. No Fold, API 26 accessibility, expanded
view, touch invalidation or new automatic policy was tested. The RU result
warrants continuing to an expandable view; U14 remains open until the specified
UI and device checks pass.
