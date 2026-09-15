# Mobile typing experiments acceptance — 2026-09-15

## Scope
Three approved directions implemented: exported CatBoost candidate ranking, compact character neural context model, conservative dynamic physical tap resolver. Four persisted switches (including separate apply control), default false, included in atomic disable-all (17 extras). RU only; resources loaded off-thread and hash checked. Existing automatic admission and original candidate remain authoritative. No private chat data in public models/APK.

## Behavior
Manual alternatives receive trained ranking and independently optional context scores. Context is acknowledged Rune-owned text; no surrounding editor read. The touch experiment defaults to shadow. Applied mode affects eligible short single-pointer edge taps only. Center, deletion recovery, stale stamps, invalid geometry/probabilities, unsupported language, nonletters, sensitive fields, accessibility and alternate/longpress paths retain ordinary behavior. Remapped samples cannot teach touch calibration. Context priors cache is bounded by session/revision and invalidated at ownership/geometry boundaries.

Schema6 appends four fixed feature flags and three content-free TAP decision reasons. Analyzer retains compatibility with schemas1–5 and reports decision counts separately from editor outcomes. Release diagnostics remain no-op; source and packaging inventories remain strict.

## Model evidence
Source training/holdout: 1700 public rows per split after protected-row filtering. Public Wikipedia corpus; models contain no private messages. On 926 held-out synthetic spelling rows with alternatives: generator-first500, CatBoost680, fixed CatBoost+context686 correct top1. Context alone303, so its independent use is explicitly experimental and joint use recommended. Missing expected alternatives count as failures. These are neither real-chat nor full-autocorrection quality figures. Character model 24-character input,24 hidden units; CatBoost80 depth4 trees. Numeric assets89604bytes combined. Full training reproduction and hashes are documented in tools/typing_experiments/README.md and asset provenance.json.

## Verification
- Full Gradle invocation: `:app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:imeIntelligenceBoundary :app:forbiddenRuntimeDependencies :app:privacyGateRelease :app:connectedDebugAndroidTest` with scoped instrumentation classes; exit0, BUILD SUCCESSFUL58s.
- JVM:949 tests,0 failures/errors/skips.
- Android API37 owned emulator:30 tests,0 failures/errors/skips. Existing controls/tools/strip/profile IME tests plus ExperimentIntegrationInstrumentedTest, DynamicTouchInstrumentedTest and PhysicalTouchInstrumentedTest.
- Host model tests:3 passed; exported CatBoost versus framework parity5699 feature vectors, maximum raw error5.32e-8; Kotlin/Python context/ranker/letter parity included.
- Diagnostic analyzer/source-boundary/packaging Python tests:57 passed.
- Debug/release pre-R8 and DEX diagnostics packaging inventories passed. No new runtime dependency or network permission.
- Additional one-class Android inference run passed to retain numeric warmed timings. Measurements are emulator-only, per-candidate/per-prediction, not real-device key-to-screen latency or energy.

Ignored raw evidence: build/typing-experiments/full-validation.log, diagnostics-python.log, host-tests.log, kotlin-tests-final.log, training-final.log, latency-instrumentation.log and emulator-latency.json. Public models/provenance/tests are tracked; machine-local logs and private artifacts remain ignored.

## Reviews and remaining limits
Task1 model spec/quality review passed (corrected report row count); Task2 tap spec/quality review passed. Whole integration review and final packaging tracked in the implementation ledger. No actual user's phone was changed. No claim of real-world touch accuracy, general grammar understanding or production qualification. Physical-device battery and sustained typing performance remain unmeasured.
