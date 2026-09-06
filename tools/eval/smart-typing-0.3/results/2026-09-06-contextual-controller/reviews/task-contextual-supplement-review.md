# Contextual supplemental-cache admission — independent review

**Verdict: PASS for the bounded supplemental admission boundary.** No blocking code or specification gap was found before scoring the frozen 46-request supplement. The reviewed implementation keeps supplemental evidence distinct from the historical v5 caches, admits only a complete exact response set, and binds calibration before holdout. Prior controller-route, metrics, and source-closure findings remain closed and were not reaudited.

Reviewed inputs:

- `task-contextual-supplement-brief.md`.
- Final handoff `task-contextual-supplement-report.md`, SHA-256 `57db9b1e42e8ae7baecd4582833de9f4ed9b4c596381c78e57686a77196ebe98`.
- The current five files under `tools/eval/smart-typing-0.3/pipeline/contextual-controller/`.
- Fresh model-free `supplement-prepare-01`, frozen `supplement-freeze-01/freeze.json`, `supplement-prepare-comparison.json`, and the final Python/host receipts.

No tests, Gradle, device operation, model call, scoring, numeric delivery, or network operation was run for this review. Checks were static and read-only except for this report.

## Exact freeze and source identity

`supplement_document()` reconstructs the supplement from the strictly reopened prepared corpus/export/config/cache/source closure and selects only actual contextual requests whose old-cache relationship is `PAYLOAD_MISMATCH` or `NEW_CONTEXTUAL_REQUEST` (`contextual_controller_attribution.py:497-523`). Each frozen row contains the exact opaque ID, split, language, prefix, ordered candidate IDs, and ordered continuations. The freeze additionally binds the prepared protocol and completion, unscored-request receipt, frozen config, backend config, and physical runner/model bytes. Loading the freeze recomputes the entire document from the prepared evidence rather than trusting rehashed freeze content (`:534-542`).

The frozen artifact contains exactly 46 unique requests, 18 calibration and 28 holdout, with candidate IDs `[0,1,2,3,4,5,6]` and seven ordered continuations on every row. Its request list exactly matches the simplified ordered records in the prepared `unscored-requests.jsonl`; its internal request digest is `cfef3f5f2e84612b0b75b26d63d747d5cadde4bef7e90c58108d7d9a74bc09cc`. The prepared unmatched file is byte-identical to the previously reviewed route prepare at SHA-256 `a06a8571b61f20c4db56f22261ab8c35086b380dd360e56ddb9aacf3927bc9a6`.

The freeze requires the exact `rune-score-jsonl-v1` identity and the fixed physical hashes:

- Model: `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
- Runner: `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`.
- Frozen config: `57fcb49a576de30d6447a48906f81986f25a9a0e527d09a5b091ed64fc47b037`.
- Policy: unchanged version-2 total-log-probability rule with `> 0.5` over Original, `>= 4.0` over the punctuation rival, and controller-deliverable token counts 1–255.

## Split execution and strict numeric admission

The freeze reserves only its `calibration` and `holdout` children (`contextual_controller_attribution.py:545-580`). Holdout staging requires the fixed calibration directory, fully revalidates its completion, and records that exact completion hash before any holdout invocation (`:549-568`). Calibration has no parent. Existing directories and alternate retry slots are refused.

Completion reconstructs the staged request, identity, command, and input receipt, then requires an exact single-attempt, zero-exit execution receipt whose request, response, command, input, and stderr hashes match (`:583-615`). Response admission requires exactly one response per frozen request in the same order. The existing strict native response validator rejects unknown fields, IDs, error names, nonfinite or positive log probabilities, malformed counts, and duplicate candidate IDs; the supplement additionally requires score order to match `[0..6]` (`:479-494`). Native-valid boundary counts 0 and 256, and a duration outside the controller's `Long` range, remain `UNREPRESENTABLE_REPLY`; counts outside the native 0–256 envelope and invalid durations fail admission. Native errors remain `SUPPLEMENT_ERROR`, preserve the exact response and error ID, and cannot be replaced by a missing or later successful row under the completion contract.

The focused regressions cover missing, duplicate, unexpected, and reordered row identities; score reordering and malformed numerics; representability; artifact and identity drift; nonzero exits; Boolean/multiple attempt counts; partial JSONL; fixed run slots; and calibration-before-holdout (`test_contextual_controller_attribution.py:307-470`). The documented external command opens outputs exclusively and records one attempt even on failure. Its receipt is correctly described as operator-attested evidence rather than trusted execution.

## Replay and verify closure

`make_response_bindings()` first reconstructs the original-cache relationship for every one of the 1,200 rows. A supplement may replace only a current `PAYLOAD_MISMATCH` or `NEW_CONTEXTUAL_REQUEST`, must match the live row's ID/split/language/prefix/ordered IDs/continuations exactly, and every supplied ID must be consumed (`contextual_controller_attribution.py:633-648`). Exact old-cache and no-contextual-request rows therefore cannot be relabeled with supplemental responses.

Supplemental response provenance records `kind=supplement`, split, run directory, freeze identity, response-file hash, and completion hash. Original reused responses retain `kind=original-v5-cache` and their historical response-file hash. `SUPPLEMENT_OK` and `SUPPLEMENT_ERROR` remain distinct through the Kotlin response transport. Unrepresentable supplemental replies stay unresolved and cannot become numeric controller replies.

Replay requires the freeze and both split directories together, writes the exact binding and transport ledgers, and checks that the current host request-side observations remain identical to preparation (`:651-733`). Verify reopens the same supplement freeze and split completions, reconstructs bindings, transport, all row evidence and metrics, checks the completion marker, and recompiles/re-executes the bound current host (`:737-770`). This closes the supplement files into the existing 1,200-row attribution receipt without modifying the historical caches.

## Frozen evidence

- `supplement-prepare-01/prepare-complete.json`, SHA-256 `abac0b8285a449174b2749f4a2c1ddc7ed0875dc1ddb3edbce8a877c962fb2b0`: 1,200 rows, zero harness errors, zero native calls, no full-corpus numeric results consumed; 863 exact, 46 prefix mismatches, 291 no contextual request.
- `supplement-freeze-01/freeze.json`, file SHA-256 `e60e059d5afe6bce51aa7005139f3597791214971fe1efff00549f7586778b9c`, internal freeze SHA-256 `0f067e87fdf1982102f797e6c86b39a858f75bd73b09009d6e7e549ca434d21c`: 18 calibration and 28 holdout requests; no split staged or scored.
- `supplement-prepare-comparison.json`, SHA-256 `401e26f1ff5be7d0b0a115dc360f6280fcab7da413eefa9efc2406f07cc90460`: byte-identical input, actual request, payload-binding, and unscored-request ledgers versus `route-review-prepare-01`, with no production/asset binding change.
- `supplement-python-03.log`, SHA-256 `d2117d9d9e7348226e34d7af781d1f63b7e0be136af016ce4378c08e5a4d65d4`: 36 tests pass.
- `supplement-host-01/complete.json`, SHA-256 `9448995946369dac18db7d38698c203b7cf8719001473440d3c4b4c568bcf48b`: 22 host cases pass, zero native calls.

Reviewed source identities:

| File | SHA-256 |
|---|---|
| `ContextualControllerAttribution.kt` | `b5ceb68e6c1501f44ddbf6a77e7d9d7987ae0c04fb81607f4cd406116c47e52b` |
| `HostTypingEditExecutor.kt` | `8fb57ca0f3e406b9cd05f347906e3c34201e432f3eb16288dabd704f88d863c6` |
| `README.md` | `bc5859fb8dfa2e0f56b7b6345812c622138daee32659ac9bf62e53457de1a6ee` |
| `contextual_controller_attribution.py` | `78f100109cad58ea1758dcdb37695806f766e209dbf6fff9405dd0d8b8fb549c` |
| `test_contextual_controller_attribution.py` | `dea13fc34f5a8c297753a6afe43dc5deb3cf72d163c9ac7744e6092da2daccbd` |

This PASS authorizes only the already frozen 18 calibration requests followed by the 28 holdout requests under the exact staged command and single-attempt preservation protocol. It does not establish a quality gate, semantic correctness, unseen generalization, trusted execution, Android behavior, or asynchronous model availability.
