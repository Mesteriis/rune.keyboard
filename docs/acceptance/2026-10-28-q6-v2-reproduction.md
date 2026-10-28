# Q6: complete original qualification-v2 corpus reproduction

The v2 generator's later mixed-script fix can now be tracked while preserving
the original corpus reproduction. The original generator (`2cbcb250...`), later
guarded version (`ed9928d6...`) and source lock were already archived. The missing
original evaluator (`ad76b78b...`) was recovered from Git commit
`9c6ffd1b5c4edd093d1cf14fcb87c9502295bcbc`, blob
`5761eeba15dfe72849540b5607ecdc17f7e5dbf8`, matching the original corpus manifest.
Its raw bytes are now archived and catalogued, without editing that evaluator.

## Actual complete regeneration

A private projection of all three original sources ran on the three original
Wikipedia shards (`en-0019`, `es-0004`, `ru-0009`), all three pinned vocabularies,
the original training manifest/train/valid files and the original prior corpus.
All input identities were checked first. It regenerated all 13,200 rows and
matched the seven data files **and the entire manifest** byte for byte, including
the article-selection counts, source identities and validation statistics.
The first full generation completed in about 74 seconds on this local Mac.

The permanent `qualification-v2/reproduce_corpus.py` command independently passed
on Python 3.11.14 and 3.12.14 with PyArrow 25.0.1. Each invocation uses a fresh
source projection and output, requires all eight exact reference hashes and
rechecks original source/input identities afterward. It creates a success receipt
only after those checks. It never rewrites the live generator, frozen corpus,
corpus manifest or ledger. Neither a model nor a scoring runner is invoked.

## Mixed-script guard and CI

The original three generator tests plus the new mixed-script test ran against
the original generator: four tests, exactly one expected failure. Its regex
admitted the Cyrillic suffix of a token beginning with Latin `C`. The same test
passes against the guarded generator. The existing two-file owner patch is
integrated without changing its preserved bytes.

The full qualification-v2 suite passes all 11 tests on Python 3.12. Seven new
reproduction cases cover the complete reference set, modified archived source,
changed/missing/extra results, modified reference manifest, redirected catalogue
path, wrong Parquet before execution/output creation and symlink refusal.
Seven legacy-recovery and four early-source tests also pass. CI now discovers
all qualification-v2 tests; its workflow was parsed locally. Full generation
requires the original large inputs and is not claimed as a hosted CI run.

All original owner's 13 payload hashes and 98 paths are preserved; all eight
tracked corpus files and the existing ledger remain unchanged. The
[machine receipt](2026-10-28-q6-v2-reproduction-evidence.json) binds inputs,
original source lineage, all three successful full reproductions, tests and logs.

This proves the original v2 corpus's complete data generation path. It does not
make revealed v2 data fresh, qualify an Android policy, prove other historical
corpora or resolve the remaining canonical-family/role-feature/left-sequence and
authorship gaps. Q6 and the overall review remain in progress.
