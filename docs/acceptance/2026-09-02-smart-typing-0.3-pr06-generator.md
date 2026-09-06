# Smart Typing 0.3 — PR6 candidate generator checkpoint

Date: 2026-09-02. Base: `84e47273b02e3b1726601f2e76b8023dda8a8218`.

This checkpoint implements a worker-confined candidate generator and the read-only index contract. It does not close PR6, enable spelling in the IME, or establish calibrated AutoReplace quality.

## Behavior

The original is retained with at most seven alternatives. Exact membership and both language scans share the 8,192-state and 64-terminal budgets. Protected tokens and valid words prohibit AutoReplace. Retrieval enumerates the unit edit radius; all verified neighbors receive the approved weighted features before deterministic case preservation, deduplication, fallback quota and top-N selection. No unit-ranked top-seven prefilter is permitted.

On exhaustion, already verified alternatives may remain suggestions; completion explicitly prohibits AutoReplace and does not claim exact top-N. Cancellation clears returned text references. Recoverable reader failures return original-only; interrupted work preserves interruption, and fatal errors propagate after owned scratch cleanup. Candidate diagnostics redact payloads. Clearing a retrieval veto never supplies calibrated confidence.

## Verification

- Approved proposal SHA-256: `94bab7a89c47a3da7ddc4946457bdaeb3080515f30012fc00695a4ad892a3b95`.
- Independent review fixed and approved two P2 findings: a stable terminal tie for case-expansion collisions, and checked reader exception handling.
- 27 generator JVM tests, including 236 independent finite weighted/routing oracle comparisons, passed at author handoff.
- Integrated `./gradlew testDebugUnitTest --rerun-tasks`: **359 tests PASS**, no failures/errors/skips; 46 tasks executed.
- Integrated prescribed lint, debug/release/profile assembly, release/profile privacy, IME boundary, dependency and native-symbol gates: **PASS**, 238 tasks / 43 executed.
- Local evidence: `build/smart-typing-0.3/pr06-generator-jvm-integrated.log`, `pr06-generator-gates.log`, and `candidate-generator-prototype/REREVIEW.md`.

The required fresh post-commit JVM result is recorded with the commit identity in the progress ledger/task report. These pre-commit results are not relabeled as post-commit evidence.

## Remaining gates

A validated production reader, full-lexicon weighted/cross-language oracle, packaged assets, latest-request worker and live IME publication remain to be integrated. No API26/API37/Fold result is claimed for this generator checkpoint. Deterministic and final model-assisted holdout quality, physical performance and external CI remain separate. Version remains 0.2.0; no push or remote PR.
