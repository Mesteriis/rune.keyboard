# Noun-case production integration

The separately qualified noun scorer now runs after the existing general and infinitive stages. It can revise an already admitted instrumental noun replacement to an accusative noun from the same complete bounded candidate pool, when all dictionary analyses and a positive packed lemma ID agree and preceding context provides an object cue. For example, `том показал мне фотографие` becomes `том показал мне фотографию`.

Every refusal retains the preceding result. This stage cannot acquire a replacement where the preceding engine kept the original, override a protected/correctly spelled word, revive a vetoed replacement, or write through a denied source admission. Its separate fingerprint binds all preceding assets, morphology, feature count, scope and frozen thresholds. Unavailable resources leave previous stages intact. The new source has independent admission checks both before selection and at the controller boundary, with explicit diagnostic reasons.

## Integrated controller evidence

The actual controller ran both the previous and new production modes on calibration, untouched holdout, broad and natural instrumental cohorts (40,136 observations total). All observations restored the exact pre-boundary text after Backspace, including unchanged controls; these are not all replacement Undo events.

| Cohort | Inputs per mode | Controls | Correct new revisions | Wrong revisions | Lost prior correct results | Changed controls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | 4,000 | 3,000 | 120 | 0 | 0 | 0 |
| Holdout | 4,000 | 3,000 | 171 | 0 | 0 | 0 |
| Broad | 12,000 | 6,000 | 0 | 0 | 0 | 0 |
| Natural instrumental | 68 | 51 | 0 | 0 | 0 | 0 |

All cohorts have zero prefix/input mutations, unexpected acquisitions, or baseline/new Undo failures. Broad and instrumental cohorts establish retention only; with no revisions they do not estimate new-source precision. Eight smoke cases also passed, including correct spelling, natural instrumental context, old infinitive correction, and source-admission refusal. Thresholds were frozen before holdout and device checks.

## Local checks

`./gradlew --max-workers=2 :app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug` passed: 1,121 JVM tests, zero failures/errors/skips, both APK builds and debug lint successful. The diagnostics/analyzer suite passed 54 Python tests. `python3 tools/verify-scoring-boundaries.py` and `git diff --check` passed. New tests exercise independent qualification/admission, refusal retention, bounded pools, resource failure, morphology and fingerprint drift.

Ignored evidence lives under `build/noun-case-integration-20261026/`; raw device material stays private and untracked. The packaged provenance records the evidence available at asset creation; this integration receipt records subsequent acceptance.

## Limits

This is a narrow noun-form revision, not general sentence correction. Known words remain protected. Cases requiring later words, such as `виновн` → `виновны`, and cases where the existing engine produces no admitted replacement remain separate work. No extra epoch or threshold retuning was performed from these evaluation results.

## Fold acceptance

The same-version debug update (0.4.2, code 8) was installed once with `adb install -r`, without data clearing or runtime permission grants. Both installed APK hashes matched the built artifacts and the previous/main/test signatures matched. All nine frozen contextual/infinitive/noun assets were verified before installation. Both coordinating phone chats confirmed an idle device and held their commands until Rune released the window.

Four explicitly selected physical instrumentation methods each passed once:

| Test | Phrases | Immediate exact Undo assertions |
| --- | ---: | ---: |
| New noun revisions, two input paces and following word | 18 | 12 |
| Existing infinitive revisions, two paces and following word | 18 | 10 |
| Existing contextual corrections, including `новй` | 20 | 16 |
| Repeated native input/first-letter forensics, two rounds | 8 | 4 |
| Total | 64 | 42 |

The forensic test received all 160 requested DOWN and 160 UP events in the requested sequence; no first-character loss occurred. Every method checked zero editor-payload reads across the six existing counter categories. Tests temporarily disabled synthetic learning feedback and restored the original settings in teardown.

Four bounded journal exports (eight stream files) were copied into private ignored artifacts and parsed successfully. The retained noun-test text stream contains five new-source boundary replacements plus editor acceptance events, proving the installed branch was used. Rotation means these bounded exports are not a complete count of all replacements; the physical assertions establish the phrase/Undo totals. Other tests' retained streams contain no noun-source replacements. Only exact task-created export directories were removed after verified local collection.

Fresh pre-install snapshots covered all shared-preference XML/backups and all four personal stores with their atomic `.bak`/`.new` variants. Immediate and delayed checks (32.0 seconds apart) found exact preference/settings equality, unchanged store presence/content, stable boot/user and the intended installed main APK. The local reservation was released only after all SDK commands terminated, and both coordinating chats were notified. No further phone command was issued.

[Machine-readable acceptance evidence](2026-10-27-noun-case-integration-evidence.json) records the aggregate outcomes without owner text, settings values, private identifiers or personal-data hashes.
