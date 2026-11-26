# Q6: English UniMorph exact-surface exclusions

[UniMorph English](https://github.com/unimorph/eng/tree/66e0e9e8e2dcd196da081a25a48e5c1fe3d8b49b)
identifies Wikipedia as its source and declares CC BY-SA 3.0. Two downloads of
its `eng` file at that revision were byte-identical: 18,022,905 bytes,
SHA-256 `20a191cefdc7cad6fa74b00f49d6f658684f17b14541aae372e5a3d5a8c15c67`,
and Git blob `8eae5ed242e87e50f6bd182133277f50fe93cef3`. The two independent
captures reproduced the same projection. The source download was not retained.

The source's 652,477 rows were screened against exact surface keys already
disclosed by the English Tatoeba and EWT inputs. For every matched headword,
all supported 1–32-character ASCII English forms in the source were retained,
including alternatives for ambiguous forms. The resulting attributed fixture
contains 27,382 headwords, 60,216 distinct headword/form pairs and 54,631
exact form keys. It has SHA-256
`f393af784e10dca0bac2e1cb0f751d2b9a31e0062c3d8dc308b6c875546bacf2`.
Of those keys, 22,647 were absent from the previous lexical and EWT surface
exclusions; 80 of those were already present in the separate control surface
keys. Other axes can also reject a proposal, so these are not counts of
previously admissible words.

Only those 22,647 exact keys are added as a new lexical exclusion entry. The
preceding 222 entries and incomplete-coverage metadata remain identical.
The source-bound importer and fixture verify the previous entry identities,
the Tatoeba parent and the EWT source fixture; `--capture <eng> --check` can
reproduce the projection from the pinned source. The fixture and its
[notice](../../tools/typing_experiments/english-unimorph-surfaces-v1.NOTICE.md)
are subject to the source attribution and share-alike terms. These are exact
form exclusions, not inferred intended senses, canonical-family certification
or complete English morphology.

Three focused tests cover ambiguous alternatives, changed source/parents and
fixture, and real preflight refusal of a form absent from the earlier exact
surface controls. All 25 ledger snapshot tests and 27 preparation tests passed;
the older English Tatoeba and Russian Wiktionary import checks also passed.
The importer and three tests passed in a staged source archive without `build/`;
test-inventory validation passed. Temporary source and archives were removed.
Full stdlib/scientific profiles and hosted CI were not repeated. English family
qualification, global registry completeness and fresh independent data remain
open; no model, APK or product policy changed.

## Apostrophe-variant preflight

The original gate looked up exact English surface hashes, so typographic
apostrophes could miss a previously disclosed ASCII-apostrophe form. Among 43
distinct apostrophe-containing forms in the UniMorph fixture, 31 had a blocked
ASCII/curly form while the corresponding alternate exact key was absent from
the lexical and EWT surface sets. A synthetic pre-fix regression reproduced the
miss. The gate now checks all combinations of ASCII apostrophe, curly
apostrophe and modifier apostrophe for English typed and target surfaces in the
family profile, and for control surfaces in both profiles. More than four
apostrophes produces an identity error rather than exponential expansion.
This is a conservative exclusion comparison; old keys are not rewritten.

All 31 observed mismatched variants have an alias in the existing exclusions.
A single preflight over those 31 variant rows returned `BLOCKED_OVERLAP` with
29 lexical and two EWT overlap signals. Counts are key signals, not labelled
word accuracy. The revised preparation suite passed 29 tests; the fresh
selector suite passed 22, both in-memory text diagnostics passed 13, the new
UniMorph importer passed three, and refinement, word and retrieval receipt
suites passed nine, nine and seven tests respectively. The 29 preparation
tests and three importer tests also passed from a staged source archive without
`build/`. One earlier pre-fix test failed as expected; temporary archives were
removed. Both isolated historical boundary and suspended-retrieval runners
also passed with their archived helpers. This does not certify English family
coverage or qualify new data.
