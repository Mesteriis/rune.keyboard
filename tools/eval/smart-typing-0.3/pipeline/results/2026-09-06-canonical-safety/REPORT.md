# Post-fix canonical and full-product diagnostics — 2026-09-06

Fresh actual-Kotlin reruns confirm that the bounded canonical fix removes all 34 previously observed automatic casing changes on the frozen correct/protected rows. `Paris`, `London`, and `Москва` still apply automatically with exact Undo. The full spelling-row replay retains the remaining `magdalene → Magdalene` error and three mechanical `find . → find.` changes. No outcomes were dropped or relabeled.

The full final-text result is EN 293/305, RU 341/359, ES 396/410 correct/changed. Russian precision is exactly 94.98607242339833%, below 95%; it is not rounded into a pass. This is diagnostic evidence on already revealed holdout, not a new qualification or threshold-fitting run.

## Fresh directories and source binding

Both runs recompiled the current actual production sources in new sibling directories:

- `build/smart-typing-0.3/current-source-replay-20260906/canonical-controller-postfix/`: 3,000 frozen correct/protected rows plus the seven public controls.
- `build/smart-typing-0.3/current-source-replay-20260906/product-controller-postfix/`: all 6,000 original frozen spelling holdout rows with exactly bound fresh native responses.

The old canonical/controller scripts, jars, receipts, input files, output files, and asset-matrix evidence remain byte-for-byte unchanged. The new harnesses export both raw `canonicalCaseUnambiguous` and computed `canonicalCaseAutoEligible` for every candidate. No production, test, or evaluator/tooling source was edited by this diagnostic; all new scripts and artifacts are scratch-local. No model calls, old score-cache reads, Gradle/device operations, commits, or delegation occurred.

Exactly two of the 39 compiled production source files differ from the prior diagnostic:

| Source | Pre-fix SHA256 | Compiled post-fix SHA256 |
| --- | --- | --- |
| `CandidateGenerator.kt` | `bb031b134b1fdf8dc6e24762595defe5f732157fe8143c3f0caa52dc57f4c580` | `61eb889e1d327f9933e4c189227c93baf2f89b4f08bad41db538d9bfdf354370` |
| `TypingSessionController.kt` | `255468e74e439b5013dc6b463afce796f2f49975fdec23224ecf527d8ff20825` | `e0546af4f012c95ab46cbe2d42837450ddd287b2c267ca560a21f8925afb9ee3` |

All other compiled production sources, all 12 packaged EN/RU/ES trie/length/rank/case assets, and pinned Java 17/Kotlin 2.2.10 toolchain inputs match the prior run. Both runs validated the assets through the actual production readers. Every current source/input hash matched after execution and again during final verification; no unexpected production drift was detected.

Settings and policy remain actual `KeyboardSettings.DEFAULT`, HIGH_CONFIDENCE, default mechanical punctuation, generator width 3, and unchanged `SpellingQualification.CURRENT` at fixed default95. No qualification override or numeric threshold change was introduced. Frozen source input labels and all 6,000 complete row objects are identical to the prior full-product run.

## Canonical negative rows and public controls

All 3,000 frozen negatives completed without errors. There are still 57 actual canonical candidate rows, but zero canonical/boundary auto-edits. All 34 previous canonical negative edits are now withheld: EN `clay`/`resistance`, ES `campo`/`puerto`/`arrecife`, and EN/RU protected `que`/`si`. Candidate metadata remains visible: the latter cross-language conflicts retain raw `unambiguous=true` but now have `canonicalCaseAutoEligible=false`. The source ambiguity fact is not rewritten to encode combined eligibility.

Three mechanical `find . → find.` typing changes remain separately recorded. There are 423 rows with no eligible candidate request. All 3,000 Backspace actions restore the exact pre-boundary state; that state already includes any earlier mechanical typing change.

| Public input | Canonical candidate | Raw unambiguous | Auto eligible | Actual final text after space | Immediate Backspace |
| --- | --- | --- | --- | --- | --- |
| `we will` | Will | false | false | `we will ` | exact pre-boundary restore |
| `we may` | May | false | false | `we may ` | exact pre-boundary restore |
| `a brown` | Brown | false | false | `a brown ` | exact pre-boundary restore |
| `paris` | Paris | true | true | `Paris ` | exact automatic-edit Undo |
| `london` | London | true | true | `London ` | exact automatic-edit Undo |
| `москва` | Москва | true | true | `Москва ` | exact automatic-edit Undo |
| `juan` | Juan | false | false | `juan ` | exact pre-boundary restore |

All seven controls retain the canonical correction as the selected visible suggestion. The four withheld candidates do not auto-apply on the space boundary. The three positive controls emit actual controller automatic edit transactions and Undo them exactly. This run observes suggestion retention and boundary behavior; it does not claim a separately executed manual candidate tap.

## Fresh score admission preserved

The ordinary scored export predates the explicit source fix. The new scratch driver records this in `scored-export-source-transition.json`, preserving the scored export's historical generator hash alongside the current compiled generator hash. It does not claim that historical export was produced from changed source or weaken the original qualification verifier. Current response admission still requires exact live payload equality.

Fresh run/complete receipts, all recorded scoring input hashes, cache identity, and fresh scores SHA256 `c0b93073e00f074cbb88949163bfcc35c10fc408f167b0971739590761377af7` were verified before admission. The exact reconstructed 2,940 scored requests retain digest `75fedb01d250b525a260b4cc7ae1202197fcc98f098cf6c83d956029a39b6401`. The actual `beginModelRanking` prefix, continuation order, and candidate IDs were compared before each response.

| Language | Exact numeric replies accepted | Exact scoring errors preserved | New requests without scored payload refused | Payload mismatches |
| --- | ---: | ---: | ---: | ---: |
| EN | 1,002 | 2 | 11 | 0 |
| RU | 973 | 10 | 11 | 0 |
| ES | 951 | 2 | 11 | 0 |
| Total | 2,926 | 14 | 33 | 0 |

All 6,000 live model request objects and admission outcomes are identical to the pre-fix full-product run. All 14 `SCORING_FAILED` rows remain failures delivered as UNAVAILABLE with empty numeric scores. All 33 additional protected `jsonl`/`logp` fragment requests remain explicitly refused rather than borrowing scores for a different payload. Their model ordering remains unmeasured. No fresh response is omitted or reassigned.

## Full final-text results

Metrics use unchanged frozen labels and the same prior diagnostic definition: a full change is actual final text differing from the original `prefix + space + typed + final space`. This includes mechanical edits during input. A replacement counts correct only for a typo row with `noAuto=false` and the exact expected final text. All false changes and errors remain included.

| Language | Pre-fix correct / changed | Post-fix correct / changed | Post-fix precision, Wilson 95% | False changes / 1,000 negatives, Wilson 95% | Coverage / 2,000 rows, Wilson 95% |
| --- | --- | --- | --- | --- | --- |
| EN | 293 / 319 | 293 / 305 | 96.07% [93.25%, 97.74%] | 1; 0.10% [0.02%, 0.56%] | 15.25% [13.74%, 16.89%] |
| RU | 341 / 361 | 341 / 359 | 94.9861% [92.21%, 96.81%] | 2; 0.20% [0.05%, 0.73%] | 17.95% [16.33%, 19.69%] |
| ES | 396 / 428 | 396 / 410 | 96.59% [94.35%, 97.96%] | 1; 0.10% [0.02%, 0.56%] | 20.50% [18.79%, 22.33%] |

Exactly 34 of the 6,000 final editor outputs differ from the pre-fix replay, each removing one previously observed canonical negative edit. Correct replacement counts do not change. Overall there are 1,030 correct results among 1,074 changed rows, with four false changes among 3,000 correct/protected rows. No other final-text difference was observed. `postfix-comparison.json` preserves every changed row and both outputs.

Ordinary spelling is unchanged at EN 293/304, RU 341/358, ES 396/408, with negative false changes 0/1/0 respectively. The Russian `ru-holdout-typo-10-4-1` failed-model deterministic suggestion `пластыр → пластырь` remains ineligible for automatic replacement, exactly as in the prior current-source run; the archived 342/359 ordinary count is not restored by this fix.

The remaining extra paths are retained:

- `es-holdout-typo-00-3-5`: `magdalene → Magdalene`, expected `magdalena`. This English fallback canonical candidate retains raw `unambiguous=true` and computed `canonicalCaseAutoEligible=true`. It still auto-applies without a model request and is still counted incorrect under the unchanged typo label. Undo restores the original lowercase text exactly.
- Three protected `command-01` rows still undergo mechanical `find . → find.` during typing, one per language. They remain false changes in full-text metrics.
- The ordinary RU protected `alignas → malignas` false change remains. There are no additional mechanical boundary auto-edits.

Count reconciliation is EN `304 ordinary + 1 mechanical = 305`; RU `358 ordinary + 1 mechanical = 359`; ES `408 ordinary + 1 canonical + 1 mechanical = 410`. The full run emitted 1,071 actual boundary auto-edits (1,070 ordinary plus one canonical); every one had exact controller Undo. All 6,000 subsequent Backspace actions restored exact pre-boundary text. This Undo assertion does not erase the three earlier mechanical changes from the evaluation.

## Preserved evidence and verification

Each new directory retains its current source-binding receipt, exact pinned compilation/execution command arrays, jar/classpath, all raw inputs and outputs, row-level candidate metadata including both casing flags, editor command logs, controller state, and exact Undo results. The full-product directory also retains exact scored payloads, fresh response records, all errors/refusals, source-transition documentation, unrounded metrics and Wilson intervals, and the post-fix comparison.

| Artifact | SHA256 |
| --- | --- |
| Canonical post-fix `execution-receipt.json` | `5bb64d4baa1bbd4f0569f647769fd68b4760e67e634727cf400e6175fcae6239` |
| Canonical post-fix `row-evidence.jsonl` | `2208c8ec1ba754d4eaaa8b25458379ffc6214c07d5dd63d0fa537d023905db5f` |
| Product post-fix `execution-receipt.json` | `452ee093c8f5c16dd39c15b310a8851cf337e1d50480b6a332ccfc5911bea439` |
| Product post-fix `row-evidence.jsonl` | `9b5b4d3c73a0942a2fb421ac34cb6aa4cee6b99b4012ae5f1f2ab273b8d8f332` |
| Product post-fix `summary.json` | `50550f49dbd50c0f3392b79d242edf0f3fe977455e04530dbf8b0246d78cb950` |
| Product post-fix `postfix-comparison.json` | `c689705c9be3c47962236e0de25aa6f0dc2e63199ed6f3baf8675ad54cc84628` |

Every recorded artifact hash in both original controller receipts, the original asset-matrix receipt, and both post-fix receipts was independently rechecked. Every current post-fix bound input was also rechecked; all matched. The original canonical receipt remains `3ae7abdaffb818a97a7e7c66d705e61f5d8606e58d0fd9c029140e4d4546d72a`, and original full-product receipt remains `5a13c77843f47022fe656c6214c9d611e0bcad0f8b509b7f43e4799a2e0c9e0e`.

These are host diagnostics using actual production Kotlin and an independent in-memory `TypingEdit` executor, with JVM `BreakIterator` instead of Android ICU. They do not execute a real Android `InputConnection`, key-view/symbol-layer dispatch, asynchronous candidate timing, editor IPC failures, or reentrant callbacks. Prefix/target text is Rune-owned through text actions; only the final target receives a ready candidate reply. The 33 unscored fragment model requests remain explicit limitations, and contextual punctuation model suggestions are not scored in this spelling replay. Wilson intervals are descriptive over repeated frozen rows. No new qualification, policy tuning, or implementation changes are claimed.

Both bounded post-fix diagnostics and this separate report are complete.
