# Q6: refinement source-article segment exclusions

The 1,158 article identities in the archived public refinement manifest were matched to the corresponding historical ranker ledger parents and extracted from the exact pinned `ru-0007.parquet` source. All source articles were found once; missing and duplicate IDs refuse the operation. The shard byte count and SHA-256 are checked against the retained source lock before reading and its SHA-256 is checked again afterwards.

| Partition | Articles | Distinct segment keys |
| --- | ---: | ---: |
| Train | 889 | 31,366 |
| Dev | 98 | 4,332 |
| Test | 171 | 5,736 |

The union contains 40,670 distinct segment keys, 38,115 not present in the previous ledger. The source is segmented using the established punctuation/newline delimiter; the results are not independently verified linguistic sentences. The entries store hashes, article keys, parent-entry digests, pinned public source identity and tracked source/archive bindings. They do not require an ignored `build/` file to remain present for the ledger check. Source text was not added to the ledger.

Two independent imports produced byte-identical ledger and receipt; receipt SHA-256 `7d764f0ea0e996584fab92bffdc1e5e5fcbe3bf9a8309585e630e5978454671f`. The original 174 stored entries and incomplete coverage declaration are unchanged. A real new source segment passed the prior incomplete ledger when its completeness check was explicitly disabled, then was refused by the updated ledger as `LEDGER_OVERLAP:sentence` through the compatible normalized sentence namespace. Focused tests cover parent scope, duplicate and missing articles. The complete standard-library inventory passed 784 tests across 156 modules with no skips. This adds exclusions for these source articles, not independent qualification or complete global provenance.
