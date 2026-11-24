# Q6: Unicode dash boundaries in future collectors

Before this change, the future selector admitted Cyrillic fragments adjacent to
U+2012 FIGURE DASH and U+2014 EM DASH, even though a hyphen between the same
words was rejected. A focused test reproduced both missed refusals. The live
selector now conservatively rejects adjacent Unicode `Pd` characters; a dash
separated by whitespace remains a valid boundary. The explicit historical
reproduction path still preserves its old behavior, and the final guard still
refuses unchecked new text.

The tests cover every `Pd` code point known to the active Python Unicode
database on both sides of a word, plus the historical path. The three actual
future collectors each reject both reported dash variants before producing an
output directory. The full 26-test selector suite and the collector test
passed in a staged source archive with no `build/`; after adding the exhaustive
Unicode test, that new test and the focused selector-boundary test also passed
locally. The archived historical text-boundary runner and suspended-retrieval
runner passed; they use their separately retained helper versions. The source
archive was removed.

The separate archived v1 text diagnostic's source-fragment predicate was not
changed and does not yet count every `Pd` variant. Its reports remain diagnostic
and always refuse publication; do not interpret them as complete dash-boundary
checks. Registry coverage, text admission, source provenance, independent
qualification and hosted CI remain open. The initial targeted test command
matched no method and exited 5; the corrected pre-fix run reproduced two failures.

## Versioned text diagnostics

The in-memory v3 diagnostic adds `sourceDashFragments`, counting each selected
source token adjacent to Unicode `Pd` punctuation. The bound Parquet v4 wrapper
records this count and the new diagnostic and previous format-helper hashes,
then rechecks data, source, decoder, dictionary and helper identities after
assessment. Both continue to refuse publication and do not claim decoder
attestation, source-label validity or independent qualification. The old v1/v2
and file v1–v3 sources remain available for their historical reports. Overlap
signals and dash-fragment counts are not counts of distinct records.

The new in-memory tests exercise all `Pd` characters in the active Python
Unicode database and a spaced-dash control. Six new file tests use synthetic
Parquet to cover detection, duplicate source and input, decoder, new-helper and
prior-helper drift. All nine tests passed on Python 3.12 with PyArrow 25.0.1 in
a staged source archive without `build/`. In the preceding temporary Python
environment, the existing diagnostic v1/v2 and file v1–v3 suites also passed
(42 tests); that earlier run of the new file suite contained three tests, before
the additional drift tests were added. Inventory validation passes with the new
tests assigned to stdlib and scientific profiles. The temporary archive and
Python environments were removed; no full profiles, real public shard, hosted
CI or qualification was run. The PyArrow wheel and its native dependencies were
not independently authenticated by this check.

The first inventory validation was run before the new test files were staged;
it correctly rejected them as stale inventory entries. After staging the files,
the same check passed.

For an authenticated source and prepared proposal, the new diagnostic can be
invoked with `python3 -B tools/typing_experiments/selector_text_preflight_files_v4.py
--data PATH --source PATH`. As in earlier versions, callers must independently
establish trust in the source lock and decoder supply chain. The diagnostic is
not yet an admission step in the collectors.
