# Rune Smart Typing 0.3 execution ledger

Baseline: b5400cbadadd29e8ee915a0fb33fb11ec5bebc79. Binding requirements: `2026-09-02-smart-typing-spec.txt` and the user-approved implementation plan in this task.

## Accepted refinements

- Holdout requires at least 300 automatic replacements per language as well as precision >=99% and correct/protected false-change <=0.5%; report coverage and Wilson intervals.
- Explicit sentence-boundary suggestions may capitalize only the initial letter of the current word.
- No new editor reads to diagnose unsupported composing; never blindly replay unacknowledged text.
- Implement cancellation inside the pinned tokenizer using a reproducible patch, not only before/after tokenization.
- Preserve upstream gitlink; record upstream and patch digests independently.

## Execution

### Resumed full implementation

The user explicitly resumed the full objective after PR1 and authorized changing
the model when needed, with on-device latency, memory and battery constraints.
The earlier stop applies to qualifying Rune Text 0.1, not to abandoning the
remaining product implementation. Historical PR1 evidence remains immutable.

Ruling: build the independent PR4 composing/privacy foundation first, then
candidate strip/Undo, deterministic lexicons and mechanical punctuation while
qualifying a resource-bounded model path. Preserve all quality/privacy gates;
do not treat switching models as permission to weaken them. Model execution
must be demand-driven, cancellable, and absent in sensitive/ineligible sessions.

Current slice: `feature/smart-typing-03-pr05-strip-undo`, based on PR4
`ffe8e3932449da9a7d2c2a8cf6f5554535c3e511`. PR4 implementation is complete with
local JVM/build gates and API36 Binder evidence; API26/37 and physical Fold
remain unqualified. PR2/3/5/6/7/8/9/10 remain required. No push, remote PR or
publication is authorized by this resume.

### PR4 local evidence

- Separate typing controller, leading-boundary composition, bounded RAM-only context,
  ownership invalidation and explicit cursor-mode-start are integrated through the existing executor.
- NPL/password/raw paths prohibit composing; NPL Caps/double-space read bug fixed.
- Independent review caught a legacy double-space callback clearing Undo. A known numeric +1 acknowledgement bridge preserves it until PR5 migration; fix re-reviewed and Binder-tested.
- Fresh JVM: 272/272 PASS (266 app + 6 runtime), no failures/errors/skips. Required post-commit rerun after `ffe8e3932449da9a7d2c2a8cf6f5554535c3e511` also PASS (44 tasks executed).
- Full prescribed lint/build/privacy/dependency/native command PASS, including Android test APK assembly.
- API36: full 43-test app run PASS; extra stationary Space hold regression PASS separately, 44 unique tests. This does not close API26/37 or Fold.
- Same-session rewrite fixture now mutates Editable and asserts no new InputConnection; earlier failed setText-based fixture is not treated as product root-cause proof.
- Official API26 ARM64 and API37 16KiB ARM64 images are downloading for later local checks. No physical device connected at initial inventory; no wireless ADB used.
- Acceptance: `docs/acceptance/2026-09-02-smart-typing-0.3-pr04.md`.
- Ruling: API36 is diagnostic evidence only; retain separate API26/API37/remote CI/Fold/energy status and app version 0.2.0.

### PR5 in progress

- First commit migrates double-space and Undo from KeyboardState into the typing owner. Only Rune-owned pending boundary/context may be transformed; unowned/unsupported text gets plain Space. The executor's legacy surrounding-text conversion/revert path is removed.
- Ruling: preserve the existing double-space gesture's priority, but remove its ability to edit unowned editor text. This matches the 0.3 ownership/privacy contract; no additional editor reads are introduced.
- Candidate strip is integrated after the migration commit: permanent three cells and keys container, current-word Original consumer, session/revision IDs and explicit Original choice without editor writes. Corrections/punctuation remain later consumers.
- PR2 tokenizer patch prototype passed host stage cancellation, 632 exact original/new token-sequence comparisons, and independent review. It remains unapplied to production until the native runtime slice.
- Undo migration verification: fresh JVM 281/281 (275 app + 6 runtime), no failures/errors/skips; full required gates PASS (292 tasks, 51 executed); all 13 composing Binder scenarios PASS on API36 in 119.440 s, including the ineligible double-space fallback and zero surrounding reads for conversion/Undo. Independent review approved with no P1/P2; stale privacy comment corrected.
- This migration is committed separately before strip integration. Autocorrection and mechanical-punctuation consumers are later slices; no placeholder edit subclasses or Undo stack are introduced.
- Migration commit: `e22fdbd4fed9687baa00ee99996ff1e3194f584b`; fresh post-commit JVM 281/281 PASS.
- Strip verification: fresh JVM 292/292 (286 app + 6 runtime); full prescribed gates PASS. API36 full suite initially 56/57 PASS in 492.582 s, with one unattached accessibility fixture failure. The fixture now attaches through ActivityScenario, preserving every assertion; all 10 component tests PASS in 6.881 s. Together 57 unique scenarios passed, including Original tap and sensitive editor transition through Binder. Independent integration and scoped fixture reviews approved.
- Ruling: retain the failed initial log and distinguish combined unique-test coverage from a fresh complete rerun. API36 remains diagnostic and does not close API26/API37/Fold.
- Official API37 ARM64 16 KiB image installed and a dedicated AVD created; API26 download continues. New local device evidence will be recorded separately.
- Acceptance checkpoint: `docs/acceptance/2026-09-02-smart-typing-0.3-pr05.md`. Full-word autocorrection Undo still needs its later consumer and end-to-end test; only current owned-boundary Undo is qualified here.

### Historical PR1 result

- PR 1 implementation and full evaluation complete: suitability **FAIL**. This ledger and the dated acceptance/evidence files are included in the closing evidence commit; the required post-commit JVM result is reported with its exact SHA in the task's final response.
- Ordered sequence stops before model-dependent PR 2 runtime API/tokenizer patch. PR 3 service, PR 4 composing, PR 5 strip/Undo, PR 6 lexicons, PR 7 model ranker, PR 8 mechanical punctuation, PR 9 contextual punctuation and PR 10 release hardening are not implemented. Independent deterministic work is not claimed complete by this evaluation slice.
- Local branch `feature/smart-typing-03-pr01`; no push or remote PR creation authorized.
- Baseline verified: 222 JVM tests, lint/build/privacy/dependency/native gates PASS; baseline API 26/37 CI PASS. New-feature device/quality results unmeasured.
- Immutable model release missing. Actions candidate artifact 9800688354 was downloaded and its inner GGUF verified before evaluation.

## Pre-flight decisions

| Boundary | Decision |
| --- | --- |
| PR1 CLI -> PR2 JNI | Share numerical C++ core; JSONL exists only in developer CLI, never product runtime. |
| PR1 suitability -> PR7 product quality | Prepared-candidate evidence is not end-to-end candidate-generation evidence; report separately. |
| PR2 cancellation -> evaluation | PR1 evaluates unmodified pinned runtime; tokenizer patch must subsequently prove token/score equivalence. |
| PR4 composition -> PR5 Undo -> PR8 punctuation | One owner and one transaction; no reducer-owned parallel undo state. |
| PR6 lexicons -> PR7 thresholds | Frequency and edit features cannot be claimed implemented by the initial prepared-candidate runner. |
| PR9 punctuation -> existing Caps | Initial-case exception is explicit and user-approved; other word content immutable. |
| PR10 release -> external gates | No version bump or release claim with failing/unrun quality, device, or CI gates. |

Ruling: use the clean dedicated checkout on a new feature branch to preserve the verified submodule/build environment; main remains unchanged. No unrelated files existed at start.
Ruling: if PR1 fails suitability, finish its reproducible report and stop model-dependent work as requested, without inventing model performance or continuing to a 0.3 release claim.

## PR1 measured progress

- Exact Actions GGUF downloaded and independently hashed: expected 396704416 bytes / 7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4; GGUF v3, qwen3, file_type15 confirmed.
- Native scorer built against unchanged pinned llama.cpp; math/UTF-8/bounds CTest PASS.
- Independent token-at-time oracle exposed host CPU microbatch dependence: n_ubatch64 sum deltas up to 0.5247 on fixed synthetic requests. Fresh-context and flash-attention checks did not remove it.
- Ruling: PR1 reference uses n_ubatch1 and flash attention disabled, with n_ctx256/n_batch64/CPU4 unchanged. All tested RU/EN/ES sums/counts then matched the independent oracle exactly. No performance claim for Android or permission to widen tolerance.
- Six actual CLI protocol probes passed with empty stderr: three normal language requests, empty list, too many candidates, token overflow. Outputs contain IDs/numbers/error codes only.
- Corpus source collision filter: pinned FrequencyWords 50k lists for each language, hashes recorded by generator. Full lists stay in build; they are a conservative veto, not an authoritative dictionary.
- Ruling: hard distractors must still satisfy planned Damerau edit bounds. Unrelated semantic alternatives discovered in corpus review are removed before any scoring/freeze; the model must not fail because the candidate set was inadmissible.
- Native slice committed as `a2110629989fd66c335072c677c8235b6b235d15`; fresh post-commit JVM tests: 222/222 PASS, zero failures/errors/skips.
- Native task review: both P2 findings addressed (dirty upstream source rejection, cross-batch/masked-logit/token-limit oracle cases); 15 scalar comparisons have exact zero sum delta.
- Python/corpus task review identified two P2 gaps before holdout: absent accent/yo ambiguity counterparts and missing explicit abstention/candidate-recall metrics. Partial calibration was stopped and preserved under ignored `build/smart-typing-0.3/superseded-corpus-v1/`; no holdout was scored, no threshold was frozen, and no model scores were used to choose the correction.
- Ruling: issue corpus version 2 and a new empty score cache after the label-independent coverage repair. Discard the entire partial version-1 calibration from qualification, including unchanged requests, to keep provenance straightforward.
- Corpus version 2 reviewed and committed as `d59d14fa3e608b675bb1c34e8ba13d8a0f5e4979`; SHA-256 `2b3874adabbb60370360087f208d6e9cf2ef308e4955af57114ef2a687c7fd96`. Both corpus/evaluator P2 findings addressed. Independent 24 Python tests and full validator PASS. Repeated generation produces identical seven JSONL files and manifest. Fresh post-commit JVM tests: 222/222 PASS.
- Ordinary CI now validates the corpus, fake-scorer Python tests and native math/UTF-8 tests without downloading a model (`33c12e1`). The CI native commands were checked locally with the SDK CMake 3.31.6, build PASS and CTest 1/1 PASS; this is not a GitHub/Linux execution claim.
- Post-CI-commit fresh JVM tests: 222/222 PASS, zero failures/errors/skips.
- All 6,600 calibration scores completed; config `cc5cf738022b02cf6843f10677e7a2f2d0634abd42427756a23ad2a90bd5928c` frozen before any holdout request. All 6,600 holdout scores then completed. Both scoring processes exited 0; report exited 2 (documented quality FAIL), no runtime errors/missing responses.
- Holdout: RU 162/172 correct automatic replacements (94.19%), EN 7/7 (100%), ES 239/243 (98.35%). False change: 5/1000, 0/1000, 3/1000. All languages fail the minimum 300 automatic replacements; RU and ES additionally fail 99% precision. No tuning after holdout.
- Full score-only cache/config/reports/provenance archived in `tools/eval/smart-typing-0.3/results/2026-09-02/`. Independent evidence review confirmed all hashes, response order/counts, calibration-only freeze, exact JSON/Markdown regeneration and separate raw-score arithmetic. No new findings.
- Ruling: honor the failed PR1 stop gate and preserve the ordered PR sequence rather than begin conditional PR2 or claim release 0.3. A separate fine-tuning milestone is documented; no training, generation API, push, remote PR, version bump or model publication was performed.

## Binding quality and release decision

Each language/split contains exactly 1,000 typo, 1,000 correct/protected and 200 punctuation probes. The report must include counts, precision, false-change, coverage, abstention, candidate recall, punctuation suggestion metrics and Wilson 95% intervals. Freeze corpus and calibration configuration before holdout. Prepared-candidate recall is by construction and does not qualify production generation.

The holdout row gate requires at least 300 automatic replacements per language, precision >=99% and correct/protected false-change <=0.5%. Thresholds may not be retuned after seeing holdout. A failed suitability gate stops model-dependent implementation; fine-tuning is a separate milestone. Independent deterministic features do not establish model-assisted quality.

After each local commit run `./gradlew testDebugUnitTest --rerun-tasks`. Before closing a PR slice run lint, debug/release/profile assembly, release/profile privacy gates, `imeIntelligenceBoundary`, `forbiddenRuntimeDependencies`, and `:runtime-llama:nativeSymbolGate`. New API26, API37, physical Fold, performance and model publication are separate gates. No version bump, push, remote PR, or model publication is implied by local test success.
