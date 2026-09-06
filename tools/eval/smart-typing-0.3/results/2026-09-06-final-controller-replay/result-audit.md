# Final product spelling replay result audit — 2026-09-06

**Result:** the completed numeric cache/replay evidence passes this bounded integrity audit. None of the 297 holdout Original misses is an observed candidate set that omits its selectable Original. They are 297 empty candidate states without a current word, all preserving the protected input exactly. The frozen report's all-row Original gate remains **false**; this audit does not change it or declare an overall release PASS.

Scope: completed artifacts under `build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/`, the previously reviewed tooling/controller contracts, and the original user specification. No source, metric, threshold, data or existing artifact was changed. No model, build, Gradle, device or network operation ran. Read-only Python checked bytes, admitted existing caches and classified/joined existing observations. Only this report was written.

## All 297 Original misses

Every holdout-ready row was inspected; this is not a sample. Each language has 99 misses out of 2,000 rows. The same category counts apply independently to EN, RU and ES:

| Category | Per language | Total |
| --- | ---: | ---: |
| branch_name | 10 | 30 |
| command | 1 | 3 |
| digits | 10 | 30 |
| environment_key | 10 | 30 |
| hex_literal | 4 | 12 |
| identifier_python | 4 | 12 |
| ipv4 | 10 | 30 |
| ipv6 | 10 | 30 |
| package_name | 10 | 30 |
| semver | 10 | 30 |
| url | 10 | 30 |
| version_identifier | 10 | 30 |
| **Total** | **99** | **297** |

All 297 have `cohort=protected`, `noAuto=true`, no local candidate request, no model request, `NO_CURRENT_MODEL_REQUEST`, an empty candidate list, no selected candidate, and no automatic spelling/canonical/mechanical edit. Their full text exactly equals the unchanged controlled input before Space, that input plus one Space afterward, and the unchanged input after immediate Backspace. All 297 pass exact restoration; none is an ordinary spelling mistake or a model error.

The complete state classification is:

- **294 have null composition and null actual Original.** Terminal characters are 285 digits, six underscores and three closing parentheses. The first example is `feature/holdout-fixture-0`, row `en-holdout-protected-branch_name-00`, at `row-evidence.jsonl:17121`.
- **Three have only a pending boundary, with no word:** `find .`, one row per language. `composingText` and `leadingBoundary` are `" ."`, `typedWord` and actual Original are empty strings. IDs are `en-holdout-protected-command-01`, `es-holdout-protected-command-01`, `ru-holdout-protected-command-01`, at row-evidence lines 17162, 17462 and 17762. These are not null-composition rows, but still contain no current candidate word.

Conversely, **all 5,703 nonempty holdout candidate sets contain the matching explicit Original**, and there are zero nonempty current-word observations lacking that Original. All 5,577 actual local generation observations preserve their current request token as Original. All 2,973 actual holdout model requests include Original at candidate ID 0, exactly matching the live Original. The separately recorded full-token generator observation also retains the corpus token as Original on 6,000/6,000 rows; this auxiliary generator observation must not be confused with an active controller candidate set.

The unavailable control has the same 297 empty-state misses, so model ranking did not cause them. Calibration likewise has 294 empty states and zero nonempty-word Original omissions. A no-model-request outcome alone is **not** an exemption: many rows without a model request still own a word and correctly show Original.

For reproducible identification, SHA-256 of the sorted 297 miss IDs encoded as compact UTF-8 JSON is `c8716196b081e2d5a3c2b7379c5c3c05b5fa30f9e8e3362c847aa3394890816d`. All IDs remain in the immutable row evidence.

## Contract interpretation and recommendation

The original user specification says the original word must be present **in the candidate set** (`/Users/avm/.codex/attachments/970220aa-3046-4612-a12d-3d1e9a832148/pasted-text.txt:345`), lists Original as part of that set (`:1096`), and requires it to remain available in the candidate strip (`:906`). The same specification explicitly distinguishes Idle, PendingBoundary and ComposingWord, says the first letter starts a word, and specifies boundaries/transitions that clear candidates (`:751`). It also requires fully hidden candidate states for certain editors (`:930`). Thus the user contract does not require retaining a stale selectable word while no current word exists.

The implementation follows that state distinction: `TypingSessionController.kt:127` requires a nonempty owned `typedWord` for candidate composition; `:432` returns an empty view without that ownership, and `:435` inserts Original whenever a candidate composition is owned. Nonword input finishes composition and commits plainly (`:581`), while pending punctuation retains boundary-only composition (`:559`). `SmartTypingViewState.kt:5` documents the enabled empty state between words; its constructor requires exactly one Original whenever the candidate list is nonempty (`:23`). Showing an empty strip's reserved height is not the same as presenting a candidate set without Original.

The current evaluator faithfully computes its stricter frozen rule: `original_retention` returns false for an empty set, and the gate requires true on every row (`final_product_replay.py:420`, `:396`). The implementation brief and early report explicitly used that all-row formulation. Therefore leave the completed report and its `allPass=false` untouched; do not silently relabel these observations as retained Original or remove protected rows from precision/false-change/Undo denominators.

**Recommended next step:** record a bounded contract clarification separating (a) Original presence/selection while an independently identified owned nonempty candidate word exists, from (b) exact text preservation and no stale candidates when no word exists. Add a separate reviewed applicability/result annotation derived from controller state, with all 6,000 rows still accounted for. Do not derive applicability solely from whether the candidate list is nonempty, since that would hide a real missing-list defect. Do not use model-request eligibility or corpus category as an exemption. For this evidence, the annotation is 5,703 applicable sets with Original and 297 no-word states with exact preservation, with zero applicable omissions. Existing frozen all-row statistics should remain visible alongside it.

No production change is supported by these misses. In particular, resurrecting committed protected tokens merely to place an Original button into an idle/boundary-only strip would create a different behavior and could violate ownership/stale-selection constraints. This host replay observes candidate identities; it does not independently execute an Original tap on every corpus row or replace the separate Android interaction tests.

## Completed numeric and replay evidence

Re-ran the existing **read-only admission functions**, not scoring: current bound export bytes, independent score identities, full complete receipts, cache hashes, and the calibration → policy-freeze → holdout chain all validate. Separately checked that each delivery JSON record is exactly derived from its frozen request and native response and that every TSV byte matches the prescribed adapter. All four replay files contain exactly their 6,000 expected unique rows with `status=COMPLETE`. Their live request manifests exactly equal the frozen manifests, including payloads and ordered IDs.

| Split | Requests/responses | Numeric successes | Retained native errors |
| --- | ---: | ---: | ---: |
| Calibration | 2,983/2,983 | 2,974 | 9 |
| Holdout | 2,973/2,973 | 2,959 | 14 |
| **Total** | **5,956/5,956** | **5,933** | **23** |

All errors are `SCORING_FAILED`; each is retained as an explicit matched unavailable outcome, with no fabricated numeric success. Every successful numeric reply was accepted by the current controller. All 23 error rows preserve full raw input plus Space and immediate Backspace exactly, with no automatic edit. Holdout error counts are EN 2, RU 10, ES 2. There are zero missing, duplicate or foreign score IDs and zero payload-admission refusals. The complete receipts record zero retries. These checks establish one retained response per frozen request; they do not independently instrument the model process to count internal native work.

Joined all **24,000** row-evidence entries back to the exact source rows and corresponding raw replay observations with no duplicate `(split, mode, id)` keys. Recomputed the decision/text/Original/Undo evaluation predicates and reproduced every published split/mode summary, including the unchanged false Original gates.

| Holdout language | Correct ordinary changes / changes | Point precision | Aggregate false changes / negatives | Immediate restoration |
| --- | ---: | ---: | ---: | ---: |
| EN | 293/304 | 96.3816% | 0/1,000 | 2,000/2,000 |
| RU | 341/358 | 95.2514% | 1/1,000 | 2,000/2,000 |
| ES | 396/408 | 97.0588% | 0/1,000 | 2,000/2,000 |

The unchanged integer point-precision, spelling-volume, ordinary/aggregate negative-safety and restoration gates pass. Original remains 1,901/2,000 per language under the frozen all-row metric, so every published `allPass` remains false. The RU protected false change and all incorrect ordinary replacements remain real retained outcomes; the Original diagnosis does not excuse them. Model-unavailable ordinary automatic changes are zero. Holdout canonical count is one in ES and zero in EN/RU; mechanical changed rows are zero. The command-dot comparison retains 33 changed observations and 14 current scoring errors.

The report correctly says `releaseApproved=false`, no threshold fitting, revealed-data fixed-policy reproduction, and host JVM/independent-editor scope. Wilson intervals are descriptive; some lower bounds are below 95%, which does not change the user-approved **point** gate. This run is not new unseen qualification, phone latency, Binder availability, energy evidence, or contextual attribution.

## Audited identities

| Artifact | SHA-256 |
| --- | --- |
| export-receipt.json | `62748ec036e8ce8eb42f1902a49a8abd7fed00305b62913171219eff688be932` |
| report.json | `deb9a0958d7ec8473f34c8910c933c6d1fb6f1dc78dd8d08a24763d5419b8303` |
| row-evidence.jsonl | `6a19850ed122dd782ecde33aaba8087d76c77a34962fda44c055c94f717cfa75` |
| calibration-scores/complete.json | `576f206622fe50e35bf4630310f68d8245396b51bb6f019763810d35c5c0714d` |
| calibration-scores/scores.jsonl | `ce550e89ac17ab71dc949afacb0631f68b718aa0b80d301e947621995561182c` |
| policy-freeze.json | `de2489192a6e0b4dd7ceda7a77b9af99b8ce0b8fffeb167464d7f0e85143dc13` |
| holdout-scores/complete.json | `620dff8a84044edbfb84f45ee70a3f70cfef50a8ee46e09acd80ff571f28a995` |
| holdout-scores/scores.jsonl | `db0bb33c8e745d7d5aeb1f56c3761c34bfaa9cc2ae2d34285db57efd0900ae63` |

All are within the accepted review-second-fix-v2 directory named above. Existing files and their FAIL states were preserved.
