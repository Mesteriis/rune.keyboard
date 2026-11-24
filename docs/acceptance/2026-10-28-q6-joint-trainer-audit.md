# Q6: joint trainer data-role gap

Source inspection at `2764c1d` found a remaining training entry-point gap in
`tools/typing_experiments/train_joint_correction.py`. The CLI checks hashes for
its train and calibration row files against the supplied manifest and checks the
legacy `family` fields for overlap. It does not invoke the permanent-registry
gate, check the manifest's historical/disclosure role or bind registry snapshots.
It creates the requested output directory and writes `frozen-policy.json` with
`stage=frozen-before-independent-holdout`, even when the supplied corpus is a
previously disclosed historical corpus. A stage name alone is not independent
qualification; a later gated calibration/evaluation does not protect a direct
invocation of this older trainer.

The maintained preparer and the newer joint calibration receipt already have
role-aware registry and input binding. Completing this training path requires
binding both training and calibration data, observations, source/model inputs
and registry state before output, preserving the original trainer bytes for the
historical receipt, and keeping historical reproduction explicitly disclosed.
The existing numeric training procedure and independent-holdout exclusions must
not be silently weakened. The separate pinned rescue trainer must be assessed
under its own historical-only contract.

This is a source audit, not a claim of a live incorrect model, an end-to-end
reproduction, or a fix. Q6 remains open; no model, corpus, device or trainer
was changed in this slice.

The exact trainer source recorded by the original policy (`e8b5adf14ac94ae6f54efbc2ad499630d3460dbf007eb76d4b640b9f2422620a`)
is now retained in `frozen_sources` with its original path. Nine source-identity
and history tests pass, including a changed-current-source fallback and an
archive-corruption refusal. This preserves evidence needed for the forthcoming
trainer change; the data-role gap itself is not yet fixed.

Follow-up guard: default CLI invocation now checks registry completeness before
loading scientific dependencies and refuses even a complete registry until the
new training-role binding exists. Explicit `--historical-reproduction` accepts
only the original pinned public corpus, original export receipts/observations,
context and feature identities, and a fresh output under `build/`. Published
policy is labelled `historical-disclosed-calibration`, with independent and
production qualification false and both current registry hashes recorded.
Captured input, code, source receipt and registry bytes are rechecked before
writing the policy. Other intermediate training files can remain in the fresh
output if a later check fails; they do not constitute a frozen policy.

Twenty-seven focused tests pass in the pinned NumPy/CatBoost environment. They
include normal and optimized default refusal, changed historical manifest
refusal before output, exact archived-source fallback and corruption refusal,
existing numerical calibration tests, and a mocked historical control-flow test
that verifies role flags and detects training-row drift before policy write.
The latter uses a dummy model and mocked hashes: it is not actual model training
or proof of historical reproduction. The full original training run and complete
independent training/registry binding remain outstanding; Q6 remains open.

A subsequent binding slice captures the train and calibration row files, both
schema-2 source-bound `joint-export` replays and all declared replay resources.
It checks row identities and editor consistency, the corpus/registry role,
source-code and runtime-context snapshots, and disjoint article, sentence,
context and canonical-family keys between those two partitions. The holdout file
is hashed without parsing its labels. The source closure now includes `train.py`,
which supplies features used by `rank_refinement.py`.

The trainer still refuses new training after this capture with
`TRAINING_SOURCE_ATTESTATION_REQUIRED`: a manifest and registry hash do not by
themselves prove that held articles, contexts and canonical families are
independent from training or that row identities reconstruct from source. That
attestation and a true fresh run remain required. No new model is trained or
qualified by this slice.

Forty-two focused tests pass, including a synthetic two-replay fixture, rejection
of train/calibration overlap and input drift, refusal before creating output,
historical role checks, and existing calibration/evaluation tests. The fixture
mocks registry completion; it is not evidence that the real incomplete ledger
or a fresh corpus is qualified. One initial test fixture accidentally reused a
context across partitions and was correctly rejected; after giving the fixture
distinct contexts the final suite passed. Python test-inventory validation also
passed. Raw output is `build/review-hosted-editor/trainer-full-binding-final.log`.

After adding the training binding and `train.py` source closure, the existing
versioned CI calibration smoke completed locally on six disclosed rows with the
actual current product replay and published-weight scoring. Its receipt reports
14 isolated input-mutation refusals, mid-calculation drift and second-write
refusals, unchanged packaged files, and both qualification flags false. Raw
artifacts are in `build/review-hosted-editor/trainer-binding-calibration-smoke/`.
This is a compatibility check of the changed calibration source binding; it does
not train the model, attest the held corpus, or establish natural-text quality.
The API 26 emulator suite was running concurrently, so its timing around this
short smoke is not an isolated performance measurement.
