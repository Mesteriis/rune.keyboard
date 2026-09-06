# Mechanical dot-fix current-controller diagnostic — 2026-09-06

One fresh actual-Kotlin controller replay completed all 6,000 original frozen spelling holdout rows with no harness errors. Exactly three final editor outputs differ from `product-controller-postfix`: the EN/ES/RU `find .` protected rows now retain their separator. Every ordinary spelling result, canonical outcome, model payload, and admission outcome is unchanged. The remaining `magdalene → Magdalene` error and RU `alignas → malignas` false change remain counted.

Full final-text correct/changed counts are EN **293/304**, RU **341/358**, ES **396/409**. This is diagnostic evidence on already revealed holdout, not unseen qualification. No thresholds, fitting, exclusions, relabeling, or rounding-based gate decision was applied.

## Execution scope and source identity

Fresh output directory: `build/smart-typing-0.3/current-source-replay-20260906/product-controller-dotfix/`. Previous directories, scripts, jars, receipts, and observations were not overwritten. The actual 39 production Kotlin files and scratch harness were freshly compiled with the pinned Java 17/Kotlin 2.2.10 toolchain; all 12 packaged EN/RU/ES trie/length/rank/case assets were validated by actual production readers. The raw ambiguity and computed `canonicalCaseAutoEligible` fields remain exported.

The base commit is `93b92f61fbf54da064634f83ad1ba255519db8e4`, with the current working-tree mechanical dot fix. Exactly one compiled production file differs from the preceding post-canonical-fix diagnostic:

- `MechanicalPunctuationPlanner.kt` before SHA256: `46b8bd16696a6f1e46acb5678abbf41c463fd7c344a7ad22b6d9dec5d7f8e68a`.
- Actual compiled current SHA256: `5cd4a0d631796da0827a720653d92a21cac701eef2c375b546ce8409b9d528ea`.

All other production-source, asset, toolchain, corpus, and numeric-cache inputs match the preceding run. The driver allows this one explicit planner source transition and aborts on other unexpected current-input drift. It also rechecks every bound input after execution; final independent verification found no drift. No production/test/tooling edits, model calls, historical score-cache reads, Gradle/device actions, commits, or delegation were performed by this diagnostic.

The root's separate API 37 full run uses the installed `93b92f6` APK. It does **not** validate the current working-tree dot fix, and this report does not claim otherwise. This run is host controller evidence only.

## Frozen inputs and numeric admission

All 6,000 complete original row objects are identical to `product-controller-postfix`: 2,000 per language, comprising 1,000 typo, 700 correct, and 300 protected rows. Original expected spellings, `noAuto` flags, cohort labels, and repetitions remain unchanged. Labels enter only the evaluation join, never the Kotlin runtime harness.

Fresh native run/complete receipts, every recorded scoring-input hash, and cache SHA256 `c0b93073e00f074cbb88949163bfcc35c10fc408f167b0971739590761377af7` were checked before admission. The 2,940 reconstructed exact requests retain corpus digest `75fedb01d250b525a260b4cc7ae1202197fcc98f098cf6c83d956029a39b6401`. Every actual `beginModelRanking` prefix, continuation order, and candidate ID list must match the scored request before a reply is constructed.

| Language | Exact numeric replies accepted | Matched scoring failures retained | New unscored requests refused | Payload mismatches |
| --- | ---: | ---: | ---: | ---: |
| EN | 1,002 | 2 | 11 | 0 |
| RU | 973 | 10 | 11 | 0 |
| ES | 951 | 2 | 11 | 0 |
| Total | 2,926 | 14 | 33 | 0 |

There are 3,027 rows with no current model request. All 14 native `SCORING_FAILED` records remain errors delivered as UNAVAILABLE with empty scores; all 33 new protected `jsonl`/`logp` fragment payloads remain explicitly refused, never assigned another request's numbers. All 6,000 actual model request objects and admission outcomes match the preceding run exactly. The 33 fragment model orderings remain unmeasured.

Actual settings remain `KeyboardSettings.DEFAULT`, HIGH_CONFIDENCE, width 3, default mechanical punctuation, and unchanged `SpellingQualification.CURRENT` at fixed default95. No qualification override is injected. The same Rune-owned prefix/target actions, ready final-target candidate reply, independent in-memory editor executor, and exact Backspace observation are used.

## Results and comparison

Full final-text change retains the previous diagnostic definition: actual final editor text differs from frozen `prefix + space + typed + final space`, including any mechanical changes during typing. A changed result counts correct only when its unchanged typo label has `noAuto=false` and the complete final text equals the frozen expected text. Counts below are exact; no rounded result is used for a gate.

| Language | Previous correct/changed | Current correct/changed | Current incorrect changes | False changes / negatives | Coverage / total rows |
| --- | --- | --- | ---: | --- | --- |
| EN | 293/305 | 293/304 | 11 | 0/1,000 | 304/2,000 |
| RU | 341/359 | 341/358 | 17 | 1/1,000 | 358/2,000 |
| ES | 396/410 | 396/409 | 13 | 0/1,000 | 409/2,000 |

The exact ratios are authoritative. Raw stored precision values are EN `0.9638157894736842`, RU `0.952513966480447`, ES `0.9682151589242054`. Stored Wilson 95% precision intervals are EN `[0.9363786768920008, 0.9796772730775392]`, RU `[0.9252761807224279, 0.9701436007917574]`, and ES `[0.9463845882089843, 0.9813323157426246]`. Full unrounded precision, false-change, coverage, abstention, and Wilson values are retained in `summary.json`. The intervals describe repeated frozen rows, not independent user samples; no unseen qualification follows.

Overall: 1,030 correct results / 1,071 changed rows; 41 incorrect changes; one false change / 3,000 correct/protected rows; coverage 1,071/6,000. There are zero mechanical typing changes and zero mechanical boundary auto-edits. Ordinary spelling remains exactly EN 293/304, RU 341/358, ES 396/408. The extra ES change is still the canonical `magdalene → Magdalene` typo failure, so it is not silently excluded from the 396/409 full result.

Every changed final output relative to the preceding run is preserved in `dotfix-comparison.json`:

- `en-holdout-protected-command-01`: `The reference lists find. ` → `The reference lists find . `.
- `es-holdout-protected-command-01`: `La referencia indica find. ` → `La referencia indica find . `.
- `ru-holdout-protected-command-01`: `В справочнике найдено find. ` → `В справочнике найдено find . `.

Each current row records `inputChangedByTyping=false`, no automatic boundary edit, and Backspace restoring its exact unchanged pre-boundary `find .` text. These rows remain in the denominator with their original labels. The remaining 5,997 final editor outputs are identical to the preceding run. Correct replacement counts remain 293/341/396; only the three erroneous mechanical changes disappear.

All 1,071 actual boundary auto-edits (1,070 ordinary plus one canonical) Undo exactly. All 6,000 subsequent Backspace actions restore the exact pre-boundary state. The RU failed-model deterministic `пластыр → пластырь` suggestion remains ineligible for automatic replacement; the archived ordinary 342/359 is not substituted for the actual current 341/358. The ordinary RU protected `alignas → malignas` false change and ES canonical `Magdalene` error remain fully recorded.

## Evidence and limits

The new directory retains the current harness and driver, pinned compile/run arrays and classpath, compiled jar, full frozen inputs, exact scored payloads, fresh response records, source transition, source/asset/toolchain/corpus/cache binding, all 6,000 raw observations, joined row evidence, errors/refusals, actual editor commands, candidate casing metadata, Undo state, aggregate metrics, and the before/after comparison.

- `execution-receipt.json`: SHA256 `31c044e7c66224a7dcc08e0000225920654fc1ef41a22781b809be33a5fcb439`.
- `row-evidence.jsonl`: SHA256 `812c6adf72c38b92142ce5828e230c0fb893667fedee62114bfd77877684bbcd`.
- `actual.jsonl`: SHA256 `7fc56b7f1a3f5d68d60ecc178fd84c0996a780e281d5582fb4a3de9afede7f92`.
- `summary.json`: SHA256 `e833bee405cc0622d53b0d75634b48eadd233a1caf0f6a51d1bd8b676bca782d`.
- `dotfix-comparison.json`: SHA256 `5ad6682459cb401dd5147ee6de51c3581d1ed52db59b5b07ede9e0b05c5a3c83`.
- `product-controller.jar`: SHA256 `b303ea14b46b9f16efa96a0b0740d14a43f372d803028b1cddaed47fdae8fb30`.

All recorded prior `product-controller-postfix` artifacts, current recorded artifacts, and current bound inputs were independently rehashed successfully. Previous receipt remains `452ee093c8f5c16dd39c15b310a8851cf337e1d50480b6a332ccfc5911bea439`. Compile plus full host replay took 35.81765112499852 seconds; this is not Android performance evidence.

The harness uses actual production Kotlin with an independent in-memory `TypingEdit` executor and JVM `BreakIterator`; it does not exercise a real Android `InputConnection`, keyboard-view/symbol-layer dispatch, asynchronous candidate availability, reentrant callbacks, or editor IPC failures. Only the final target receives a ready candidate reply. Unscored fragment requests remain explicit limitations, and this spelling replay does not score contextual punctuation model suggestions. Current dot-fix Android validation and unseen quality qualification remain outside this report.

The bounded diagnostic and report are complete; no implementation patch was made by this task.
