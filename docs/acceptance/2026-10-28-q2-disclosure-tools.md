# Q2: retained diagnostics and disclosed source fixtures

This source-only slice follows `2d59c74`. It versions three existing helpers
and their tests unchanged: descriptive quality slices, deterministic authored
stress data/reporting, and the owner's explicit offline 95% proposal-ratio gate.
All 19 existing tests pass. Both reporting CLI --help commands pass; stress
prepare produces a fresh local authored corpus without model/scorer execution.
The ratio gate preserves minimum volume, controls, prior-correct retention and
net gain; it does not configure per-word product confidence.

The original 35-row CC0 regression fixture and five-case detailed-source metadata
are retained byte-for-byte. `audit_disclosed_fixtures.py --historical-root .`
verified all 35 rows against the hash-pinned original corpus, source sentence
hashes and captured prefixes. It verified the five original row/proposal
triples, frozen model/policy hashes, source sentence hashes, SHA-256 of each
prefix, public source URLs and contributor attribution against the original
six-column detailed export. The recorded proposal JSON is compared and hashed;
model scores were not recomputed. Source snapshots and digest bindings are
listed in the adjacent evidence; no source sentences are added to that report.

The durable registry already excludes all 35 source/sentence/prediction-context
identities and all five detailed-source sentence IDs. No new ledger entries
were needed. This is known-exposure coverage, not complete canonical-family or
fresh-data qualification. The five cases were historically included only through
the owner-authorized original 4,000-context training corpus; they cannot qualify
that run independently. The older 35 remain regression-only.

Eleven new source/role/schema/exclusion regressions pass. Default CI audit checks
tracked exact fixture bytes, minimized five-case schema/attribution and current
registry coverage, without accessing ignored historical data. Full historical
source verification is explicit and fails when those original inputs are absent.
The audit emits numeric counts and hashes, never context text, and performs no
model calls. Current inventory: 113 stdlib and 19 scientific test modules.

The three original experiment reports linked by the fixture README are restored
with their bodies unchanged and a separate historical-scope notice. Their old
training, scoring and qualification claims are retained history, not reexecuted
or fresh acceptance. Q6 transitive lineage, family recovery and independent
qualification remain open, as does broader Q2 README/dependency closure.

No app source, assets or production policy changed. No APK install, training,
new model execution or hosted CI run was performed. Pending owner additions in
the main experiment README remain outside this commit; only the new reviewed
source-status paragraph is integrated.
