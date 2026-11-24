# Q6: public word-ranking and additional-epoch target windows

The verified public historical archives and pinned Russian Wikipedia parquet
were matched back to their source using each original selector's identity. All
10,500 rows matched; every matching occurrence was retained. The four added
ledger entries contain only article and source-window hashes. They do not claim
full sentence coverage or complete historical lineage.

| Corpus | Rows | Distinct source windows |
| --- | ---: | ---: |
| Additional epoch test | 1,500 | 1,499 |
| Word ranking train | 6,000 | 6,014 |
| Word ranking dev | 1,200 | 1,199 |
| Word ranking test | 1,800 | 1,800 |

Multiple rows can share the same normalized window, and one row can match more
than one occurrence. All four sets were absent from the prior sentence-key
union. The original 135 ledger entries and the coverage status are unchanged;
there are now 139 entries. The article and target-context exclusions in the
parent entries remain necessary. See the adjacent machine-readable receipt for
input identities and counts. The parquet is a local pinned public source and is
not included in the repository.

Reproduction from the previous ledger requires the verified fixture archives,
the pinned parquet and PyArrow. Run `import_word_epoch_windows.py --base
<previous-ledger> --output <new-directory>` using the project Python environment.
The importer verifies fixture and source identities, validates every row and
parent article, rejects missing or duplicate articles, retains all matches and
checks input hashes after scanning. It performs no model calls. Existing Q6
lineage gaps and independent qualification remain open.

Verification: two independent importer runs produced byte-identical ledger and
receipt; the fixture verifiers accepted all 31 model and 15 data payloads.
The focused recovery suite passed 7 tests. The Python stdlib inventory check
passed and its full 123-module run passed 690 tests with no skips. `git diff
--check` passed.

A subsequent hardening step verifies the passed base ledger's two parent entries
against the exact archive-derived entries, and snapshots input hashes before
fixture verification. The regenerated ledger preserves all earlier entries and
all four sets of window keys; only the importer binding changed. Two fresh runs
again produced identical ledger and receipt bytes. An actual base-ledger parent
binding mutation failed with `WORD_EPOCH_PARENT_IDENTITY` before creating output;
the updated focused suite passes 8 tests. The 690-test full-suite result above
predates this hardening step.
