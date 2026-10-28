# Contextual «новй» and visible correction order

> Historical material from 2026-10-26. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

The owner requested autonomous phrase typing, remaining ranking fixes, coordination with AURA and installation on the physical Fold. AURA explicitly released the device before Rune's device calls. Tests use authored public phrases and real touchscreen events; they never ask the owner to type or replace the field with expected text.

## Shipped scope

`WordContextPolicy` V3 contains two finite reviewed exceptions. Lower-case `новй` becomes `новый` only when the complete preceding whitespace-delimited token case-folds to `нужен`. Lower-case `завтро` becomes `завтра` only after `встретимся`. Thus `нужен новй` and `мне нужен новй` are supported. There is no unconditional `новй` mapping. `с новй`, `о новй`, `для новй`, missing context, punctuation, identifiers, mixed scripts and upper-case originals do not match this source. The continuation can require a different grammatical ending.

The rules supplement an actual abstention, preserving previously applied winners. A raw legacy proposal that the joint policy explicitly vetoed does not block the reviewed source. The rule selects the exact same-request candidate from a complete bounded pool; it never invents or inserts an unverified target. Source qualification pins the exact rule identity, search version and public dictionaries. Morphology membership, valid/rare original protection, private word protection/rejection, request ownership, editor mode, deadlines, explicit Original and exact Undo remain separate gates. This is finite authored coverage, not a statistical precision qualification.

When a qualified Space replacement is available with autocorrection enabled, it leads the displayed corrections. The prior manual ranking could put a different word ahead of the automatic winner. Suggestions-only mode retains the manual order, and shadow comparison still evaluates the raw manual preference. This changes presentation rather than the frozen statistical model or its thresholds.

The diagnostics vocabulary appends `WORD_CONTEXT`. Its ranking decision/refusal preserves the original request identity and contains no text. Successful boundaries identify the same source. The debug schema remains 8; text collection still requires existing separate consent.

## Fast phrase miss identified on the phone

The first 100 ms phrase pass retained `давай встретимся завтро`. Native diagnostics show the exact target `завтра` was already in the complete local candidates. The joint path refused it as `WINNER_AMBIGUOUS`, the rescue path refused `INSUFFICIENT_MARGIN`, and the old model request missed its permitted deadline after Space. Thus this was not a missing dictionary word. The additional finite meeting-context rule avoids that slow fallback for this exact reviewed pair; deadlines and statistical admission thresholds remain unchanged. The unsuccessful fast pass is retained rather than replaced by a slower passing run.

## Rejected generalization

A broader public word-bigram source was tried and rejected before deployment. It used a frozen 500,000-pair table derived from public Russian Wikipedia, complete original-plus-rival comparison, existing model support and a single internal insertion/deletion. Product-path calibration added 104 correct corrections and zero wrong ones, but two predeclared independent validation folds added 186 correct and **5 wrong** corrections: **97.3822%** precision over additions, below the frozen 99% gate. Each fold also fell below 99%. No old correct answers, controls, prefixes or exact Undo results were lost; that does not rescue the failed precision gate.

The failed model SHA-256 is `b5a9b64c1ddcfb42e4042b325b22c7c3d594d7cda282ec3fc99a2330e341d053`; frozen failed policy SHA-256 is `a816ff2a149770caa4c23afc039ac842ece58e0859bb383f6336c45a52b3da52`. Neither model nor policy is packaged, and its decoder/runtime integration was removed. No parameters were adjusted against the revealed validation errors to qualify this source. Failed attempts and raw public observations remain under ignored `build/context-ranking-20261025/`. Future generalization requires a new independently frozen validation set.

## Local validation

- `:app:testDebugUnitTest`: 1,076 tests, zero failures/errors/skips. New coverage checks finite context boundaries, unsupported spellings, incomplete/missing/malformed candidates, independent source qualification/admission, displayed winner, exact Undo and metadata request identity.
- `:app:assembleDebug`, `:app:assembleDebugAndroidTest`, `:app:lintDebug`: passed. Final diagnostic test changes were followed by another successful JVM/lint run.
- Diagnostics Python: 64 tests passed, including the appended source; debug/release/profile packaging checks passed. `tools/verify-scoring-boundaries.py` passed.
- Production Kotlin replay: 4,788 prior public rows plus two additional frozen public sets of 3,648 and 3,576 rows. Boundary documents and exact Backspace documents are unchanged across all 12,012 rows. This is regression parity, not a claim that every preexisting answer was correct.
- Fourteen authored production replay probes passed, including corrected `нужен новй`, abstention outside that context, correct forms and exact Undo. Labels stay outside the Kotlin observer.

## Physical reproduction

After installing matching debug app/test APKs on the explicitly selected Fold, run AndroidJUnitRunner with `class=io.github.mesteriis.rune.keyboard.qa.FoldAutocorrectionInstrumentedTest#contextualInternalEditsKeepWordFormsAndExactUndoAtTwoPaces`, `allowPhysicalDevice=true`, `runeFailureArtifacts=false`. It checks three typo phrases and three correct-form controls at requested 50/100 ms pauses. The 15-phrase probe also injects touch down/up events using fresh per-phrase key bounds, at requested 100 ms pauses; expected text never drives input. Run the existing nine assertion tests separately. The 15-phrase characterization uses `probePhrasesThroughRealTouchInput` with offsets 0, 3, 6, 9, 12 and count 3; inspect every `matched` result as well as instrumentation status.

Preserve owner preferences, four personal stores and existing diagnostic journals before the run. Synthetic learning, touch adaptation and example collection are isolated only within tests and settings are restored afterward. Check all editor payload read counters. Coordinate the entire device window with AURA; hand it back only after installation, hash/state checks and final log collection. Private journals remain in ignored mode-0700 `build/fold-context-20261026/`, with archives mode 0600.

## Device contention evidence

A later focused run captured `foreground=dev.androidmcp.app` while the Rune field became unavailable. That proves this particular run lost the intended application surface. AURA confirmed it had not resumed phone commands. The earlier missing-node failures lacked foreground evidence, so they are not all attributed to AURA or to the same cause. Fast touch tests now check the intended Rune package before each gesture and stop on a foreground switch. Teardown restores settings but does not press Home over a foreign foreground app. The fast guard reads the active root package directly: the UiAutomator package helper calls `waitForIdle` and was measured to slow each key, so its earlier slower 12/12 run is excluded from speed claims. Queue coordination remains required; the guard is not a device lock.

## Physical results and installation

- New contextual rules/controls: 12/12 authored cases at requested 50/100 ms pauses. All six typo cases restored the exact original on Backspace; six correct-form controls stayed unchanged.
- Full 15-phrase touch characterization: 15/15 exact matches at requested 100 ms pauses, including `нужен новй пароль → нужен новый пароль`; three correct control phrases stayed unchanged. This is authored characterization, not an independent accuracy estimate.
- The earlier full assertion run was **7/9**, with two failures: an unavailable QA counter node after keyboard reshow, and an unavailable QA editor node during the final rescue assertion. The journal still recorded all six letters in each of the three diagnostic phases. These failed runs are retained.
- The first targeted two-test repeat passed the rescue test (all four correction/Undo cases), but diagnostic setup failed because the Space node was unavailable. The earlier missing-node failures did not record their foreground package. The driver now waits for description-based keys before dispatch, matching its character-key lookup; it never retries a gesture already sent. QA counter lookup also waits for visibility. The final diagnostic repeat passed 1/1 with all three six-letter phases and zero editor-payload reads. The final exclusive-device assertion run subsequently passed **9/9**, including the diagnostic and rescue tests. Earlier failed attempts remain recorded.
- Native text diagnostics confirm the new `WORD_CONTEXT` automatic boundary with `modelUsed=false`. All completed counter assertions remained zero. Tests retain the original diagnostic consent rather than enabling collection.
- The checked app was reinstalled with `install -r` after physical acceptance. Installed and built APK hashes match: `865b1028828a92ac17bb762adbefee2f7e3a6a284e50e6239955fc35c1c9e19c`.
- Owner preferences and four personal stores match their pre-run fingerprints. Rune explicitly enabled and selected after test teardown. The device window was returned to AURA after all device commands.

[Aggregate evidence](2026-10-26-contextual-novy-evidence.json). Failed attempts, private journals and installation/state receipts remain ignored under `build/fold-context-20261026/`; no private journal text or store fingerprints are published.
