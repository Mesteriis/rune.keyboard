# Q7: editor-consistent historical local diagnostic

The pending morphology-admission patch was tested on a real 12,000-row replay.
Its old evaluator reported `releaseApproved=true` using the lexical decision
label, without checking the editor text it read, input identity beyond row ID,
actual Undo snapshots or the correction's edit range. Five controlled corruptions
of a genuine RU holdout observation still received that old approval: wrong
editor text, foreign typed input, a truthy string instead of the Undo boolean,
a contradictory admission refusal and a wrong UTF-16 edit offset.

The evaluator now refuses each of those contradictions. It validates row/input
identity, snapshot shapes/positions, strict boolean flags against actual text,
admission records and the UTF-16 replacement against the before/after snapshots.
Correct credit requires the entire expected editor text. Undo compares text,
caret and composing range. Existing morphology evidence and legitimate
`ORIGINAL_VALID` veto reporting remain required; the 99%/300-family thresholds
are unchanged.

## Actual outcome

A fresh final 12,000-row replay completed and returned **exit 1 for the historical
quality gate**, with a complete schema-2 report. This is an expected diagnostic
refusal, not a successful qualification. All observations passed structural
validation. The before/after runtime projections match on all 12,000 rows,
excluding only top-level `fullTokenGenerationNanos` and `hostStageNanos`.
No product behavior or asset changed.

The old holdout credit was 360/360 RU and 341/342 ES. Exact editor credit is
357/360 RU (99.17%) and 334/342 ES (97.66%). Three RU and seven ES rows have the
correct target suffix but a prefix changed during typing; these extra failures
describe full editor/context divergence. They do not identify seven new Spanish
target-word ranking errors. `typingChanges` and `editorMismatchChanges` make
that distinction explicit. The ES historical gate fails its existing threshold.

`historicalHoldoutGatePassed` now controls diagnostic exit status. The legacy
`releaseApproved` field is retained as false, alongside `productionQualified=false`
and `newUnseenHoldout=false`. Revealed v2 diagnostics cannot newly approve a
release. No policy constants or packaged qualification were updated.

The final run binds 183 source/input/toolchain files, including all 69 packaged
asset files, before compilation and rechecks them after execution. Asset-set
drift and undeclared JVM options are refused. The report retains raw-file hashes,
the original freeze and the full JDK inventory. Local reports contain local
toolchain paths; the public receipt retains sanitized roles/hashes.

All six focused tests pass. The final pipeline suite ran 125 tests: 124 pass and
one existing conditional Kotlin-ready test skips because `FINAL_REPLAY_EXPORT`
was not supplied. That case is not claimed as passed. CI already discovers this
pipeline suite. Five corruption probes were repeated against the final evaluator
and all fail closed. The original two related owner files are backed up byte for
byte; their admission work was extended for this fix. The other 11 original owner
payloads and all 98 original paths are preserved. Corpus and ledger are unchanged.

See the [machine receipt](2026-10-28-q7-local-editor-gate-evidence.json). No new
training, device operation, APK, push or hosted workflow execution occurred.
Fresh Q6 qualification, actual hosted Q7 execution and the remaining review
requirements stay open.
