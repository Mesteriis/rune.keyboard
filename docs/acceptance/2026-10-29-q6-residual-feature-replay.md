# Q6 historical residual training feature replay

`tools/typing_experiments/replay_historical_residual_features.py` reconstructs
v10–v12 training features from their retained groups and verifies their saved
labels, group IDs and weights. It checks v13 and v14 as identical-input copies
of v12, rather than counting them as separate feature recomputations. The driver
checks model record hashes against the tracked historical source projection,
checks all projected source bytes, and compares the actually imported feature
sources with the model bindings where present. Two old preparation scripts no
longer match their live versions; their exact tracked archival copies remain in
the projection. Dictionary receipts, frequency files, installed assets and
model input hashes are also checked. The script does not fit or qualify a model.

The driver SHA-256 is
`444bb9c8327171ba3ef431b128d414b7c37296c7acc765a533b5cb5116809665`.
The stdlib guard tests reject outside output and optimized Python. At this
checkpoint the complete local replay is still running; v10 has completed with
zero mismatched vectors, while the remaining sets are pending. It requires the
historical ignored build inputs and a scientific Python environment. The static
source bindings do not establish the full runtime import chain or independent
data qualification.

The initial full invocation completed v10, v11 and v12 with zero feature, label
or weight mismatches, but then failed before writing a final receipt: its alias
check incorrectly required v13 and v14 weights to equal v12. Their groups and
vectors do match v12, while their intentional weight policies differ. The failed
log SHA-256 is `fd729b183742cd6a0d62edf92f926391283e4c7a3847c2cc9243dc54df997b34`.

The corrected driver (SHA-256
`32a9fb378f0ce04f40ecf2e8a3a96a3345c0a7123e8f4d870443730e5b3e644f`)
checks the shared groups and vectors, then independently recomputes v13's
strong-supervision and v14's signature-based weights. Its four stdlib guard
tests pass. The corrected full replay completed successfully: 1,422,067
vectors were independently reconstructed for the three distinct v10–v12 input
sets, with zero unequal float32 vectors, nonfinite values, label errors, group
ID errors or weight errors. v13 and v14 reuse the verified v12 groups and
vectors; their distinct weights were independently regenerated with zero
mismatches. Relative to v12, 144,858 v13 weight rows and 217,287 v14 weight
rows differ. Across all five model records there are 2,429,425 rows including
reused inputs. The aggregate receipt SHA-256 is
`ec7a499ffc990da55b61068538668d4ae2bf819651fe2eb4d5004bbef7c20f23`.
This verifies retained training inputs, not full historical provenance or
independent qualification.
