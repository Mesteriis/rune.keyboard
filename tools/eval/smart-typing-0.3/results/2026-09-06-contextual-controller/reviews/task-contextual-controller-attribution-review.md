# Contextual controller attribution — independent specification/code review

**Verdict: CHANGES REQUIRED before the 46-request supplement is scored.** The final `prepare-04` evidence is internally coherent and model-free, but the five-file implementation does not yet satisfy three requirements of the approved brief. One is a concrete report-construction defect on a required failure path. Two are specification-evidence gaps in the claimed production route and compile-source closure. Supplemental-cache admission was intentionally excluded from this review.

Reviewed inputs:

- Approved brief: `task-contextual-controller-attribution-brief.md`.
- Handoff: `task-contextual-controller-attribution-report.md`, SHA-256 `809c86102e142ad999f3b32ee537febe7ebfe211221cb403399de729c6c022e4`.
- The five files under `tools/eval/smart-typing-0.3/pipeline/contextual-controller/`.
- Immutable `build/smart-typing-0.3/contextual-controller-attribution-20260906/prepare-04/`, `host-final-08/`, `python-final-03.log`, and `final-model-free-comparison.json`.

No Gradle, device, model, network, or source command was run. Review checks were static/read-only except for one in-memory Python call to `build_metrics`; it wrote no bytecode or artifacts.

## Findings

### 1. [Code, blocking] A tap-stage harness failure can make report construction crash instead of preserving the row

`joined_rows()` forces `decisionId=None` for every harness failure (`contextual_controller_attribution.py:442-458`). `build_metrics()` then counts that row as indeterminate while also counting an offer/tap (`:137-180`) and calculates `abstentions = n - offers - indeterminate`. A failure after an offer has been exposed, such as during tap or duplicate-tap verification, is therefore subtracted twice. A one-row in-memory reproduction with `offer=true`, `tapAttempted=true`, `harnessError!=null`, and the joined `decisionId=None` reaches the Wilson-rate helper with a negative numerator and raises:

```text
ValueError expected a nonnegative input, got -1.0396352948264687
```

An earlier error before `tapAttempted` can instead fail the stricter `attempts == offers` assertion. Both outcomes contradict brief lines 95 and 104: failed rows need structured row evidence, remain in the denominator, and prevent clean completion. They must not abort report generation or become exclusions.

Fix `abstentions` by counting known no-offer rows directly, rather than subtracting overlapping categories. Allow `tapSuccesses <= tapAttempts <= offers` in the aggregate and make `offers != attempts`, a refusal, forbidden edits, or a harness failure set `attributionComplete=false`. Add regressions for failures before a tap, during a handled/refused tap, and during duplicate-tap verification.

### 2. [Specification, blocking] Direct candidate admission bypasses the required production route/ready/reply guards

The host creates `LocalCandidateCoordinator` with unconditional `requestRoute={ true }` and `routeReady={ true }` (`ContextualControllerAttribution.kt:73-75`), then bypasses its request/reply path: `retrieve()` directly calls `beginCandidateRequest`, runs `CandidateGenerator.generate`, and calls `controller.acceptCandidates` (`:101-119`). The actual local path additionally checks `owner.canRequestCandidateWork`, `LanguageRouter.route`, route request/readiness, active language, session/revision, original-token identity, and current candidate ownership before it admits a generated reply (`LocalCandidateCoordinator.kt:195-237`).

The approved brief allows direct final generation, but line 75 explicitly requires service-equivalent owner/route preconditions and prevalidated route handles. All twelve assets are present, so this gap does not demonstrate that any of the 1,200 observed decisions is wrong; it means the current ledger does not prove the production-routing claim it makes. The host also records one coarse terminal route plus gate booleans, but not the required secondary-reason list from brief line 71. For example, all 160 `CONTEXTUAL_INELIGIBLE` rows happen to join to old engine exclusions, yet that relationship is learned only after Python joins labels/export evidence and is not an independently recorded controller-side terminal reason.

Retain the bounded synchronous final-target design, but explicitly validate and record the same owner, `LanguageRouter`, route availability, live reply identity, and original-token guards before direct admission. Emit one terminal reason plus ordered secondary reasons. Then export a fresh model-free prepare and confirm whether the request universe remains byte-identical before scoring it.

### 3. [Specification, blocking] The new compiler closure is actively derived from an archived command receipt

`compile_inputs()` reads `pipeline/results/2026-09-06-command-dot-safety/commands.json` and treats every Kotlin argument except the old diagnostic harness as the source list (`contextual_controller_attribution.py:34,241-250`). That archived file is therefore an active source-selection dependency, not merely a read-only compiler/classpath example. This conflicts with brief line 75, which requires the new tool to resolve and freeze an explicit current dependency list and says the old command file must never act as a source override or active helper dependency.

The resulting artifact closure is otherwise strong: the archived command file itself is bound, current source bytes are bound, snapshots are checked, and the independently compiled `prepare-04` and `host-final-08` JARs are byte-identical. Replace the dynamic extraction with an explicit source manifest owned by the new tool (or an equivalently explicit new receipt), retaining the archived command only as comparison evidence. Add a regression showing that mutation of the old archive cannot change the selected compile sources.

## Passing specification checks

- Labels are absent from the JVM input. `inputs.tsv` has only index, opaque ID, language, prefix, and current word; split/source/observed boundary are joined in Python after host execution.
- Current defaults, current spelling/runtime qualification, ready transport, per-code-point typing, acknowledged editor selections, actual packaged generator, spelling-first model coordinator, and production tap gateway are used. The limitations around earlier-word workers, Android input, physical visibility, and timing are stated.
- Exact original-cache reuse is strict. The full v5 loader/export/frozen-config/calibration/holdout chain is admitted; cache ID, split, payload prefix, ordered IDs, ordered continuations, backend, policy, response schema, error count, and numeric representability are checked before delivery. Token counts 0 and 256 remain `UNREPRESENTABLE_REPLY`.
- Spelling precedence receives no contextual score. No-request rows retain old response identity as unused evidence. Unknown payloads and unrepresentable replies receive `decisionId=null`, suppress complete agreement, and are excluded from ordinary abstention counts when report construction succeeds.
- The independent editor consumes only `TypingEdit`s. Response acceptance is checked for zero editor edits. A visible `CandidateUiItem.Punctuation` is selected through `LocalCandidateCoordinator.selectCandidate`, exact text/caret/composition and a one-command ledger are checked, and the stale duplicate ID must be rejected without edits. Synthetic evidence covers IDs 1-6, threshold boundaries, owner/session/revision/caret/language invalidation, hidden strip, refusal, Unicode uppercase expansion, ordinary grapheme deletion, and no automatic punctuation on Space.
- Execution is bounded by fresh output directories, subprocess timeouts, two active processors, and a 768 MiB heap. No scoring command exists.

## Receipt audit

The final handoff claims reproduced in read-only checks:

- `prepare-04`: 1,200 rows, zero harness errors, zero numeric responses, zero native/model calls.
- Routing: 909 contextual requests, 160 contextual-ineligible, 42 canonical precedence, 63 spelling precedence, 25 incomplete generation, and 1 unknown/no-alternative.
- Payloads: 863 exact old payloads, 46 unresolved `PAYLOAD_MISMATCH`, and 291 no-contextual-request rows. Every unresolved row differs only in `prefix`; all 909 contextual requests contain ordered IDs `[0,1,2,3,4,5,6]` and seven continuations.
- All 12 immediate `prepare-complete.json` output hashes and all 316 protocol-bound file hashes match. There are 49 compiled Kotlin source snapshots.
- `prepare-04/contextual-controller.jar` and `host-final-08/contextual-controller.jar` are byte-identical at SHA-256 `2ee748a7195a0ea849026691d80ee639d7efbdd605e03a7141ad4ae4660f7259`; normalized compile/run commands are identical.
- `host-final-08/complete.json`: 18 cases, SHA-256 `06e74ea8298945bbc1f1a372710f8c71476fcdf3a2e681a8499ddfa7c3e844db`; `python-final-03.log`: 27 tests pass.
- `final-model-free-comparison.json`, SHA-256 `ad6867786f32f20238fc66174bad61043f2845b5a2b0064a3d10fccb17fdd9ed`, reports identical observations/request universe and no production drift.

Final five-file hashes independently rechecked:

| File | SHA-256 |
|---|---|
| `ContextualControllerAttribution.kt` | `dcc37225a72e7cc5b12c3c9c8b28154ed9bb08c9c2602d3355f96c2319b9417a` |
| `HostTypingEditExecutor.kt` | `0acbe371bdfe71cd168d588d122e0db14e414223ab31ab424161152e583420dd` |
| `README.md` | `364db2341ce904167a29ab0e41815a7ee660a2fca5db7a36fe6ce96f71c15abc` |
| `contextual_controller_attribution.py` | `dbf36ed6a3d911cbde0746a8d2d299f97faeba7131cc3796c63e89f148fbd225` |
| `test_contextual_controller_attribution.py` | `0be6e1cf3fa0c9fb9894b8d206dbe705f39db69353ddf13874a7297dd02a7a49` |

`prepare-04/unscored-requests.jsonl` and its receipt remain intact and unmodified. This review makes no supplemental-cache-admission, numeric attribution, semantic quality, Android, physical-device, or model-scoring claim.
