# A4: preserve lowercase `инн`

The previous control screen found `инн` automatically changed to `Инн` before
space, period and colon. The candidate generator now marks this one Russian
canonical-case candidate ineligible for automatic replacement. The candidate
remains available for manual selection; `Инн` is still a possible name reading.
Other canonical-case candidates follow the existing policy. This narrow veto
deliberately gives up automatic capitalization for that ambiguous surface in
every context; it is not a contextual name recognizer.

The 140 disclosed authored controls were rerun twice per boundary. All 140 were
retained for each boundary, including `инн`; no input or prefix transformations
were observed. Focused JVM tests cover candidate eligibility, the manual
selection, three boundaries and unaffected `москва` behavior. All 1,374 JVM tests
pass with zero skipped. The Q7 current-product gate independently ran both
2,160 and 12,000 disclosed historical rows twice and matched the existing space
baselines. This bounds parity to those inputs; it does not establish independent
natural accuracy or physical-device behavior.

The changed generator SHA-256 is
`c23069b33735c7a4c29170b3a8125756e3df90400d35189c03cf7cc9d0381afe`.
Raw replay receipts and observations are in
`build/review-a4-inn-fixed-{space,period,colon}-20261028/`; report SHA-256 in
that order: `845a3d35f6ada5e4308159c6a264e0cfa72c42b3bba74dfab03b97224642007b`,
`229277be26c13cccc153cfc8bf8b72bc1b6cdcb3de11b68ba367d552e85e6d01`,
`9a7772c678ee1ed50c1c927747d4c79037393f794d9ab60e45806466e8e5eff3`.
The first release-privacy attempt stopped at `RELEASE_SOURCE_DIRTY`, as the
patch had not yet been committed; its diagnostics packaging and source-check
test prerequisites passed. The clean-source retry of `:app:privacyGateRelease`
passed at commit `84353b0` (log: `build/review-a4-inn-clean-privacy-20261028.log`). Fold protected
abbreviation, useful correction and exact Undo are still outstanding, so A4
remains open.

## Category gate

`tools/typing_experiments/a4_controls_gate.py` checks the fixed corpus and each
boundary's two deterministic observation files, identity map, receipt, source,
asset and toolchain bindings against current bytes. It verifies action results,
actual editor text and Backspace for every row, then fails on any changed control
or failed restoration. Running it on the three corrected receipts succeeds with
zero changes and zero Undo failures in every category; output is
`build/review-a4-control-gate-final-20261028.json`. The same evaluator rejects
the original observed `инн` change on all three boundaries. Three focused tests
also cover missing rows, corrupt flags, unhandled actions and category drift;
their module is in the Q7 Python test inventory. A passing gate covers only this
disclosed authored set, not an independent corpus or Fold.
