# Q6: archived refinement text exclusions

The pinned public historical-data archive contains 1,069 refinement text records: 888 train, 97 dev and 84 test. All corresponding article keys are present in their respective historical ranker parent entries. The importer checks archive contents and manifest article membership, records the parent-entry digest, and adds separate source-segment and dictionary-family entries for each partition. The six entries bind tracked archive, attribution, source-lock and helper files; they do not bind ignored `build/` paths.

| Partition | Records | Russian surfaces | Dictionary resolved | Unknown exact surfaces | Family keys |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 888 | 55,986 | 47,221 | 8,765 | 22,106 |
| Dev | 97 | 13,000 | 11,708 | 1,292 | 7,381 |
| Test | 84 | 12,607 | 11,392 | 1,215 | 7,232 |

The union contains 24,586 family keys, including 11,110 absent from the previous ledger, and 10,745 unsupported-surface keys, including 10,027 new keys. There are 1,067 distinct segment keys summed across partitions. Multiple dictionary analyses are all retained; unrecognized forms are exact surface exclusions only. Truncated fragments can include partial words. This covers the retained payloads, not every article's full text, all possible canonical analyses, or proof that all prepared text was used for model training.

Two independent generations matched byte for byte; the receipt SHA-256 is `830b0407caa3e1c0578df7b79198861c0d674081a7195966bbb29f644f79fbfa`. All 168 preceding stored entries and the incomplete-coverage declaration were preserved exactly. A newly covered real dictionary family passed the previous incomplete ledger with its completeness check explicitly disabled, then was refused by the updated ledger as `LEDGER_OVERLAP:family`. Focused tests cover parent identity/article scope, ambiguous dictionary analyses and exact unknown surfaces. The complete standard-library inventory passed 782 tests across 155 modules with no skips. Complete historical lineage and independent qualification remain open; no model or APK changed.
