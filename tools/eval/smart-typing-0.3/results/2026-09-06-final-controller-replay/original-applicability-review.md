# Original applicability companion annotation review — 2026-09-06

Spec verdict: **PASS**. Code-quality verdict: **PASS** for this separate annotation of the exact previously audited replay. No actionable gap found in scope. This is not overall release approval or a replacement for the frozen all-row gate.

## Reviewed behavior

`tools/eval/smart-typing-0.3/pipeline/original_applicability.py:11` determines the applicable word state from the recorded controller `typedWord`, independently of candidate-list presence, corpus category and model-request status. A nonempty word still requires matching composition, matching actual Original and exactly one explicitly tagged Original with matching text and a nonempty ID (`:14`). Consequently an empty candidate list cannot turn a missing-Original defect into an exempt row.

The no-word branch handles both null composition and boundary-only composition. It requires an empty candidate list, no selected candidate, no actual Original word, no local/model request, no automatic edit, exact raw text before Space, exact insertion of Space and exact immediate Backspace restoration (`:23`). It does not simply classify every protected/no-request row as successful.

Aggregation rejects duplicate identities, retains each row and records failures instead of dropping them (`:39`). The CLI requires both caller-supplied audited input hashes, all 12 split/mode/language groups, and exactly 2,000 rows per group (`:67`). It writes only a fresh output via exclusive creation (`:92`). The result binds its own tool bytes and both source artifacts, copies the frozen holdout gates unchanged, and explicitly records `releaseApproved=false` (`:81`). No scoring, threshold selection or existing-artifact rewrite occurs.

The five scoped tests cover a word with no model request still requiring Original, wrong/duplicate Original, exact preservation and stale candidates in no-word states, boundary-only composition, and duplicate rows. I inspected these tests but did not rerun the root-reported five-test PASS. The CLI digest/fresh-output guards were inspected directly; the completed output's actual hashes and counts were independently verified below.

## Independent completed-result checks

Read both exact audited inputs and independently classified all **24,000** `(split, mode, language, id)` observations. No duplicate identity, predicate failure, missing group or count mismatch was found. Each of the 12 groups has 2,000 accounted-for observations and 2,000 passing the stated annotation contract:

| Split | Per language/mode: word present | Per language/mode: no word | Accounted for |
| --- | ---: | ---: | ---: |
| Calibration | 1,902 | 98 | 2,000 |
| Holdout | 1,901 | 99 | 2,000 |

Across both modes and all languages this is **22,818 word states + 1,182 no-word states = 24,000**. The holdout-ready group totals agree with the prior exhaustive audit: 5,703 word states and 297 exactly preserved no-word states, including the three boundary-only `find .` observations.

The copied frozen gates exactly match `report.json`: every language still has `originalAlwaysAvailablePass=false` and `allPass=false`. Neither the report nor row-evidence bytes changed. The annotation therefore explains applicability without changing the frozen calculation, numerical targets, corpus or its denominators.

## Exact identities and limits

| File/artifact | SHA-256 |
| --- | --- |
| `pipeline/original_applicability.py` | `25cb79bd88c0e553133fc88588c3b22394d299370d3f9e8d32ad1507e0d86db9` |
| `pipeline/test_original_applicability.py` | `2016d356743bbb62a67e781e52bead34967a26a5820ac0f72ce34569ac6a9db3` |
| `original-applicability.json` | `a4eedc1df519ca58df16133aa715574e0c84671431c8d7a7b86b3360ef2fbdb6` |
| Frozen `report.json` | `deb9a0958d7ec8473f34c8910c933c6d1fb6f1dc78dd8d08a24763d5419b8303` |
| Frozen `row-evidence.jsonl` | `6a19850ed122dd782ecde33aaba8087d76c77a34962fda44c055c94f717cfa75` |

Artifacts are under `build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/`. All listed hashes were checked against current bytes, including the annotation's internal bindings. This small tool relies on the expressly supplied, previously audited input pair; it does not replace full replay/cache admission or establish arbitrary unaudited data provenance.

The accepted claim is state-based Original presence and exact no-word text preservation in this host replay. Actual Android Original-tap behavior, asynchronous availability, unseen quality and release readiness remain separate. Only read-only filesystem/data checks and this report write were performed; no source edits, tests, model, device, Gradle or network operations ran.
