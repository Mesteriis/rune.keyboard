# Following-context acquisition and first-action calibration

This experiment extends offline evaluation to unknown words that the installed
controller leaves unchanged. It does not enable a model in the Android app.
The previously installed APK and all production assets remain unchanged.

`RightContextSourceScope` requires a complete actual retrieved pool, comparison
against the raw original and every retrieved alternative, dictionary protection
for the original, independent public source certificates, a known target lemma,
and an unambiguous short-adjective reading supported by completed right context.
Existing joint-source admission remains unchanged. The replay observer exports
facts from the same public original guard and packed morphology used by the
current engine. Its 1,600-row noninterference audit found no changes to existing
semantic fields; the new certificate field contains 5,514 candidate entries.

`previous_word_evidence` validates exact public replay snapshots against private
session state. It uses UTF-16 offsets and permits an unchanged leading boundary
such as comma/space in the original correction root. It does not normalize input
drift, fabricate an edit for an unchanged word, or certify future runtime editor
ownership. Tests cover emoji offsets, punctuation, stale roots, first-letter
loss and session/context divergence.

## Full suffix is insufficient evidence

The frozen third experimental model, SHA256
`170205268883a58d9a7968391b9ccf7aa753b838d3176287c4a73a63ae8af808`,
was scored against the same 1,600-row matched calibration set. Using the complete
source suffix gave a candidate policy with 137 new correct changes and zero new
wrong changes. This is not a runtime-quality result: later words may conceal an
earlier wrong replacement.

The timeline evaluator instead presents the earliest actual boundary of each
completed following word, within the existing 128-character/eight-word bounds.
It evaluates the first source-certified proposal crossing the policy thresholds.
Later proposals cannot repair or overwrite an already accepted action, and a
source word contributes at most one gain. It never inserts a delimiter to make
an unfinished word available.

Applying the full-suffix policy to that timeline exposes one wrong change:
`живм` becomes masculine `жив` after ` будет `, while the printed source form is
feminine `жива`. That policy produces 147 correct and one wrong first action.
A new timeline-calibrated candidate raises the minimum margin from
0.4167522193786286 to 0.43703741385116235, retaining the minimum score
0.5799239253194995. It yields 123 new correct changes, zero wrong changes,
zero control changes and zero previously-correct losses in matched calibration.
Of these, 90 acquire a previously unchanged original and 33 revise an existing
replacement; 106 occur after the first completed following word and 17 after
the second. These remain calibration results, not independent validation.

## Independent side cohorts

A finite scan of seven already-local public Wikipedia shards completed over
648,354 articles. Selection used dictionary forms and fixed corruption rules,
without querying the experimental model. Previously bound articles and training
families were excluded; calibration and holdout families remain separate.

The frozen side corpus has 6,050 calibration rows over 1,290 contexts and 5,810
holdout rows over 1,242 contexts. It includes other-part-of-speech contrasts,
agreement-role negatives, direct-subject positives, correct/protected originals,
and unfinished-right-word controls that must retain the observed baseline.
The cap of 20 contexts per family applies within each group and split; it is not
a global family cap. Priority sampling and synthetic corruptions do not estimate
the prevalence of errors in personal typing. Printed-source agreement negatives
can also contain source-language errors and need explicit analysis if they fail.

The current controller replayed all 6,050 side calibration rows. The unchanged
first-action candidate policy gave two new correct changes, zero wrong changes,
zero control changes and zero previously-correct losses. Both calibration gates
therefore passed before the model/thresholds/protocol were frozen for holdout.

## Frozen holdout result: rejected

The first experimental scoring of the 7,410 holdout rows used the unchanged
model, scope and thresholds, with no holdout refitting:

| Holdout cohort | Rows | New correct | New wrong | Correct/control losses |
| --- | ---: | ---: | ---: | ---: |
| Matched following-copula | 1,600 | 114 | 2 | 0 |
| Independent side cohorts | 5,810 | 2 | 4 | 0 |

Overall precision over changed words is 116/122 (95.08%), above the user's
95% floor. That aggregate hides side-cohort precision of 2/6 (33.33%), and the
predeclared zero-new-wrong qualification requirement fails. The policy is
**rejected for production activation**. Thresholds and source labels were not
changed after seeing the holdout. These holdouts are now disclosed/consumed;
future changes require a new independent frozen holdout.

All four side errors choose plural `аналогичны` after `модели`, `концепции` or
`технологии`. These words have possible plural-nominative analyses, but in the
source they are singular complements of `аналогичен/аналогична`. A dictionary
nominative reading alone does not prove that the following word is the subject.
The old engine had produced `аналогично`; these changes are new wrong revisions,
not losses of previously correct outputs.

One matched error changes `невредимп` to masculine `невредим` before `будешь`
when the source is feminine `невредима`. A singular future copula supplies number
but no gender; the model still defaults to masculine despite feminine evidence
in the preceding clause. The other exposes a corpus-label defect: the original
public shard says `Державцем (комендантом) Остра был Филон Кмита`. The collector
lowercased the place-name form `Остра` and treated it as short adjective `остра`.
The exact original shard text was inspected after scoring. This row remains in
the recorded failure counts; neither it nor any other error was removed to pass
the gate. New corpus generation must preserve surface case and audit proper-name
homographs before freezing labels.

The [evidence receipt](2026-10-27-right-context-acquisition-evidence.json) binds
model/policy, source modules, calibration and holdout records, errors and checks.
Next work is case-role ambiguity and singular-gender evidence/training, followed
by fresh independent qualification, before runtime integration.

## Verification and activation limits

63 focused Python tests pass. The Kotlin observer compiled and passed the
1,600-row semantic noninterference audit. No application build or phone test is
claimed for this offline milestone. Public synthetic replay has no personal veto
data. Runtime vetoes, actual multiword ownership, scorer parity, cancellation,
exact Undo and preservation of following text still need qualification before
activation. The holdout is not used for threshold fitting.

Artifacts: `build/right-context-acquisition[-v2]-20261027/`,
`build/right-context-timeline-20261027/`,
`build/right-context-side-20261027/`, and
`build/right-context-side-timeline-20261027/`.
