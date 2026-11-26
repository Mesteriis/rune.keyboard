# Q6 training/evaluation collector registry gates

The maintained refinement, word-ranking, additional-epoch and retrieval
preparers now use the permanent-registry gate. Default execution refuses
incomplete historical coverage before importing Parquet or reading requested
corpus inputs. Row construction, quota/leakage checks and the final shared gate
precede creation of output directories. Existing row-generation algorithms and
source/label checks are retained.

The explicit historical option marks new manifests and CLI summaries as
disclosed regression scope, with no new independent qualification. Original
source bytes for all four preparers are retained by exact digest and original
path in the frozen archive. Existing data manifests and both exclusion ledgers
are unchanged.

Historical data/source verification and ranker-window recovery now use the
shared source identity reader. The expected digest still comes from the
original pinned receipt: a changed maintained script can only be substituted by
an archive with that exact digest and original path. Wrong origins, modified
archives, unsafe names and symlinks fail. The reader does not execute archived
code. Original provenance keys/digests remain intact instead of being rebound
to the changed collector.

The packaged-provenance guard initially refused the changed refinement producer,
as expected. Its original model receipt digest is retained with one explicit
exact-archive mapping; unknown replacements still fail. Twelve guard tests pass
on each Python 3.12/3.14, including corruption refusal for both approved archives.
The actual packaged-provenance audit passes. No packaged provenance is rewritten.

Actual verification:

- All 13 maintained spelling/joint/refinement/word/epoch/retrieval CLI commands
  refuse incomplete coverage before intentionally absent source inputs are
  opened; no output is created.
- Collector tests: 7 on each Python 3.12/3.14. Source identity tests: 4 on each.
- Historical data fixtures: 7 tests; historical model source audit: 5 tests.
  These verify retained original corpus bytes, source identities and exclusions;
  they do not regenerate the full natural corpora.
- Full stdlib: 114 modules / 603 tests, zero failures/errors/skips.
- Scientific: 19 modules / 72 tests, zero failures/errors and one explicit
  MLX-environment skip.
- CI tooling: 41 tests pass, including the expected timeout-refusal probe.

See the [source/evidence receipt](2026-10-28-q6-training-collector-gates-evidence.json).
Reproduction documentation and the test inventory are updated. This closes the
identified direct collector bypasses, not the whole generator inventory:
evaluation/promotion drivers and other corpus entry points still require scope
checks. Missing canonical families, historical lineage and fresh independent
qualification remain open. No model is trained and no APK is changed.
