# Q6: selector training-text exposure audit

The word-row admission gate alone cannot establish independence of separately
emitted text. A diagnostic auditor now reconstructs each fragment from its
hash-pinned public article, checks both ledgers for article and surface keys,
checks lexical family, unsupported-surface and full-segment keys, and compares
source and family identities across partitions. It includes every complete
selector segment of each source article, including segments outside the emitted
fragment, so segment exposure is deliberately conservative. It never approves
a corpus; context-window and global historical completeness are not certified.

The inputs are the previously disclosed, explicitly intercepted selector runs,
not new independent corpora. Their input manifests and files are bound by hash;
the pinned source is checked before and after reading. Dictionary-only analyses
use the pinned dictionary. Numbers below are distinct keys unless otherwise
specified. Cross-partition counts combine the selected word rows and text; each
pair of partitions is counted separately.

| Measure | Refinement | Word ranking |
| --- | ---: | ---: |
| Text records and source articles | 1,069 | 430 |
| Distinct text word surfaces without dictionary analysis | 10,745 | 2,078 |
| Fragments cut inside a word | 17 | 4 |
| Text-source articles already in lexical registry | 1,069 | 430 |
| Text families already in lexical registry | 10,271 | 5,004 |
| Source-segment keys already in lexical registry | 863 | 7,443 |
| Text surfaces already in control registry | 837 | 377 |
| Family overlaps across partitions, text plus rows | 15,927 | 5,650 |
| Segment overlaps across partitions, text plus rows | 776 | 405 |

The all-article segment scope and reused public historical shard make these
diagnostic collisions unsurprising; they do not establish a false-change rate
or evaluate a fresh source. They show why the existing unchecked-text refusal
must remain until source extraction, exact contexts, unknown words and partition
separation are addressed. The auditor outputs only aggregate counts and input
identities; its report does not certify labels, safety or independent holdout.

Reproduce with `audit_selector_text_exposure.py --data <intercepted-output>
--parquet <pinned-ru-0007.parquet>` in the pinned PyArrow and Pymorphy
environment. Raw numeric reports are in `build/q6-text-exposure-*-final.json`.
Two independent runs for each input produced byte-identical reports.
The full stdlib inventory passed 772 tests across 153 modules without skips;
provenance-path and test-inventory checks and `git diff --check` passed. The
runner receipt is in `build/review-q6-text-exposure-20261028/`.
No application, model, phone, ledger or qualification threshold was changed.
