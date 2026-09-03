# Deterministic policy calibration — 2026-09-03

Baseline `0117d2932217d804b2fdc4c4c5b77dd54f8d4b26`. This is PR7 calibration
infrastructure and evidence; APK behavior/defaults are unchanged.

The actual bounded generator's2/4/8-candidate exports feed a portable integer
ranker. Features combine quarter-unit edit cost, integer frequency band, repeated
character edits, fallback and length difference. A positive margin must separate
the winner from both the second returned alternative and the original's calibrated
OOV penalty. Incomplete/protected/valid-word generation retains its unconditional
veto. Original is returned when evidence is insufficient or alternatives tie.

A declared10800-combination grid per language/width fits only the6000 calibration
spelling rows. Corpus labels, expected words and `noAuto` never reach the decision
function. `noAuto` replacements count as errors instead of being silently filtered
out. Correct/protected replacements always count as false changes. The initial
loader assumed all rows had `expectedSpelling`; this failed before any fit. The
corrected annotation layer handles the actual negative-row schema, with regression
coverage. Holdout rows are rejected by fitting and by generated-model dispatch.

For each admissible policy (precision >=99%, false-change <=0.5%), deterministic
selection maximizes correct changes, then minimizes errors and uses declared
threshold/grid tie breaks. No unseen-candidate or target injection is used.

| Total candidates | Language | Provisional replacements | Correct | Precision | False changes /1000 |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | EN | 106 | 105 | 99.06% | 0 |
| 2 | RU | 57 | 57 | 100% | 0 |
| 2 | ES | 146 | 145 | 99.32% | 0 |
| 4 | EN | 318 | 316 | 99.37% | 0 |
| 4 | RU | 326 | 323 | 99.08% | 0 |
| 4 | ES | 257 | 255 | 99.22% | 0 |
| 8 | EN | 78 | 78 | 100% | 0 |
| 8 | RU | 163 | 162 | 99.39% | 0 |
| 8 | ES | 171 | 170 | 99.42% | 0 |

Reports include exact row/unique-input counts, coverage, abstention, candidate
recall and descriptive Wilson95 intervals. Repeated authored lexical families
and candidate-panel rows are not independent typing samples. Four candidates
provide the best calibrated correct-change counts for each language within this
fixed grid, but ES remains below300 even on calibration. None of these results
qualifies production AutoReplace or substitutes for final holdout.

The four-candidate calibration was rerun: config/report bytes match exactly.
Configs bind grid, corpus, generator receipt and evaluator sources. Python16/16
PASS; JVM598/598 PASS, zero failures/errors/skips. All prescribed local lint,
three build variants, privacy, IME/dependency and native-symbol gates PASS.
Mandatory post-commit JVM is reported against its resulting SHA.

## Actual-candidate model scoring

A separate bridge maps each generated set to original plus its actual
alternatives. Prepared panels, expected answers and policy annotations never
reach native input. The boundary uses owned prefix plus a space and plain word
continuations, matching controller splitting for these authored contexts.
3047 original-only rows omit model calls;2953 sets remain, including incomplete
sets useful only for suggestions. Cache identity binds those requests, native
executable and exact GGUF digest. The old failed prepared-candidate holdout is
untouched; this bridge has no holdout mode.

The native CLI was rebuilt against pinned sources. Exact model size/digest
verification passed; three real requests returned valid numeric scores with no
runtime errors. Full2953-set scoring was started in a resumable private build
cache. The archived three-response smoke snapshot and run-input identity prove
only that start, not completion or model quality. Only a matching complete cache
and `complete.json` may establish completion. Current model job state must be
queried live rather than inferred from this report.

No Android code/settings change, APK update, model publication, push, remote PR
or version bump occurred in this slice. Kotlin calibrated ranking/AutoReplace,
full correction Undo, contextual punctuation, final model-assisted holdout and
physical energy/full device release matrices remain required.

Evidence: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-03-deterministic-calibration/`.
