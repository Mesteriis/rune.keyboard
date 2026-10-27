# Q6: recover every historical punctuation source article

Recovered all 3,600 punctuation rows across qualification-v2, compact-v3/v4 and
RU/EN/ES. All nine scans succeeded. Original archived punctuation selectors,
source locks, article-selection filters, source Parquet SHA-256/size and frozen
component hashes are verified. Original prefix, current word, boundary and
selection hash must match; all eligible matching occurrences are retained.

| Component | Language | Rows | Occurrences | Articles |
| --- | --- | ---: | ---: | ---: |
| qualification-v2 | EN | 400 | 401 | 389 |
| qualification-v2 | RU | 400 | 402 | 384 |
| qualification-v2 | ES | 400 | 401 | 386 |
| compact-v3 | EN | 400 | 402 | 387 |
| compact-v3 | RU | 400 | 404 | 391 |
| compact-v3 | ES | 400 | 402 | 392 |
| compact-v4 | EN | 400 | 401 | 385 |
| compact-v4 | RU | 400 | 401 | 375 |
| compact-v4 | ES | 400 | 403 | 387 |

Total: 3,617 occurrences in 3,476 language-qualified articles. Of 1,150 RU
articles, 373 already occur in the lexical registry and 777 add coverage.
Article hashes include language and normalized decimal Wikipedia ID. Protected
controls remain authored fixtures with no invented source article. Original
control keys/bindings and protected entries are preserved; the lexical registry
and its 122/131 overlap report are unchanged.

The final scanner saves immutable source-control bytes with each receipt, so
subsequent registry enrichment cannot invalidate its input path. The baseline
was verified against the pre-recovery Git snapshot. A second complete set of
nine scans produced byte-identical identity files to the first set. The merge
checks every dependency/input hash and original row/selection identity, then
requires all nine groups before adding article keys. No source windows or lemmas
are inferred, and overall freshness coverage stays incomplete.

All 91 tests pass in a source-only directory without original corpora, models,
PyArrow or morphology packages. New tests cover all matching occurrences,
source divergence, language-qualified article IDs, append-only merging,
incomplete receipts/model calls, malformed keys and a persisted RU article.
CI includes these tests; no remote CI execution is claimed.

The accompanying evidence binds final receipts, baseline snapshots, repeated
identity checks, namespace audit and final registry. Versioned preparation must
check these article keys as well as both registries' context/family/control
keys; wiring those gates is the next step. No Android build, Fold action,
model call or changed historical label is part of source recovery.
