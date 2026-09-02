# Smart Typing 0.3 — PR6 live suggestions checkpoint

Date: 2026-09-02. Source base: `c45f43ae6f84ac27d84e68eb8c10fea40a385dbe`, followed by the reviewed, locally integrated controller, lazy-loader and service changes described here. This records pre-commit integrated evidence; fresh post-commit JVM results must be recorded separately. Version remains 0.2.0.

## Delivered scope

Eligible NORMAL text input can show the typed Original plus up to two explicit spelling alternatives. A correction tap replaces only the current Rune-owned composing word, preserving its leading boundary; Original can explicitly restore the source spelling. Space keeps the typed or explicitly selected text. There is no automatic spelling replacement or model inference from the IME, no new editor readback, and no ranking-confidence threshold.

One serial loader validates requested public dictionary languages off main and publishes readiness without a completion callback. The whole approved primary/fallback route must be ready before the one candidate worker runs. Loading retains enum demand only; it cannot submit an old word when it completes. While unavailable, the eligible composing word remains Original-only until a later accepted edit. Render, Shift/caps refresh and load completion do not start candidate work.

Requests follow accepted composing revisions and use the existing bounded generator. Session/revision/request ownership, current word/language/route readiness, view/layer/selection and editor policy are checked before accepting a reply. Boundary, selection, language, privacy and lifecycle changes cancel obsolete work. Passwords, NO_PERSONALIZED_LEARNING, raw and other unsupported fields do not submit. Candidate updates bind the permanent strip without rebuilding keys. Explicit selection uses the existing controller/editor transaction with no fallback replay or parallel Undo storage.

The three separately reviewed source proposals are controller `321b0162b1a00461798fddf925aa83d27e29ab916b7f283a96ad040170e80ba1` (including the case-preservation correction), loader `01b26847868d0ec42f160274831a7e8486a21184394e0ae4b0a5563e1b5dac0d`, and service/coordinator `f64631b40e81b36992c9794801888783355cca7102a39f92dc389041c10a32d6`. The independent [packaged-asset checkpoint](2026-09-02-smart-typing-0.3-pr06-packaged-assets.md) remains the source of dictionary/APK-mapping evidence; its prior Fold PASS does not qualify this new live UI.

## Observed gates

| Check | Result |
|---|---|
| Fresh integrated JVM | PASS 453/453: app 434 + runtime 19; zero failures/errors/skips; 46/46 Gradle tasks executed |
| Initial integrated lint/build/debug/release/profile/privacy/dependency/native gates | PASS: 298 tasks, 53 executed, 245 up-to-date |
| Final gates after test-only failure-capture opt-out | PASS: 298 tasks, 21 executed, 277 up-to-date |
| API26 live Binder scenarios | PASS 3/3, 50.620 s |
| API26 existing Original-tap regression | PASS 1/1, 7.447 s |
| API37 live Binder scenarios | PASS 3/3, 54.061 s |
| API37 existing Original-tap regression | PASS 1/1, 11.255 s |
| Physical Fold live Binder scenarios | PASS 3/3, 31.838 s; both install-r operations succeeded |
| Full IME lifecycle/configuration/Fold regression, weighted quality, duty/energy and release qualification | Not closed |
| New remote CI or model publication | Not performed |

The three new Binder scenarios check explicit correction and whole Original restoration with composing/commit counts and zero values for the six checked readback counters (`before`, `after`, `selected`, `extracted`, `surrounding`, `snapshot`); Space retaining the typed original and clearing old candidates; and switching to the NPL fixture, clearing suggestions and keeping plain input. The fixed public example is `helllo` → `hello`. The bounded readiness wait repeats explicit eligible edits because loading alone intentionally does not generate. These are functional test durations, not candidate latency distributions, cold-cache budgets, quality scores or energy measurements.

Evidence is saved under `tools/lexicon/smart-typing-0.3/results/2026-09-02-live-candidates/`: content-free test/build logs, numeric summary and current source hashes. Instrumentation logs do not contain per-device installed-APK readback or hardware identity proof; this checkpoint does not add those claims. The final build's test-only capture guard is distinguished from the earlier functional runs; it does not change candidate/controller production behavior.

## Physical capture boundary and remaining work

The reviewed test-only patch `00a89715511b6b0be39f5a3ad91952064f7e947d3c9010374fec4c8aaee9028c` adds the exact instrumentation argument `-e runeFailureArtifacts false`. Physical UI runs must pass it to suppress automatic failure screenshots and hierarchy dumps, including setup failures that might leave a lock screen or notification visible. Test assertions and unconditional TestWatcher.finished teardown are unchanged. CI keeps its existing capture behavior when the argument is absent. This switch covers only that failure watcher, not unrelated explicit screenshot operations.

The first physical attempt was blocked before wake/install because USB listed no device. No live test began, no new live APK was installed and no screenshot/hierarchy was captured during that attempt; it was not a failed test. The user then reconnected the device and the parent confirmed USB ready before wake/install. Both install-r operations succeeded, and the three live Binder scenarios passed in 31.838 s with `runeFailureArtifacts=false`; no screenshot/hierarchy was captured. The latest live APK is now installed on Fold. This is the scoped live UI result, separate from the earlier packaged-reader Fold checkpoint.

The physical result covers those three scenarios only. Cover/inner transitions, broader composing/privacy/selection/configuration lifecycle and controlled performance measurements remain separate gates. Current packed-reader completeness and bounded generator tests do not close weighted development/holdout quality, useful completion rate, model confidence, duty or energy acceptance. IME model invocation and automatic spelling replacement remain off; PR6 and overall Smart Typing 0.3 are incomplete.
