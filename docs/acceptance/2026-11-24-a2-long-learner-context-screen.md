# A2 long-context source screen

The aggregate screen tested whether published human writing and its
corrected versions contain enough local, single-word edits after 300,
600 and 1,000 characters of original context. It used NFC normalization
and aligned word and punctuation tokens with Python's SequenceMatcher
with autojunk disabled. A candidate must be an aligned replacement of
one Cyrillic or Spanish word by one word in the same script, differing
by one insertion, deletion, substitution or adjacent transposition after
lowercasing. This also admits some grammatical and lexical edits.

## Russian RLC-GEC

The three CSV inputs matched the [existing pinned source screen](2026-10-29-q5-rlc-source-screen.md)
at upstream revision
[`c84fb2de7db3668c59cd8cda7f79642bc59d9ac3`](https://github.com/Russian-Learner-Corpus/rlc-annotated/tree/c84fb2de7db3668c59cd8cda7f79642bc59d9ac3).
All 2,004 document IDs had a contiguous sentence index and a sentence
count identical to the declared document count. Document offsets use the
original sentences in index order with one space between consecutive
sentences. This preserves preceding words and approximates the original
inter-sentence formatting. The screen retained only aligned edits from
sentence pairs with blank status. The corroborated view also requires
an annotation on the same sentence with exactly the extracted old and
new form. It checks form identity, without using annotation offsets.
The corpus authors describe the underlying material as learner writing.
[Source paper](https://aclanthology.org/2024.lrec-main.1241/)

| Selection | At least 300 characters | At least 600 | At least 1,000 |
| --- | ---: | ---: | ---: |
| Within the edited sentence | 32 edits / 19 documents | 2 / 2 | 1 / 1 |
| With preceding sentences from the same document | 4,245 / 1,231 | 2,858 / 873 | 1,766 / 515 |
| Document context plus matching annotation forms | 3,987 / 1,197 | 2,692 / 847 | 1,654 / 500 |


A stricter pass required a manual `ortho` or `misspell` annotation and
agreement with the aligned original token indices, the original form
and the published replacement. The source defines start and end in
tokens. This pass used original document offsets without NFC conversion
to preserve the source character positions. Counts are by tag and can
overlap across tags. [RLC annotation schema](https://github.com/Russian-Learner-Corpus/rlc-annotated/tree/c84fb2de7db3668c59cd8cda7f79642bc59d9ac3#rlc-gec)

| Manual tag with matching token span | At least 300 characters | At least 600 | At least 1,000 |
| --- | ---: | ---: | ---: |
| `ortho` | 639 edits / 322 documents | 459 / 226 | 271 / 129 |
| `misspell` | 19 / 14 | 11 / 9 | 6 / 5 |

## Spanish COWS-L2H

The screen used the five `csv/vacation.*.csv` files at upstream
revision [`ebb11724f258f3ed377a27ed34f08897a8e5639c`](https://github.com/ucdaviscl/cowsl2h/tree/ebb11724f258f3ed377a27ed34f08897a8e5639c).
The vacation prompt describes a hypothetical trip. The repository
describes the writers as L2 and heritage learners. The authors explicitly
describe corrections that include stylistic changes.
[Source paper](https://aclanthology.org/2020.lrec-1.894/)

| Source file | SHA-256 |
| --- | --- |
| `vacation.F17.csv` | `8136b1314443a88c8e7535430403477ad0ebd9b35f352558390e08c4f678ff22` |
| `vacation.S17.csv` | `4327ae3fe0d8106625408872fd197f7dd9a41ea061f5c8f594f2432810ce70a1` |
| `vacation.S18.csv` | `007abaecc2038c37172681581c03fc26b303a25d6c9f93be9363db9b6bde84b0` |
| `vacation.SU17.csv` | `ca04c829ba2f56b094cd27495d6761bc858ff0aa3ec0da62fc8ed5d6fb746933` |
| `vacation.W18.csv` | `c4c6418a6934569ca88ad76ed609c70c8e8d19023fd2debf6d10ffbb73f61216` |

The input bytes matched the five Git blob hashes. Across 820 source rows,
the first occurrence of each exact normalized essay was used. Of those,
329 have a published corrected version and 188 have two. The prefix
length is the code point offset in the unedited whole essay. Agreement
requires the same original span and replacement in both corrected
versions. Demographic fields are outside the measurement.

| Selection | At least 300 characters | At least 600 | At least 1,000 |
| --- | ---: | ---: | ---: |
| Edit in either reference | 1,896 edits / 309 essays | 1,408 / 286 | 742 / 233 |
| Same edit in both references | 626 / 152 | 458 / 137 | 243 / 109 |


## Candidate controls and intersections with existing exclusions

The control screen considered unchanged Russian sentences with blank
status and no joined annotation. In Spanish it required both published
references to preserve the original token and at least two aligned
tokens on each side. Both selections took alphabetic tokens of at least
two characters followed by whitespace. Counts use original document
offsets, with the same sentence join as above for Russian and NFC essays
for Spanish.

Every candidate was checked against the current disclosed surface keys
and the control context keys for regression, protected input and
punctuation. The Russian screen also queried lexical context keys.
The context comparisons used the full source prefix and the last 1,024
code points as a separate suffix. The checks used the current
`control_ledger.py` and `holdout_ledger.py` key functions and the
following registry SHA-256 values.

| Registry | SHA-256 |
| --- | --- |
| `control-ledger.json` | `fd4f7d9e76c2ce55b6f1180de375acbae3f97868cd520c91fe0bf1e6cff04e4a` |
| `holdout-ledger.json` | `db1093ede1b0fcfebf9112bec83a135eaf92d694ee89d344d3d65545702cac77` |

| Selection | At least 300 characters | At least 600 | At least 1,000 |
| --- | ---: | ---: | ---: |
| Russian candidate controls | 81,633 tokens / 1,405 documents | 66,537 / 1,096 | 51,088 / 722 |
| Russian after the checked exclusions | 31,018 / 1,339 | 25,696 / 1,042 | 20,044 / 700 |
| Spanish candidate controls | 13,029 tokens / 188 essays | 9,708 / 182 | 5,379 / 175 |
| Spanish after the checked exclusions | 5,218 / 188 | 3,882 / 182 | 2,159 / 171 |

All identified intersections were on the surface axis. At 1,000
characters the surface filter removed 31,044 Russian and 3,220 Spanish
token occurrences. That filter changes the distribution of words
available for false-change measurement. The remaining counts still need
manual verification of unchanged labels, source and author identities,
dictionary-family checks, and a sampling plan that accounts for multiple
words per document. The suffix check uses a fixed slice. The deployed
model uses a word-bounded UTF-8 window with hysteresis, which requires a
separate sequential replay to screen its actual emitted prefixes.


## English CPython documentation revisions

An exploratory screen queried GitHub's commit search for
`repo:python/cpython typo doc committer-date:2024-01-01..2025-12-31`
and inspected the 30 newest results of 84. It limited inputs to
existing documentation files under `Doc/tutorial`, `Doc/library`,
`Doc/howto`, `Doc/reference` and `Doc/faq`. It requires one deleted line
and one replacement line, unchanged text around a single changed
alphabetic word, and a one-character edit or adjacent transposition.
The line has to be unindented plain text. Both lines were verified
against the full parent and edited versions, and the edited file was
checked against its published Git blob identity.
[Search syntax](https://docs.github.com/en/search-github/searching-on-github/searching-commits)
[Python documentation license](https://docs.python.org/3/license.html)

| Verified change | Parent revision | File |
| --- | --- | --- |
| `b373d3494c587cf27b31f3dff89a8d96f7d29b9d` | `478b8dab0b40f08c3ded40bf988ec49a50f4c8fb` | `Doc/library/idle.rst` |
| `478b8dab0b40f08c3ded40bf988ec49a50f4c8fb` | `b1027d4762435b97546c122dd94290d707b3ff39` | `Doc/library/codecs.rst` |
| `9b5235b62ed85e4757f1530cd73ef8d318be6215` | `d22a7456443415961b93169b851ab7e550be8791` | `Doc/library/logging.rst` |
| `cd76eff26e5f700ffb715d9d096d2e28744d0594` | `24436629efa3f90c52fc2e8d1d4613ed70f6d389` | `Doc/howto/remote_debugging.rst` |

All four edits occur after at least 1,000 characters in the parent
file. The file offsets include documentation structure. A separate
contiguous plain-paragraph check found one edit after 300 characters
and zero after 600 or 1,000. These counts establish that the source can
supply authentic English edits, with sparse long plain-text context
under this screen. The register is technical documentation.

## Qualification status

The counts are nested thresholds and documents can contribute multiple
edits. A development sample from these sources can exercise authentic
long-input context. A qualification set still requires human spelling
labels, verified unchanged controls, author and dictionary-family
separation, clearance against all Q6 exclusions, and source-specific
reuse review. COWS-L2H declares Apache 2.0 at the repository level, while
the reuse scope of the constituent writing still requires verification.

A broader English source remains open. Cambridge's Write & Improve 2024 corpus supplies
document context under non-commercial terms. LOCNESS also has explicit
restrictions on distribution. These are source leads only.
[Write & Improve project report](https://www.repository.cam.ac.uk/items/ba155087-0754-4c6b-ade8-68858e1df2f0)
[LOCNESS provider](https://uclouvain.be/en/research-institutes/ilc/cecl/locness)

The screen consumed source bytes in memory and emitted aggregate counts
and input digests. Model scoring and corpus qualification remain pending.
