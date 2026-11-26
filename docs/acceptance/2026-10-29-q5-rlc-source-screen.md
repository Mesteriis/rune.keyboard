# Q5: learner-corpus source screen

The public [RLC-GEC repository](https://github.com/Russian-Learner-Corpus/rlc-annotated)
and its [2024 paper](https://aclanthology.org/2024.lrec-main.1241/) describe
corrected Russian learner writing. The repository includes an MIT license; the
underlying authors' rights and reuse terms have not been independently audited.
Revision `c84fb2de7db3668c59cd8cda7f79642bc59d9ac3` was screened by aggregate
counts only using `tools/ci/screen_rlc_learner.py`. Its three CSV input hashes
and the auditor hash are in the generated report. Two executions produced
byte-identical reports; four unit tests pass. Source files and reports are
local ignored build artifacts. No individual text or row hashes were exported,
no product/model scoring was performed, and no rows were added to a registry.

The three tables contain 2,004 documents, 31,519 sentences and 41,410
annotations. Of 28,951 sentences with blank status, 14,443 have identical
original and corrected strings; 15 of those still have annotations. The
remaining 14,428 unannotated unchanged sentences cover 1,724 documents and
contain 67,061 lowercase Cyrillic tokens of length 2–6, with 5,797 distinct
surfaces. This is a mechanical potential-size screen, not proof that every token
is correct or that the sentences were comprehensively reviewed.

There are 6,998 annotations referring to 2,327 sentence IDs absent from the
published sentence table, all attributed to `rlc-errant`. This mismatch was
reported rather than hidden; it prevents treating the three files as a complete
joined annotation dataset. The corpus is learner writing rather than ordinary
native chat, and 639 document records name the RULEC subcorpus. Subcorpus
lineage, overlap with prior Rune sources, individual labels, rights and family
separation have not been established. It is neither an independent holdout nor
an approved training/evaluation corpus. Q5 and Q6 remain open.

Reproduce with `python3 tools/ci/screen_rlc_learner.py --source
build/q5-rlc-source-screen --output build/<new-output>` after obtaining the exact
three pinned files. Reports and the source bytes must remain outside tracked
files until the unresolved scope is addressed.
