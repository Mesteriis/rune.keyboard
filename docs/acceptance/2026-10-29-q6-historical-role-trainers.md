# Q6 historical role trainer sources

Three early right-context training scripts, previously available only in
ignored local build directories, are retained byte-for-byte in
`tools/typing_experiments/frozen_sources/`. Their SHA-256 values match the
training-source identities in the corresponding surviving v1, v2 and v3
frozen-model records. Those original frozen-record SHA-256 values are,
respectively, `34f0a5f18a33ae5903949164c72112a00e43048ae75be6c75883ca99a061ac23`,
`e3b2a07111958a829229e0b9270fa3e60ac2eb9bd6459748b11eabc3b834c9a2` and
`0b36e184e562667026b0d66434d69d8bde86d98d0567316b6a08085f9676a8a8`.
The archived scripts contain no non-ASCII string literals; no historical
training was executed or new training data published during this recovery.

Fourteen surviving frozen-model records, including the six composite residual
models, were also checked against their actual artifact types: all 83 applicable
model, plan, group, vector, weight and selection hashes matched. All 14 records
state that the models are not qualified. The initial generic inventory used the
wrong binary filename for composite models; its six apparent misses were
resolved by checking their declared composite manifests and both constituent
models. This is a current local identity check, not proof of independent model
quality or successful replay of every model.

A CI verifier hashes the three archived scripts and checks Python syntax without
executing them. Its test rejects missing or modified files; hosted CI has not
run this change. The original frozen records and model artifacts remain under
ignored local `build/` and are not required by the portable source verifier.

At the later tracked checkpoint including the recovered sources and feature
replay driver, `python3 tools/fdroid_data_policy.py` passed with 31 inventory
entries, and all 12 `test_fdroid_data_policy.py` tests passed. The two recovered
feature-source verifier tests and the trainer verifier test also passed. This
checks the local data policy and source guards; it is not a new F-Droid scan,
independent build-server run or release acceptance.

After restoring the three trainer files, every one of the 322 direct
`modelFeatureSources` references in the 14 surviving frozen-model records has
a matching tracked file: 53 distinct source hashes. A tracked projection records
the model-record hashes, original source basenames, source hashes and tracked
paths without publishing local absolute paths or model data. The corresponding
portable verifier checks the pinned projection and all 53 files, and its test
rejects source and projection mutations. The projection was compared to the
original local records when created; the portable check does not re-read those
ignored records or prove their completeness, transitive dependencies, historical
execution or independent qualification.

## Comparison with late-training receipt projections

Both tracked source inventories were revalidated and compared by the model
directory name recorded in each late-training receipt path. All 17 projected
receipts matched 11 of the 14 model directory names. Across those receipts,
321 source references matched a model-record source by basename and SHA-256;
three additional references, one each for v4, v5 and v6, were
`select_training_groups.py` and their archived bytes passed the late-source
verifier. No same-basename/different-hash reference was found. Counts are
references across receipts, not distinct files.

This directory-name correlation and source overlap do not bind a particular
receipt to execution of a particular model: the portable model projection does
not include the plan hash. The three additional selector references do not
resolve the 49 unbound imports, establish transitive provenance, or prove
training execution. Original historical receipt files were not re-read for
this comparison; both inputs are tracked projections.

A bounded static import screen of the 322 recorded source references found 49
model/import pairs where an imported module name matches a tracked project
module but is not itself listed in that model's direct source bindings. The
five distinct names are `ranker`, `grammar_contrast_corpus`,
`right_context_contrast_corpus`, `right_context_subject_evidence` and
`right_context_timeline_calibration`. Some corpus manifests separately name
some of these modules, but that does not establish which bytes a model run
actually imported. The screen includes imports inside functions whether or not
they ran, ignores dynamic and relative imports, and classifies by module basename;
it neither proves those 49 paths executed nor inventories all transitive
imports. Consequently the direct source inventory does not establish full
transitive provenance.

`tools/ci/audit_role_model_transitive_imports.py` reproduces this first-level
screen against the pinned source projection and tracked project module names;
its focused test covers static versus dynamic imports. The command reports
incomplete closure rather than using the absence or presence of findings as
qualification. Hosted CI remains unverified.
The same 49 findings and the focused test were reproduced in an isolated
tracked checkout without `build/`; a temporary Git index supplied the project
module inventory.

The screen now distinguishes direct module-level imports from nested or
conditional imports. All 49 model/import findings include at least one direct
module-level import in a bound source: `ranker` in 14 model records,
`grammar_contrast_corpus` in 6, `right_context_contrast_corpus` in 11,
`right_context_subject_evidence` in 8 and `right_context_timeline_calibration`
in 10. Module-level means the import would run if that particular source file
were imported; the frozen source list alone does not establish that every such
file was imported during fitting. Some other historical corpus manifests record
hashes for some names, but their presence there cannot by itself bind the
training process. The unit test checks the top-level/nested distinction and the
explicit exclusion of dynamic imports.

## Runtime imports in the byte-exact v5/v6 refit

The [v5/v6 refit command](../../tools/typing_experiments/refit_historical_role_models.py)
now records project modules present in each subprocess after fitting. It
records each module name, repository-relative source path and SHA-256. The
wrapper checks the file in the isolated source export and its Git blob at
`3bd893ca175bf7c62760611d09c0dab7e5d1fe68` before accepting the receipt.
The regression test rejects modified source bytes, a matching forged report
digest for those bytes, and a path escaping the source export.

The offline repeat verified nine modules for v5 and two for v6. Both fit
stages loaded `rank_refinement` and its project dependency `train`.
The v5 feature stage also loaded the morphology `ranker` at SHA-256
`66a4004867f68b04942cf08975641523d0bd40f82d57bed82b6b14eb93035c3d`.
The ranker is one of the imports absent from the original direct
source bindings. V6 used v5's verified vectors. The other three unbound names
from the v5/v6 static screen were absent from both final module snapshots.

Both model bytes and the vector archive matched all three original SHA-256
values. The numeric receipt SHA-256 was
`b0d594caf8d636e101ee4a9c00464430f536e5dc0f439b64114c92ab77ff610d`.
The environment, checkout and fit files were removed. The snapshots cover the
replayed fitting stages. They leave the original receipt preamble, any modules
unloaded before completion and the other model records for separate provenance
checks.
