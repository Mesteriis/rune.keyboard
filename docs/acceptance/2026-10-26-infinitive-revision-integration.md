# Learned infinitive revision: controller integration and Fold acceptance

On 2026-10-26 the [offline-qualified secondary model](2026-10-26-infinitive-revision-offline.md)
was connected to the production controller and checked on a physical Fold 7.
The [machine-readable receipt](2026-10-26-infinitive-revision-integration-evidence.json)
binds model, policy, APK, checks and evidence hashes. This follows the
[Kotlin scorer/scope milestone](2026-10-26-infinitive-revision-android-core.md).

## Behavior and bounds

The unchanged contextual model first selects its usual replacement. A second
frozen model may revise an unknown spelling's already selected finite verb into
an infinitive. It requires a complete candidate pool containing the old choice,
a preceding infinitive cue, unambiguous dictionary parts of speech, matching
non-null packed morphology lemma IDs, frozen score/margin thresholds and its
own independent automatic admission. An explicit old veto is retained. Correct,
protected and rare original words remain protected. Every secondary refusal
retains the old decision. No editor read or new network operation was added.

Examples checked through actual typing:

- `том начал немного злищься → том начал немного злиться`.
- `тебе надо научищься → тебе надо научиться`.
- `я не могу тебе заплатищь → я не могу тебе заплатить`.
- `ты научищься → ты научишься` without an infinitive cue.
- Correctly spelled `тебе надо научишься` stays unchanged, despite its grammar.
- `нужен новй → нужен новый` retains the previous result.

The policy/model hashes and 146-feature schema are separately qualified,
including the unchanged reference model, shared context tables and packed
morphology. Missing secondary resources leave the previous engine usable.
`INFINITIVE_REVISION` is an appended diagnostic source. Ranking emits explicit
scope, score, margin, resource and admission refusals without word payloads;
boundary events identify the applied source. Existing enum ordinals remain stable.
The analyzer accepts this source, all new refusal reasons and existing schema-8
correction/Undo identities without inventing editor text from metadata.

## Actual controller comparison

Both modes ran the real `TypingSessionController` with the packaged assets.
`contextual-production` is the baseline; `infinitive-revision-production` adds
only this revision stage. These are host-harness modes, not user settings.

| Partition | Inputs per mode | New correct replacements | New wrong replacements | Losses of previous correct results | Changed controls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Focused calibration | 2,000 | 179 | 0 | 0 | 0 / 1,500 |
| Focused holdout | 2,000 | 157 | 0 | 0 | 0 / 1,500 |
| Separate broad holdout | 12,000 | 1 | 0 | 0 | 0 / 6,000 |

All 32,000 observations completed; immediate Undo restored the exact text before
the boundary in every observation. This includes unchanged-input cases and does
not mean that all 32,000 observations contained a correction.

Offline projection had 180/158 focused gains. The two extra projected changes
were inspected with a separately compiled observer retaining a bounded history
of completed and incomplete evaluations. In both completed evaluations the
runtime refusal was `INSUFFICIENT_MARGIN`. No threshold was lowered. A precise
floating-point explanation was not established. Application source hashes match
the bulk run; only observer diagnostics were subsequently expanded.

The first comparison gate failed because it rejected any capitalization while
typing. Four calibration and four broad inputs already undergo the same initial
capitalization in the baseline and revision. The corrected invariant compares
the actual pre-boundary input and prefix against the baseline: zero additional
changes. Original failing artifacts were retained; no row was removed or relabeled.
This also corrects the earlier core evidence's explanation of its 499 scored
calibration groups: one typo row was excluded after capitalization, not because
its candidate pool was incomplete.

## Physical acceptance and state retention

The following three explicit instrumentation methods passed once each, using
Rune's own QA field, physical key touches and two inter-key pauses (50/100 ms):

- `learnedInfinitiveRevisionsPreserveExactUndoAtTwoPaces`: 18 phrases,
  including following-word continuity, and 10 exact immediate Undo assertions.
- `learnedContextualCorrectionsAtTwoPacesPreserveExactUndo`: 20 regression
  phrases and 16 exact immediate Undo assertions.
- `repeatedRealTouchInputAndUndoKeepTheRequestedCharacters`, two rounds:
  eight phrases and four exact immediate Undo assertions. Native DOWN and UP
  receivers matched every requested character: 160 DOWN/UP pairs.

Total: 46 phrases, 30 exact immediate Undo assertions. Every method's assertions
also checked that editor-payload read counters remained zero. These are synthetic
physical-device tests, not a human typing study or a 95% guarantee on future text.

A fresh pre-install snapshot verified hashes of all existing preference XML files
and explicitly checked four known no-backup learning/control stores and their
`.bak`/`.new` variants. All four stores were absent before testing; their absence
was checked again afterwards. The verified archive, settings and raw diagnostics
remain private, ignored build artifacts. No historical backup was restored.
Immediate and delayed comparisons matched every tracked file and presence state,
the three IME settings, Android user and boot identity. Both installed APK byte
hashes and signing identity were verified. Update used `install -r`; no data clear,
uninstall or permission grant was used. The debug version remains 0.4.2/code 8.

The initial read-only screen preflight expected fields absent on this OEM build;
keyguard plus power/display checks confirmed an awake, unlocked device with an
ON panel. Initial read-only snapshot commands exposed shell quoting and
`exec-out` exit-status limitations. The snapshot was completed using discrete
`shell run-as` presence/hash commands and verified tar contents before any update.
No unlock, consent, permission or session recovery was performed.

Each test exported its bounded journal before teardown. The three text-stream exports
were processed successfully by the diagnostic analyzer; metadata contains the
new source and its precise acceptance/refusal reasons. Only those exact
newly-created cache exports were collected and removed. Local reservation was
released after SDK commands finished, and both other Fold chats were notified.

## Checks and remaining work

`./gradlew --max-workers=2 :app:testDebugUnitTest :app:assembleDebug
:app:assembleDebugAndroidTest :app:lintDebug` passed: 1,107 JVM tests,
zero failures/errors/skips; both APKs assembled; debug lint passed.
`PYTHONPATH=tools python3 -m unittest test_typing_diagnostics_analyzer
 test_typing_diagnostics_boundary` passed all 54 tests, including the final
`UNCHANGED` refusal addition. `python3 tools/verify-scoring-boundaries.py` and
`git diff --check` passed. No production source changed after these build checks.

This narrow revision does not solve `фотографие`, general agreement correction,
or `виновн` cases requiring a following subject/right context. Those need their
own data, independent qualification and controller/device checks.
