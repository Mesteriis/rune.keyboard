# Instrumental-noun competition and combined role inputs

Pure instrumental nouns after a left copula now have actual retrieved training
competition, including both retention and repair to a short adjective. This is
prepared supervision, not a newly fitted/qualified model or an Android change.

## Retrieval changed the authoring plan

`right_context_instrumental_corpus.py` derives singular instrumental forms from
dictionary paradigms, requiring every surface analysis to be that noun's
instrumental reading. Genitive complements are independently dictionary checked.
Unknown corruptions are one edit from the noun and within three unit edits of
the declared predicate competitor. Wider distances use the existing OSA helper;
the author does not invent a one-edit keyboard cost for them.

The initial seven old noun/predicate pairs produce 1,102 authored rows / 138
native queries, but selection keeps only 40 correct-original controls. No
unknown-input contrast has both required forms retrieved. Therefore that
preparation does not count as closing the supervision gap. `зал` and `пол` lack
a pure instrumental surface under this pinned dictionary; their other training
coverage and the natural hard-negative diagnostic category remain unchanged.
The initial generator is preserved as a hash-matching snapshot under
`build/right-context-instrumental-v1-20261027/initial-generator.snapshot.py`.

Four additional authored noun families (`ум`, `бог`, `беда`, `боль`) have closer
competitors in existing adjective families. Examples include `умом / умён`,
`богом / богат`, `бедой / беден` and `болью / болен`. They were selected from
dictionary/corruption/retrieval evidence, never from disclosed natural failures.
All old attempted pairs remain in the new authoring and its exclusion report;
unretrieved contrasts are not injected or counted as available training groups.

The revised preparation has 2,862 authored rows / 346 completed native queries.
Complete-pool selection keeps 180 groups / 3,062 candidate rows:

| Label type | Groups |
| --- | ---: |
| Unknown original, intended noun or predicate | 72 |
| Unfinished-suffix retention | 36 |
| Correct-original retention controls | 72 |

The remaining 2,682 rows are explicitly excluded: 1,152 missing contrasts, 864
missing applied forms, 576 missing targets and 90 incomplete pools. These are
first-reason counts, not independent conditions. Complete manual-retention pools
may supply correct-original controls, as in the unchanged selection procedure.
The unknown/unfinished groups require complete joint pools and both actual
contrast forms. Applied states are authored counterfactuals, not editor actions.

The real-dictionary/native-pool audit finds 24 unknown-input groups with a pure
instrumental noun already applied after a left copula: 12 retain that correct
noun with a genitive complement and 12 repair the wrong noun to a predicate.
Both labels share the same left-context/original query and differ in visible
following context. The six unknown spellings are `бедей`, `бедон`, `богот`,
`больн`, `умон`, `умём`. This is limited exposure across four noun families,
not independent quality evidence or broad instrumental coverage.

## Combined 242-field preparation

The previous 32,024 groups, the 2,268 left-sequence groups and these 180 groups
combine to 34,472 groups / 473,067 candidate vectors. The existing v1
242-field schema supplies a 96-field residual input after the frozen first
146 fields. No reader/profile registration or trained forest is added here.

The previous 445,321 candidate rows preserve all 221 prior feature values,
labels, group IDs and saved weights exactly. All 32,024 previous groups reuse
their identical candidate pools. There are 2,448 fresh groups; all vectors are
finite. Across combined group inputs, 6,209 repeats have identical targets and
there are zero contradictory targets. This input identity check does not prove
that every different intended role is separable by the model's feature space.

Supervised family exclusions increase from 38 to 42. A metadata-only scan of
the existing clean calibration/holdout family sets finds no context containing
the four new families, so no current row requires prospective exclusion. No
holdout prediction or score was read or computed. Future corpus collection must
exclude all 42 families; the new preparation records the full list.

Artifacts are under `build/right-context-instrumental-v2-20261027/` and
`build/right-context-left-role-v11-inputs-20261027/`, bound by the accompanying
receipt. The legacy `previousFrozenModelSha256` field in the latter preparation
references the previous **feature-preparation manifest**, not a newly trained
model; `modelTrained` and `productionQualified` are both false.

## Checks and next boundary

All 174 `test_right_context*.py` tests pass, including three new instrumental
authoring tests. Native replays, complete-pool selection, dictionary/counterfactual
exposure audit, combined input conflict audit and exact vector-prefix/label/
group-ID/weight identity checks pass. Training candidate presence is distinct
from source admission or first-action quality.

Next is an explicitly versioned 242/96 residual profile, fitting the prepared
inputs, numeric parity and the unchanged natural first-action quality gates.
The previous v9/v10 quality failures and insufficient natural cohort volume
are still unresolved. No threshold requirement is reduced, no holdout is scored
and no Android/JVM/lint/APK/device check or installation is claimed for this slice.
