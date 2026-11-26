# Q6: source and family projection for four selectors

The refinement, word-ranking, additional-epoch and retrieval collectors now
attach the numeric source article, original target window and complete selector
segment on the registry-checked path. They project every dictionary-only
analysis of the selected target into the shared canonical-family namespace.
Missing analyses and source, segment, context or family reuse across partitions
stop before output creation. Source and frequency inputs, the selector support
code and dictionary implementation are hash-bound and rechecked before the
registry gate. The pinned dictionary receipt is retained with successful
registry-checked output. Historical reproduction retains its previous row
schema and selection behavior.

The existing real registries remain incomplete, so fresh publication still
fails before source extraction. An isolated test intercepted the initial and
final registry guards solely to exercise the selector paths on the pinned public
Parquet. For retrieval the unavailable old observations manifest was replaced
with a test stub; its prior-exclusion coverage is therefore not demonstrated.
The real dictionary and input identity checks were used. Results:

- Refinement and word collectors refused before output due to source reuse
  across partitions. Separate diagnostic projection found respectively 1 and
  5 unresolved rows and 1,552 and 1,529 pairwise family intersections. These
  selectors needed a genuinely disjoint selection algorithm before fresh use.
  The subsequent [admission step](2026-10-28-q6-disjoint-selector-admission.md)
  adds it; separately emitted training text still blocks fresh publication.
- Epoch and retrieval reached the intercepted final gate with 1,500 and
  1,800 rows. Independent scans of the pinned source matched every recorded
  article, selected target, whole segment and context-window hash. The
  intercepted outputs are explicitly test-only, not qualified corpora.
- Historical word and epoch runs each reproduced all seven JSONL files byte for
  byte. Focused tests include both-registry overlap, unresolved family, source
  reuse, historical mode and source mutation refusal. Provenance-path checking
  and `git diff --check` pass.
- The final stdlib inventory passed 769 tests in 153 modules with no skips
  (`build/review-q6-projection-gate-final3-20261028/`). An earlier run that
  overlapped source edits failed its source-drift check; the final run started
  after those edits and passed it.

Raw execution and independent window-scan logs are in
`build/q6-selector-live-final3.log`, `build/q6-selector-projection-check.log`
and `build/q6-selector-window-verify.log`. The final epoch and retrieval rows
are byte-identical to the rows used in the independent window scan. Those files are local diagnostic
artifacts, not the published training inputs. This work does not establish
complete registry coverage or an independent holdout. Q6 remains open.
