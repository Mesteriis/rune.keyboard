# Rune Smart Typing 0.3 — quality qualification

Historical 0.3.0 evidence. The [0.3.1 report](2026-09-07-rune-0.3.1.md)
supersedes this document as the current release status. The scores below are not
a fresh run of the changed 0.3.1 source tree.

Date: 2026-09-06. Scope: source-bound, model-assisted spelling evaluation on the
frozen RU/EN/ES corpus. Physical Fold validation is excluded from this acceptance
scope by the product owner; Android API validation uses emulators.

## Inputs and procedure

The evaluator is [`final_product_replay.py`](../../tools/eval/smart-typing-0.3/pipeline/final_product_replay.py).
It compiles the versioned source manifest, verifies every bound input digest, exports
all 12,000 spelling rows without model calls, scores calibration, freezes policy, then
scores holdout separately with the exact Rune Text GGUF:

- bytes: `396704416`
- SHA-256: `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`
- scorer SHA-256: `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`

The fresh receipt is local and ignored by design:
`build/smart-typing-0.3/final-product-replay-20260906-current-v5/`.
Its `source-freeze.json`, `policy-freeze.json`, complete score receipts and
`report.json` bind the current sources and prove that holdout was not observed while
choosing the policy.

## Holdout result

| Language | AutoReplace | Correct | Precision | Aggregate false-change | Original in applicable candidate sets | Exact Undo of automatic edits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EN | 304 | 293 | 96.38% | 0 / 1,000 (0.00%) | 1,901 / 1,901 | 304 / 304 |
| ES | 408 | 396 | 97.06% | 0 / 1,000 (0.00%) | 1,901 / 1,901 | 409 / 409 |
| RU | 358 | 341 | 95.25% | 1 / 1,000 (0.10%) | 1,901 / 1,901 | 358 / 358 |

All three language gates pass: at least 300 automatic spelling replacements,
precision at least 95%, aggregate false-change at most 0.5%, original available in
every candidate set, and exact immediate Undo for every automatic edit. Protected
forms that never create a candidate set are excluded from the original-candidate
denominator; they remain included in false-change evaluation.

The report has `releaseApproved: true`. The model-unavailable replay made zero
automatic spelling replacements in all three languages.

## Verification

- `PYTHONPATH=tools/eval/smart-typing-0.3/pipeline python3 -m unittest test_final_product_replay` — PASS, 17 passed and 1 environment-gated integration test skipped.
- `./gradlew testDebugUnitTest --rerun-tasks --no-configuration-cache` — PASS.

This receipt supersedes the earlier failed product-holdout receipt for the current
source-bound policy. API 26/API 37 emulator matrices and normal build gates remain
recorded separately.
