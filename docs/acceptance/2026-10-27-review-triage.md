# Incoming review: verified findings and integration priorities

The owner supplied a read-only review based chiefly on `ab8e019`. This triage
checks selected high-impact claims against `00200ac` and records the first fix
at `e6b6555`. It does not claim that every proposed feature, performance estimate
or external-editor scenario in the review has been verified.

## Confirmed release-check blocker, fixed

The tracked `tools/test_typing_diagnostics_boundary.py` fixture omitted
`correctionId`, `recoveryCompletion`, `recoveryInspectedStates` and
`recoveryVerifiedTerminals`. Both the tracked verifier and actual Kotlin DTO
already require those fields. Running the positive-contract test reconstructed
from the original HEAD fixture reproduces one failure, without editing sources.

The existing working-file alignment contains only those four fields, added on
two lines. It is verified and committed separately as `e6b6555`; no runtime,
admission rule, asset or threshold changes. Other pre-existing working changes
remain separate.

Checks:

- All 25 boundary-fixture tests pass in the working tree.
- The standalone source gate passes 17 negative/six positive fixtures and the
  debug/release/profile dependency checks.
- `:app:imeIntelligenceBoundary` passes, including all 64 diagnostics tests.
- A Git archive containing the 263 required tracked source/helper files from
  `e6b6555` passes the same 64 Python diagnostics tests and source boundary gate,
  with no working changes or ignored build inputs.

The clean archive is a boundary-check snapshot, not a full clean Android build,
APK qualification or device test. The initial narrower archive ran 35 tests;
the final archive additionally includes the analyzer and all 64 matching tests.
Both records are retained under `build/review-triage-20261027/`.

## Other selected findings checked against current source

| Finding | Current evidence / disposition |
| --- | --- |
| Visible Undo defaults off | Confirmed in `KeyboardSettings.kt`; schema 3 also decodes a missing key as false in `SettingsCodec.kt`. A default change needs compatibility/migration tests, not just flipping the field. |
| Rejection persistence depends on personal learning | Confirmed in `AndroidTypingPersonalization.rejected()`. This is not permission to enable hidden learning or turn Undo into whole-word confirmation. Preserve the existing opt-out/Undo contracts. |
| Unexpected composition span may remain before BYPASS | The cited `stillOwnsSpan`/`FinishComposingText` code exists and deliberately avoids finishing an unknown span. The proposed data-loss scenario remains a hypothesis until a simulator or editor reproduction; do not remove the ownership guard solely on review text. |
| Important generators/training drivers untracked | `git ls-files` does not contain the inspected `fresh_spelling_holdout.py`, `neighbor_recovery.py` or `train_joint_correction.py`. A tracked durable exclusion ledger is also absent at the reviewed path. This is relevant to current experimental reproducibility. |
| Privacy text versus optional phrase persistence | Confirmed: architecture/user guide claim no disk typing history, while opted-in `committed()` records phrases through `PersonalTypingStore` in `noBackupFilesDir/personal-typing/profile.bin`. Correct disclosure must distinguish defaults, consent and local persistence. No privacy behavior changed here. |
| False-change metrics absent | The review's detailed Q5 is more precise than its summary. `evaluate.py` already computes false-change rates/cohorts and Wilson intervals. The missing evidence is sufficient representative ordinary-chat controls, not the metric implementation itself. |
| APK footprint / native stripping | Requires a measurement of the current packaged release. Do not present an estimate from the older artifact as current measured size or assume the suggested NDK edit alone proves stripping. |

The review's U5 summary proposes a complete personal candidate dictionary,
whereas its detailed card proposes a visible confirmed-word list and explicitly
excludes merging stores and adding PERSONAL candidates. Treat these as different
scopes; a candidate-source change would need independent qualification.

## Updated order for the existing autocorrection objective

1. Preserve reproducibility before further promotion: inventory and track the
   required training/qualification sources and evidence; add the durable public
   holdout ledger, then a deterministic current-product replay baseline and CI.
   Preserve old hash-bound generator files and introduce versioned replacements;
   refactoring their contents in place would invalidate historical receipts.
2. Correct privacy/storage descriptions alongside this inventory, preserving the
   existing consent settings and separate personalization controls.
3. Reproduce the shifted composing-span/BYPASS case with explicit final-text and
   ownership checks before choosing a runtime fix. Add third-party-editor cases
   as measured evidence rather than assuming QA EditText proves compatibility.
4. Implement visible Undo with settings migration, model/canonical cancellation
   coverage and zero new refinement authority; preserve explicit old preferences
   and the existing eight-second window.
5. Expand ordinary-chat correct/protected controls and per-source outcomes, then
   continue short-participle/modal/role correction work with the durable replay
   and exclusion machinery in place.

The broader autocorrection goal remains active. Recent host models/source-v6
remain unqualified (136 useful / nine wrong first diagnostic proposals, 93.79%
raw proposal precision). This review is not a reason to weaken thresholds, bypass
known/rare-word protections, reuse disclosed holdout as fresh qualification, or
ship the experimental right-context source. The reviewer’s suggested bulk staging,
push and model/generator rewrites are not executed as instructions from a file.

No APK build, installation, Fold interaction, complete JVM suite or external
service change is claimed for this triage. The accompanying receipt binds the
reproduction, successful checks and clean tracked-source snapshot.
