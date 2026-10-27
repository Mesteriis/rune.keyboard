# Q3 — admission refusal identities (partial)

Admission now distinguishes an absent target (`TARGET_UNKNOWN`) from a known
winner with an ambiguous lemma (`WINNER_AMBIGUOUS`), and a missing or ambiguous
rival analysis (`RIVAL_UNKNOWN`). Unavailable public rare-word evidence reports
`RESOURCE_UNAVAILABLE`; an empty local search maps to `LOCAL_SEARCH_EMPTY`.
The analyzer recognizes the new diagnostic names. Existing numeric reason codes
retain their order; additions are appended. No editor metadata or schema fields
are added in this slice; the diagnostic schema remains 8 and admission VERSION
remains 1.

The joint singleton exception still tests `WINNER_AMBIGUOUS`. Unknown targets
and unresolved rivals could not pass its existing winner/singleton checks;
their new refusal identities do not grant admission. A 120-case independent
expected-outcome table exercises original/target/rival availability, ambiguity,
competing lemmas and both qualification states. Separate assertions distinguish
missing target, ambiguous target, missing/ambiguous rival and unavailable rare
word evidence. The old self-comparison of `allows` against its own `evaluate`
implementation is replaced with explicit allowed/refused expectations.

Validation:

- All 1,281 JVM tests pass, with zero failures, errors or skips; debug lint,
  the scoring boundary gate and all 29 analyzer tests pass.
- Fresh baseline/candidate Kotlin compilations replay 12,012 regression,
  1,676 stress and 1,600 historical calibration rows. All non-timing fields
  match exactly except the explicitly allowlisted admission reason renames.
  Candidates, model scores, allowed booleans, editor commands, final text and
  Undo remain identical. Only the two existing host timing fields are excluded.
- The clean baseline is commit `3c3abe6`. Each compilation binds its own source
  manifest, harness and sources; all 69 asset identities are checked before and
  after and match across versions. Toolchain/compiler/Android stub, input,
  output and comparison script hashes are in the adjacent evidence JSON.
- Among actual admission-hook refusals, 917 regression, 65 stress and 96
  calibration cases now report `RIVAL_UNKNOWN`; one regression and one
  calibration case report `TARGET_UNKNOWN` instead of `WINNER_AMBIGUOUS`.
  Additional per-candidate observer decisions are counted separately in the
  evidence and are not unique boundary events.

Q3 remains open for protected/personal/control veto distinctions, rejected
candidate-response diagnostics, bounded mechanical refusal events, editor
class/variation metadata and schema 9. This slice does not establish a reduction
in actual `BOUNDARY=NOT_QUALIFIED` journal events: the existing replay exports
admission-hook refusals, not every controller boundary diagnostic. Null hook
results must not be counted as successful refusal explanations. No phone update
or new quality qualification is claimed by this receipt.
