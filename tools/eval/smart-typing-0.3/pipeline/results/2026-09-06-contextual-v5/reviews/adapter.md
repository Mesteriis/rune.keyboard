# Contextual v5 adapter independent review — 2026-09-06

Verdict: **one P2 admission finding; fix before real export/scoring**. No other actionable finding in this bounded adapter review. Existing 33 scoped synthetic tests pass, and the current recorded Kotlin policy/variant parity artifacts pass read-only admission/hash checks. These passing checks do not cover the downgrade bypass below.

Reviewed HEAD `55195f20da162a10e690de98da481da18e7f77d8` plus the adapter diff: `pipeline/contextual_quality.py`, new `pipeline/test_contextual_v5_adapter.py`, and the README addition. Read dependencies include the strict v5 loader, actual Kotlin exporter/engine, existing cache validation and Wilson implementation. No real source corpus rows or numeric model cache were read, no corpus was exported/frozen, and no model, build, device or delegated operation ran. Only disposable synthetic test files and this report were written. Native metadata receipts were read solely for backend identity.

## P2 — Removing corpus metadata bypasses v5-to-legacy downgrade admission

Location: `tools/eval/smart-typing-0.3/pipeline/contextual_quality.py:397–414`, especially the optional `elif "corpusDirectory" in receipt` at line 409.

`load_export` selects its semantics from mutable exported row markers. When all v5 row markers and all receipt binding keys are removed, `records_binding` returns `{}` and the receipt agrees with that empty binding. Removing the optional `corpusDirectory` field then skips even the legacy manifest-type check. The current source/policy/compiled-binary/actual-output checks remain satisfied, because the compiled artifacts need not change. Only exported row JSON and its receipt digest need be updated.

Independently executed synthetic reproduction using the new test fixture:

1. Call `V5ReceiptFlowTest.setUp()` and its synthetic `export()`; obtain 1,200 admitted v5 export records.
2. For each exported record, remove `corpusVersion`, `labelSemantics`, and `observedBoundary`; set fabricated `ambiguous=False` and `expectedCandidate=BOUNDARIES.index(previous_observedBoundary)`.
3. Remove all `CORPUS_BINDING_KEYS` and `corpusDirectory` from `provenance.json`; rewrite `rows.jsonl` and update only the receipt's `records` SHA-256.
4. Call actual `load_export` on that directory.

Observed result:

```json
{"syntheticOnly":true,"v5DowngradeAccepted":1200,"binding":{},"legacyAmbiguousRows":1200,"corpusManifestStillV5":5}
```

The accepted records then select legacy `metrics`/`metric_semantics`, so observed Wikipedia spaces/punctuation can be treated as authored semantic ambiguity/expected-candidate labels and lose the v5 diagnostic-only flags. This contradicts the explicit no-mixed-schema/no-reinterpretation contract. Existing downgrade coverage only removes receipt keys while retaining row markers; it therefore fails closed without exercising this bypass.

Required correction: require the corpus directory and manifest binding on every current export receipt and validate/replay the selected source format, including the existing full-corpus loader on the legacy path. An equivalent strict format-discriminated admission is acceptable if a v5 export cannot become legacy by removing metadata, or by pointing the weakened legacy branch at an unrelated manifest. Keep legitimate current legacy exports as a positive control. Add the complete synthetic downgrade regression above, rather than merely another single-field mutation. The exact consumer-source change must also receive refreshed Kotlin policy parity before any freeze.

## Reviewed behavior that holds apart from that finding

- Explicit `--corpus-format contextual-v5` calls `corpus_contract.load_corpus`, not its weaker artifact-only reader. The loader source confirms exact manifest/row schemas, complete file and 40-exclusion identity checks, recorded Python/pyarrow implementation identities, quotas, source/observation checks and deterministic full selector replay. The default branch still invokes the original complete legacy loader and `validate` before selecting punctuation rows; no spelling corpus requirement was removed from that entry point.
- The actual unchanged Kotlin exporter calls `ContextualPunctuationEngine.variants` and emits sequential candidate IDs. The consumer requires exactly the seven boundaries in production order, checks sentence-initial casing for period/question/exclamation continuations, and preserves zero-variant exclusions. Strict v5 source words use the admitted EN/RU/ES alphabets, so the reviewed casing check matches this source scope. No expected candidate or ambiguity label is fabricated on the intended v5 path.
- Intended v5 `load_export` re-admits the source corpus, binds its manifest and row digest, compares exact Kotlin input bytes, reparses actual output, and compares exported records. V5 receipts/configs carry format/version/label semantics plus loader, generator and both lock hashes. The downgrade finding is the alternative admission branch, not a failure of this intended v5 branch.
- Schema-2 policy binding, total-log-probability comparison thresholds (`>0.5` over Original and `>=4.0` over the strongest other punctuation), tie handling, invalid-score abstention and the prior orphan-cache guard remain intact. Score caches bind actual ordered request payloads, protocol, runner/model hashes, complete numeric/error responses and file digest. Errors remain abstentions; excluded rows cannot receive fabricated scores. Calibration must be complete before freeze and holdout requires the current frozen config/backend/export links.
- Source metrics retain every row in language/boundary denominators, including exclusions and errors. Agreement compares final decision boundary with the observed source boundary; Original therefore agrees at source spaces even when caused by errors/exclusions. Those causes remain separately counted. Coverage, abstention, exclusions, runtime errors and missing responses use all stratum rows; insertion at spaces uses every observed-space row. All seven decision IDs are exposed, including punctuation absent from source strata. Each rate has numerator/denominator and Wilson 95% row-descriptive interval; empty strata use null rate/interval. Automatic replacements remain zero.
- Config/report flags explicitly state no semantic correctness evaluation and no quality gate. The README accurately describes source punctuation as an observed boundary rather than a unique semantic answer, quota/non-independence/pretraining limitations, missing/error conventions, and absence of spelling/model/device qualification claims. Its broad claim that all downgrades are rejected is not yet true because of the P2.

## Independent scoped verification

Command:

```text
PYTHONDONTWRITEBYTECODE=1 /Users/avm/.pyenv/versions/3.11.14/bin/python3.11 -m unittest discover -s tools/eval/smart-typing-0.3/pipeline -p 'test_contextual*.py' -v
```

Result: **33 tests PASS**, 0.245 seconds. No real corpus, model or compiler execution occurs in these tests; I/O boundaries use disposable explicit synthetic fixtures.

An additional independent inline metric check used three observed-space rows: one missing response, one runtime error, one production exclusion. All three remained abstentions/space agreements, each cause count was one, insertion was 0/3, an empty comma stratum returned null rate/interval, and Wilson endpoints were independently checked (including the closed form for 3/3). PASS.

Read-only `load_verification` admitted the current 79-case Kotlin/Python policy receipt. The 12-row synthetic actual-variant receipt was checked for self-digest, current consumer/policy/loader/source hashes, exact recorded artifact hashes, Java/compiler hashes and driver identity: six seven-variant rows and six retained exclusions. No Kotlin compilation or execution was rerun here.

| Evidence | SHA-256 |
| --- | --- |
| `adapter-policy-parity/verification.json` | `1c4a0d7a0f7198e0be3fe9cc37f54c6685f3a46e357646fbcc599cef1fa0ab37` |
| `adapter-variant-parity/verification.json` | `952b4dd5190344f509377cf63ad88ea1b4ae04e21966200689d2dd97c42a0cc7` |

Those evidence paths are under `build/smart-typing-0.3/contextual-v5-20260906/`. They are current only for the consumer hash reviewed here and must remain historical after its correction. Scoped `git diff --check` passed.

## Backend-only config contract

No helper contract change is required merely to provide a new, clearly backend-only self-hashed config. `verified_model` (`contextual_quality.py:426–434`) validates the config digest and consumes its `modelIdentity.runnerSha256` and `modelIdentity.modelSha256`; it does not require spelling coefficients or spelling qualification. `score_run` independently constructs the supported `rune-score-jsonl-v1` cache identity and checks expected model size through `cache_identity`. Freeze/holdout compare actual protocol/runner/model identity across splits. The existing synthetic backend-config test and synthetic v5 scoring flow exercise this shape.

The archived native `run-input.json` explicitly distinguishes historical runner `f2f8e9e21a028871da4b9ced6ce0492eb692f742c4de765467a2d44a18535973` from current runner `bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553`, with the same model `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`. A new backend config should identify only the current tested executable/model and its native verification provenance; it must not rewrite the legacy spelling config or imply that native compatibility requalifies spelling or v5 source semantics.

The helper's internal `SPELLING_CONFIG` error name is historical; no legacy calibration is required by its actual schema. Additional provenance fields can be self-hashed in the new backend config, but its entire file hash/provenance fields are not propagated by `score_run`; only execution identity is propagated. Root should bind/archive that exact config and provenance in the reviewed protocol freeze. If pipeline-enforced propagation of the complete backend-config provenance is desired, that would require a separately reviewed receipt-field change; it is not necessary to accept the current binary under the existing identity contract. Config protocol metadata, if included, is descriptive to this helper: the enforced request protocol comes from `cache_identity`.

## Reviewed source binding

| File | SHA-256 |
| --- | --- |
| `pipeline/contextual_quality.py` | `4dd02feb7b313f66c27d80767967070ff1702c99764dba8091e2f0b5449bef6f` |
| `pipeline/test_contextual_v5_adapter.py` | `f30cd4eb08bac45e14241cc82d400aeb11436370d622d6ed88e5724933a4dbee` |
| `pipeline/README.md` | `fdc22579a7020ee61fa3caf77dfa55f239df70886992e325f022168816e592b6` |

Paths are relative to `tools/eval/smart-typing-0.3/`. Strict loader SHA-256 remains `100bafb1fa324aa4be500c38bd49f7c54c2ca211ca0149be5bd6f30d52e1371e`. This is the initial adapter verdict; a subsequent fix needs its own appended recheck and refreshed source/parity binding.


## Independent P2 fix recheck — 2026-09-06

Current verdict: **P2 resolved; no remaining actionable finding in this bounded adapter slice**. The original finding, reproduction, initial source hashes and historical verification above are preserved. This recheck applies to consumer SHA-256 `ab02e8457abe3cfdf711f67b52b13be33fde7f7693270bf4dc4203f5ba49c713`.

`load_export:399–413` no longer has an unchecked legacy fall-through. Every current schema-2 export requires a nonempty repository-relative corpus location without parent traversal, a resolved location inside the repository, a matching manifest SHA-256 and `holdoutScored:false`. Both branches then call `corpus_rows` with their selected format: v5 reaches the strict source/selector loader; legacy reaches the unchanged full loader plus `validate`. Both require the admitted corpus-row digest, exact Kotlin input bytes and equality of stored records to actual-output parsing against those admitted source rows. Pointing a stripped export at another source cannot bypass these source/input/output comparisons. The existing current exporter writes all required links, so this closes the missing-provenance path without introducing a historical-receipt exception.

The new complete downgrade regression reproduces the original combined row/receipt stripping, including fabricated ambiguity/expected-candidate fields and a fresh exported-record hash, then requires `EXPORT_CORPUS_LOCATION`. The new legitimate legacy positive control verifies all 1,200 records remain admissible and specifically asserts that the complete legacy loading and validation execute. Its missing/wrong manifest and rehashed changed expected-candidate cases fail. Existing v5 admission/replay, receipt, metric, complete cache and semantic-flag tests still pass.

Independently rerun scoped command (same Python 3.11.14 command recorded above): **35 tests PASS**, 0.270 seconds. A separate inline repeat of the original downgrade proof now rejects the removed-location case with `EXPORT_CORPUS_LOCATION`. Retaining the v5-shaped fixture's location while stripping all other v5 markers instead reaches the actual complete legacy loader and fails because its required spelling corpus file is absent; it does not return fabricated legacy metrics. Both checks used only disposable synthetic exports with model/compiler subprocesses substituted by the existing explicit test boundary.

Fresh read-only `load_verification` admission of `adapter-policy-parity-downgrade-fix/verification.json` succeeds for **79 cases**, validating current policy/consumer, probe, toolchain/commands, exact artifact hashes and expected/actual outputs. Receipt file SHA-256: `713dae9657f42bdc001b7cc3760cad35b98676acfa87194004699f6cdaa6d178`. The old policy receipt now fails with `VERIFICATION_POLICY`, as required. No compiler execution or model scoring was performed by this recheck.

Historical policy receipt SHA `1c4a0d7a0f7198e0be3fe9cc37f54c6685f3a46e357646fbcc599cef1fa0ab37` and historical variant receipt SHA `952b4dd5190344f509377cf63ad88ea1b4ae04e21966200689d2dd97c42a0cc7` remain unchanged. The old variant run remains historical evidence for the unchanged Kotlin variant engine; it is not represented as a run of this new consumer. The fresh policy receipt is the current prerequisite for the subsequent root-owned freeze.

| Rechecked file | SHA-256 |
| --- | --- |
| `pipeline/contextual_quality.py` | `ab02e8457abe3cfdf711f67b52b13be33fde7f7693270bf4dc4203f5ba49c713` |
| `pipeline/test_contextual_v5_adapter.py` | `db92d1ace500db615ad4b4a24f2f97fb7b33a77540baf9bf5fdaf69c80c99629` |
| `pipeline/README.md` | `8e399b2a77e27735fe530f8ed5f2cbc9ea1b121e3a574c08dec7a714df920ad0` |

Scoped whitespace checks are clean, and these hashes were rechecked unchanged at report append. No production/source edits, corpus export/freeze, real corpus or numeric cache reads, device operations, model calls, builds, commits or delegation occurred. The backend-only config assessment and diagnostic/qualification limits from the initial review remain unchanged. This verdict clears the reviewed adapter correction; it does not assert a real corpus evaluation or Android result.
