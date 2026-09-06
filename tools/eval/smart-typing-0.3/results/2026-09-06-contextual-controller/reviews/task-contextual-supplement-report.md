# Contextual supplemental-cache admission — frozen implementation handoff

2026-09-06. Ready for independent review; source edits stopped. Scope is the five contextual-controller tool files only. Previous preparations/freezes/reviews remain untouched. No production, corpus, old cache, policy, model, Gradle/device/network or numeric corpus delivery change occurred. No model was invoked. Root owns all scoring and final replay.

Implemented `supplement-freeze`, `supplement-stage`, and `supplement-complete` with explicit supplemental admission in both `replay` and `verify`. The freeze reconstructs the ordered unmatched universe from admitted current prepared inputs and actual contextual requests; it binds the prepared protocol/completion, exact row IDs/splits/languages/prefixes/ordered seven candidate IDs/continuations, unchanged policy/config, exact backend identity and physical runner/model hashes. Each freeze reserves one calibration and one holdout run directory. Existing/orphan or alternate retry slots fail. Holdout staging requires the fully admitted calibration completion and binds it before the external invocation.

External native output is plain response JSONL. Staging writes exact input, identity, command and run-input artifacts without executing anything. Completion requires those artifacts, a successful single-attempt execution receipt, intact stream hashes, exact response count/order/identity, and the existing strict numeric schema. Candidate reordering fails. IPC-unrepresentable counts/durations remain explicitly unresolved. Native error responses remain complete unavailable evidence, with exact error IDs; no retry-to-green or missing-row omission is provided. Nonzero exits/partial files do not get a completion marker.

Replay uses distinct `SUPPLEMENT_OK`/`SUPPLEMENT_ERROR` statuses through the actual host transport. Supplemental row provenance identifies its response file, completion and freeze; original-cache rows keep their original file hash. Supplement entries cannot attach to no-query, spelling-precedence or exact-old-cache rows, and every entry must be consumed by its exact current contextual payload. Verify reconstructs both split admissions from their exact files, all joined metrics and current compiled host outcomes. The existing 1,200-row denominators, source-agreement semantics, manual tap accounting and error/unknown handling are preserved. No new quality gate or fitting was introduced.

## Evidence

- Python: **36/36 PASS**, `supplement-python-03.log`. The prior 30 tests remain. New positive/negative cases cover strict error-preserving admission, missing/duplicate/unexpected/reordered IDs, bad numerics, token representability, wrong payload/split/policy/backend/preparation, source/identity/file drift, partial output, process failure, Boolean execution-count coercion, calibration-before-holdout ordering, orphan/retry-slot refusal, and the integrated old-cache/no-query/supplement binding and TSV path. Only the expensive full-corpus admission boundary is substituted in synthetic fixture setup; supplement files and physical fixture hashes are real.
- Actual host: **22/22 PASS**, `supplement-host-01/complete.json`. Existing numeric transport case now also proves successful supplemental offer/tap and supplemental error delivery/no offer. Compiler/runtime use two processors and 768 MiB. Commands, source snapshots, logs and JAR are retained in that directory.
- RED evidence preserved: `supplement-red-01.log`, `supplement-red-02.log` (missing boundary), `supplement-slot-red-01.log` (alternate retry slot accepted), `supplement-type-red-01.log` (Boolean attempt count accepted; subsequent failures are consequences of that wrongly written completion), and `supplement-host-red-01/` (`SUPPLEMENT_DELIVERY` before the transport extension).
- Fresh model-free preparation `supplement-prepare-01`: **1,200 rows, zero harness errors, zero native calls, no full-corpus numeric results consumed**. Routing remains 909 contextual, 63 spelling, 42 canonical precedence, 25 incomplete generation, 1 unknown/no-alternative, 157 engine excluded, 3 no owned space. Payloads remain **863 exact, 46 unresolved prefix mismatches, 291 no contextual request**.
- `supplement-prepare-comparison.json` records byte-identical actual row ledger, inputs TSV, payload bindings and unmatched requests against reviewed `route-review-prepare-01`; no shared production/asset binding changed. All twelve packaged assets remain bound.
- Fresh supplement `supplement-freeze-01/freeze.json`: **46 requests, 18 calibration + 28 holdout**. Neither split has been staged/scored/admitted. All 46 remain unresolved; no outcome or measured abstention is claimed for them.

## Root commands after review

The preparation and supplement freeze below are already complete; do not rerun them into the same directories. The exact prepare/compiler invocations are retained in `supplement-prepare-01-command.log` and `supplement-prepare-01/commands.json`. Freeze invocation was `supplement-freeze --prepared build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-01 --output build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-freeze-01` with the recorded Python/pyarrow environment below.

```sh
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/model-v02/venv/lib/python3.11/site-packages
CONTEXTUAL_PYTHON=/Users/avm/.pyenv/versions/3.11.14/bin/python3.11
CONTEXTUAL_TOOL=/Users/avm/projects/Personal/rune-keyboard/tools/eval/smart-typing-0.3/pipeline/contextual-controller/contextual_controller_attribution.py
CONTEXTUAL_PREPARED=/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-01
CONTEXTUAL_SUPPLEMENT=/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-freeze-01
CONTEXTUAL_REPLAY=/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-replay-01
"$CONTEXTUAL_PYTHON" "$CONTEXTUAL_TOOL" supplement-stage --freeze "$CONTEXTUAL_SUPPLEMENT" --split calibration --output "$CONTEXTUAL_SUPPLEMENT/calibration"
```

Run the exact standalone Python invocation documented in the tool README with `$CONTEXTUAL_SUPPLEMENT/calibration` as its argument. That procedure executes the staged two-element native argv once, creates stdout/stderr exclusively, and records `execution.json` with exit status and command/input/output hashes even on timeout. Preserve any failure; do not retry that run. It creates no scores in an original cache. Then:

```sh
"$CONTEXTUAL_PYTHON" "$CONTEXTUAL_TOOL" supplement-complete --freeze "$CONTEXTUAL_SUPPLEMENT" --run "$CONTEXTUAL_SUPPLEMENT/calibration"
"$CONTEXTUAL_PYTHON" "$CONTEXTUAL_TOOL" supplement-stage --freeze "$CONTEXTUAL_SUPPLEMENT" --split holdout --output "$CONTEXTUAL_SUPPLEMENT/holdout" --calibration "$CONTEXTUAL_SUPPLEMENT/calibration"
```

Only after that successful stage, invoke the same documented external procedure once for `$CONTEXTUAL_SUPPLEMENT/holdout`. Then:

```sh
"$CONTEXTUAL_PYTHON" "$CONTEXTUAL_TOOL" supplement-complete --freeze "$CONTEXTUAL_SUPPLEMENT" --run "$CONTEXTUAL_SUPPLEMENT/holdout"
"$CONTEXTUAL_PYTHON" "$CONTEXTUAL_TOOL" replay --prepared "$CONTEXTUAL_PREPARED" --supplement-freeze "$CONTEXTUAL_SUPPLEMENT" --supplement-calibration "$CONTEXTUAL_SUPPLEMENT/calibration" --supplement-holdout "$CONTEXTUAL_SUPPLEMENT/holdout" --output "$CONTEXTUAL_REPLAY"
"$CONTEXTUAL_PYTHON" "$CONTEXTUAL_TOOL" verify --prepared "$CONTEXTUAL_PREPARED" --replay "$CONTEXTUAL_REPLAY"
```

External execution remains operator-attested hash-bound evidence, not a cryptographic trusted-execution or asynchronous availability proof. No Android InputConnection, physical timing, semantic correctness or unseen-generalization claim is added.

## Frozen identities

- Prepared protocol internal SHA256: `646446bf1a192f370134fc8cdddc4d4ff83a3e0d76f9c7ef13418e3083408562`.
- Supplement freeze internal SHA256: `0f067e87fdf1982102f797e6c86b39a858f75bd73b09009d6e7e549ca434d21c`.
- `tools/eval/smart-typing-0.3/pipeline/contextual-controller/ContextualControllerAttribution.kt`: `b5ceb68e6c1501f44ddbf6a77e7d9d7987ae0c04fb81607f4cd406116c47e52b`.
- `tools/eval/smart-typing-0.3/pipeline/contextual-controller/HostTypingEditExecutor.kt`: `8fb57ca0f3e406b9cd05f347906e3c34201e432f3eb16288dabd704f88d863c6`.
- `tools/eval/smart-typing-0.3/pipeline/contextual-controller/README.md`: `bc5859fb8dfa2e0f56b7b6345812c622138daee32659ac9bf62e53457de1a6ee`.
- `tools/eval/smart-typing-0.3/pipeline/contextual-controller/contextual_controller_attribution.py`: `78f100109cad58ea1758dcdb37695806f766e209dbf6fff9405dd0d8b8fb549c`.
- `tools/eval/smart-typing-0.3/pipeline/contextual-controller/test_contextual_controller_attribution.py`: `dea13fc34f5a8c297753a6afe43dc5deb3cf72d163c9ac7744e6092da2daccbd`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-01/protocol.json`: `3d0a3e625f9e555d42b2c9380804fdfd19cd5fd3c5e16b0e6378cf58ac338d05`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-01/prepare-complete.json`: `abac0b8285a449174b2749f4a2c1ddc7ed0875dc1ddb3edbce8a877c962fb2b0`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-01/contextual-controller.jar`: `3f6454920d65c0f59d1f8a7ba8ea760ab98710686e59d16fbb2a530edd358e4c`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-01/unscored-requests.jsonl`: `a06a8571b61f20c4db56f22261ab8c35086b380dd360e56ddb9aacf3927bc9a6`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-freeze-01/freeze.json`: `e60e059d5afe6bce51aa7005139f3597791214971fe1efff00549f7586778b9c`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-python-03.log`: `d2117d9d9e7348226e34d7af781d1f63b7e0be136af016ce4378c08e5a4d65d4`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-host-01/complete.json`: `9448995946369dac18db7d38698c203b7cf8719001473440d3c4b4c568bcf48b`.
- `build/smart-typing-0.3/contextual-controller-attribution-20260906/supplement-prepare-comparison.json`: `401e26f1ff5be7d0b0a115dc360f6280fcab7da413eefa9efc2406f07cc90460`.
