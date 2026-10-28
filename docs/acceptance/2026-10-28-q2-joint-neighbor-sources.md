# Q2: joint/neighbor sources and historical gaps

This slice follows `7b1d4da`. Fourteen existing source files and eight associated
test modules are retained without byte changes: base external holdout builder,
neighbor preparation/training/scoring/product replay/controls, joint and
follow-up preparation, joint/rescue training and calibration, and product and
acquisition evaluation. Source hashes and exact commands/exit codes are in the
adjacent evidence JSON. All local experiment-module imports resolve to retained
sources; dynamically loaded product harnesses/generators were already tracked.
This bounded import inspection is not full transitive execution proof.

All 26 tests across the eight retained modules pass using the existing pinned
NumPy 2.2.6 / CatBoost 1.2.8 host environment. The three stdlib-assigned modules
also pass without scientific dependencies. All fourteen --help entry points
exit successfully, without training, corpus generation or model scoring.
The versioned runner inventory now assigns all tracked tests to 98 stdlib and
19 scientific modules. Relevant checks cover deterministic neighbor edits,
zero-error threshold selection, refusal of incorrect model refinements,
family partitions, original retention versus acquisition, actual editor output,
prefix/control/Undo errors, and new-acquisition precision independent of old
correct retentions.

Five original public JSON receipts/manifests are retained byte-for-byte under
historical_provenance_sources/joint-neighbor-receipts. The joint original
trainer and follow-up v2 calibrator SHA-256 fields match current retained source.
Three preparers match previously retained frozen-source snapshots. None of
these identity comparisons is a fresh model execution or qualification.

Two historical neighbor source versions remain **unrecovered**: corpus builder
`bf2118a0b7d54f10a56d59c73ae77900fbd957c997f8307452b33549769b0323`
and frozen-policy tool
`8d42d7e854ea205e797f9d0d2e41dc1f260a050613c708eb933ef3aebfa856bd`.
The current neighbor source has a different SHA-256. The original receipts
preserve this disagreement; current tests cannot prove historical source parity.
Q2 source/dependency closure and Q6 historical/fresh-data qualification remain
open. Historical preparers do not become approved fresh-qualification builders
merely by entering Git; global consumed-data exclusions remain required.

No product source, asset or policy bytes changed. No new Android installation,
model training or hosted CI run was performed. Only the new source-status
paragraph is staged in the experiment README; pending owner text is preserved.
