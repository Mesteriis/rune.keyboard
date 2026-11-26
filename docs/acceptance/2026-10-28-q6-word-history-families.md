# Q6: historical word-ranking family quarantine

The versioned public historical fixture contains all 9,000 original word-ranking
rows: 6,000 training, 1,200 development and 1,800 test. Its source manifest,
archive members, public Wikipedia article attribution and previous context
exclusions were verified before processing. Every row's target, cohort, unique
ID and article membership were checked. No source text is copied into the ledger.

The pinned dictionary recognized 8,995 target occurrences. All dictionary-only
analyses produced 2,295 distinct family keys, of which 615 were not previously
blocked by the default supervised/prepared-training family checks. Five target
occurrences across three distinct surfaces had no dictionary analysis. Their
exact public surface keys are quarantined without guessing lemmas; two were not
previously blocked. This conservative quarantine covers all partitions and
does not claim that every prepared target was actually consumed in training.

One new family entry retains every prior entry and the incomplete global
coverage declaration. The original article-only parent keeps its historical
missing-axis metadata; the separate context and family entries describe the
additional evidence. Unsupported surface keys prevent exact surface reuse but
cannot establish canonical families for those three unresolved forms. Full
source sentences, other historical sources and independent qualification remain
open. The [numeric receipt](2026-10-28-q6-word-history-families-evidence.json)
binds the corpus archive, audit code and pinned dictionary. No APK, policy,
model or phone was changed.

The portable historical fixture revalidated after the ledger update. The final
Python stdlib profile passed 686 tests across 123 modules; 53 focused ledger and
preparation tests also passed. The first full run failed an old snapshot test
that assumed exactly 13 entries with unsupported surfaces; that test now checks
the original 13 separately and verifies the new quarantine and unresolved parent.

## Synthetic label compatibility

The archived word-ranking manifest binds its original selector, and the tracked
frequency file matches its recorded SHA-256. Using that exact selector and a
separately hash-verified archived refinement helper candidate, the
`audit_wordrank_synthetic_labels.py` check reproduced all 9,000 row IDs,
partitions, split labels, edit counts, synthetic cohorts, operations and typed
forms. The distribution is 1,500 unchanged, 3,000 one-edit, 3,000 two-edit and
1,500 three-edit rows. Partition files concatenate byte-for-byte to the audited
all-rows file. Two final audit outputs matched byte-for-byte; three focused
tests, including altered row fields and duplicate identities, passed in the
working checkout and in a clean source export with no `build/` directory.
The check executes only selected functions and constants from the two verified
source files, and is included in the CI test workflow. Raw local results are
under `build/ci-editing-investigation/q6-wordrank-label-audit-final-*.json`,
`q6-wordrank-label-audit-tests-final.log` and `q6-wordrank-label-no-build-final.log`.

The original word-ranking manifest does not bind the imported refinement
helper's bytes, so the candidate's matching output does not establish its
historical runtime identity or prove a training run. The corpus was already
disclosed and its generated errors are synthetic; this is not natural typo
qualification, complete source-text provenance or a new holdout. The global
registry and independent qualification remain incomplete.
