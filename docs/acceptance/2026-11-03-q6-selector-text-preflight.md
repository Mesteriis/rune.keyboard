# Q6 selector text preflight, version 1

Historical selectors remain blocked from publishing new text while the
registries are incomplete. A separate, versioned diagnostic now examines the
actual emitted text, as well as optional word rows, against the lexical and
control registries. It includes regression, protected and punctuation contexts
in both cleaned and source text, exact surfaces, article/source segments,
dictionary families and split overlaps. Partial source tokens, unknown words,
truncated words, ambiguous Unicode mapping and duplicate articles are reported
or rejected. Multiple overlap axes may count the same occurrence; the aggregate
is a count of overlap signals, not distinct records or errors.

The file wrapper requires exact JSONL and manifest hashes, a source shard
matching the selected lock, both registry snapshots, a dictionary receipt and
helper hashes. It checks those inputs again after reading and emits a bound
report without writing or publishing a corpus. The CLI uses the tracked source
lock; callers of the library must verify the bound lock against their own
trusted lock. Bindings identify inspected helpers, not a complete transitive
software supply chain. A clean result still reports `BLOCKED_COVERAGE` and
`publicationPermitted: false`. Independent labels and eventual completion of
the historical registries require separate evidence. No existing collector or
historically bound verifier was changed.

A diagnostic with the retained refinement text archive and its exact ru-0007
source inspected 1,069 articles; word-row inputs were deliberately empty. It
returned `BLOCKED_OVERLAP` with 88,059 historical and 44,042 cross-partition
overlap signals, 13,094 source-token fragments, 17 truncated endings and
10,745 dictionary-unresolved surfaces. The installed dictionary receipt hash
was `dc4745f9ac4d89dfc60f201cc2c1845d3ffa7d4197f6da6cf5e3c7d33c3596de`;
it differs from the earlier pinned receipt, so these counts are diagnostic and
not a replacement for the earlier pinned-dictionary result. The first bound
run correctly failed on input drift when its analyzer was edited during the
run; the repeat above completed against unchanged inputs. Neither run qualifies
any data or model.

Eleven focused tests pass, including altered source/proposal, source and
mutable-dictionary drift, absent/duplicate source, protected/punctuation
contexts, compounds, truncated and unresolved words and split overlap. The
historical boundary verifier passed its checks; a subsequent mistakenly named
extra command failed because that file does not exist. The new checker is an
intermediate component: source-bound finalization, actual collector integration
and a defensible complete-registry assertion remain unfinished.

The eleven focused tests also passed in a staged source archive without
`build/`. Task-created source archives, audit inputs and generated reports were
removed after use.

A subsequent standard-library inventory run passed 855 tests in 175 modules,
with no failures or skips (raw runner receipt SHA-256
`babce7395aa845ce82d577cf72ce389ef546a348083fbb88ff879f2a0f7bb0e2`).
The file-wrapper test module was added while that run was in progress, so its
five tests are covered by the separately passing eleven-test focused run, not
by the 175-module receipt. The runner itself exited zero; a separate shell
summary failed to sum a list-valued skip field, and the counts above were read
from the unmodified runner receipt before cleanup.

The diagnostic and its word-row source attestation now also reject fragments
joined by internal ASCII or typographic apostrophes, in addition to the existing
hyphen, digit, mixed-script and combining-mark checks. Before this correction,
`д'артаньян` could be split into apparently complete Cyrillic tokens and a word
row adjacent to an internal apostrophe could be attested. Standalone surrounding
ASCII or curly quotes remain acceptable. The live selector guard now also
rejects these joined fragments for registry-checked rows; its historical mode
preserves the original behavior. Historical verifier runs use the separately
archived guard bytes. This does not make collectors safe to publish or qualify
a corpus: the registry and text-admission blockers still apply.
Both diagnostic test modules passed (21 tests), including a staged source
archive without `build/`. The isolated historical text-boundary and named
regression checks also passed with their archived helpers and unchanged
registry bindings. No hosted CI or new corpus qualification is claimed.

After updating the live guard, the 19 selector tests and 21 diagnostic tests
passed both locally and from a staged archive without `build/`. The 25 corpus
preparation tests, 10 historical model-fixture tests, five historical-runner
tests and the isolated historical verifiers passed. The refinement, epoch and
truncated-source registration checks also passed. The new guard changes the
future source binding; it does not rewrite any historical receipt.

## Unicode format-character boundary follow-up

The live nonhistorical word selector accepted Cyrillic pieces adjacent to
Unicode format characters, including zero-width space, zero-width joiner,
word joiner and a bidirectional override. Before the fix, a focused test
reproduced four accepted fragments; the v1 text diagnostic also reported no
source-token fragment for zero-width joiners. The selector now rejects any
adjacent Unicode `Cf` character as an unsafe token boundary. Historical mode
retains its original behavior, and the archived v1 diagnostic is unchanged.

A separate v2 in-memory diagnostic adds a format-fragment blocker on top of
v1 without changing its historical source bytes. It still always refuses
publication and does not assert source identity or qualification. It is not
yet connected to a source-bound file wrapper or collector; complete text
admission and registry coverage remain open. The selector suite passed 21
tests, the v1/v2 text diagnostics 13 tests, and the new v2 and selector checks
also passed in a source-only archive without `build/`. The previous UniMorph
and both Wiktionary registry checks passed; the isolated suspended-retrieval
history runner passed six tests and its registration check. The initial
diagnostic test invocation used an unmatched `-k` filter and exited 5 with no
tests; the correct pre-fix invocation reproduced the failure. No independent
qualification, full stdlib inventory or hosted CI is claimed.

## Bound file diagnostic for format characters

`selector_text_preflight_files_v3.py` adds the v2 format-character check to
the existing source-lock-bound Parquet diagnostic. It retains only selected
article text in memory, keeps the previous word-row attestation and blocking
states, and never permits publication. The new report binds its additional
helpers and decoder identity, then rechecks captured data, source, dictionary,
decoder and both old and new helper hashes after the second assessment.
Historical v1/v2 readers remain unchanged. The caller must still establish
trust in the source lock; package file hashes do not authenticate the PyArrow
wheel or its complete native dependency chain.

Six new tests use real synthetic Parquet to verify a zero-width joiner,
duplicated and changed source, and input, decoder, old-helper and new-helper
drift. All 27 file-diagnostic tests across v1–v3 passed from a staged source
archive without `build/`, with Python 3.12.14 and PyArrow 25.0.1. The earlier
24-test run passed before the extra drift checks. Inventory validation passed;
the temporary source archive, environment and dependencies were removed.
The scientific profile includes the v3 tests. No actual public shard, collector
admission, full scientific profile, hosted CI or independent qualification was
run for this change; nonempty new selector texts still fail closed.

## Real-shard format diagnostic

At `1bc532b4`, the public ru-0007 Parquet source was downloaded into a
temporary directory and matched the locked 170,922,988 bytes and SHA-256
`39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88`.
After the historical fixture verifier passed, the v3 file diagnostic read
the retained refinement text: 888 train, 97 dev and 84 test articles. Word
row inputs were deliberately empty and the temporary manifest was adjusted
accordingly. Python 3.12.14 used PyArrow 25.0.1 and the hash-locked Pymorphy
requirements; the PyArrow wheel and external native dependencies were not
independently attested.

The report returned `BLOCKED_OVERLAP`, 102,750 historical overlap signals,
44,042 cross-partition overlap signals, 55 format-fragment occurrences,
13,165 other source-token fragments, 17 truncated endings, no unmapped source
fragments and 10,745 dictionary-unresolved surfaces. Overlap axes can count
the same occurrence more than once; these numbers are not distinct rows or a
quality measurement. Source bytes matched the supplied tracked lock, while
the report retained `sourceDecoderAttested: false` and
`publicationPermitted: false`. No word-row provenance, labels, new data or
model was qualified. The temporary source, corpus and environment were removed;
the tracked checkout remained clean.

## Collector format-boundary check

The maintained refinement, word-ranking and extra-epoch collectors now check
each selected text against its actual source before appending it. In the
nonhistorical path, source-mapping errors, Unicode format characters adjacent
to emitted Cyrillic fragments and a final token cut in the middle cause an
explicit refusal before the output directory is created. The shared helper is
bound and rechecked in the selector input snapshot. The v2 text diagnostic and
v3 file diagnostic use and bind that same helper. Historical reproduction
continues to use its original selection, and the separate final guard still
rejects all nonempty unchecked text; this format check does not establish
family, context or source-label independence and does not authorize a corpus.

An actual three-collector synthetic test exercised the nonhistorical path and
confirmed that each rejects a zero-width joiner without creating output. Its
first attempt failed before reaching that check because the macOS temporary
path alias was not resolved; after correcting the test root, all three paths
passed. From a staged source archive without `build/`, the collector test,
22 selector tests, 13 text-diagnostic tests and 27 file-diagnostic tests passed
using Python 3.12.14 and PyArrow 25.0.1. The fixture verifier and seven
historical-data tests passed, as did 12 packaged-provenance tests and its live
path audit. The temporary archive and environment were removed. The PyArrow
wheel was not independently hash-attested. Both isolated historical boundary
and suspended-retrieval runners also passed with their archived helpers. Full scientific/stdlib inventories,
hosted CI, fresh independent qualification and general text admission remain
open.

## Complete source-token check in collectors

The initial collector check detected Unicode format characters and cut endings,
but accepted cleaned text whose source contained a combining mark, a hyphen,
digits or adjacent Latin letters. The full v1/v2 text diagnostic already
reported these as source-token fragments; the gap was in the collectors' earlier
pre-append check. The nonhistorical collector path now applies the existing
whole-source-token rule to every selected fragment after the existing source,
format and truncation checks. It returns `SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN`
before writing output. Historical mode retains its original behavior; the
final unchecked-text publication refusal remains unchanged.

The three actual collector paths each rejected synthetic combining-mark,
hyphenated and digit-joined source fragments, as well as the existing zero-width
case. The 22 selector tests, 11 original text-diagnostic tests and three v2
diagnostic tests passed. A real Parquet fixture confirmed the existing bound
diagnostic reports combining-mark, hyphen, digit and Latin-adjacent fragments;
10 v2 and seven v3 file-diagnostic tests passed with Python 3.12.14 and PyArrow
25.0.1. An initial attempt with the system Python failed to import PyArrow; it
was not counted as a pass. The collector and v2 tests also passed in a staged
archive without `build/`. The temporary archive and Python environment were
removed. The isolated historical text-boundary and suspended-retrieval checks
passed with their archived helpers. This does not certify fresh source labels,
complete exclusion coverage, decoder supply chain, or independent quality.

## Full inventory after collector integration

At `e35f00bc2df02b132ba397236382ae03ecd4ffae`, a clean temporary clone with
the pinned llama.cpp submodule and no initial `build/` ran Python 3.12.14
inventories. The stdlib profile passed 194 modules and 945 tests, with zero
failures, errors, skips, expected failures, unexpected successes, timeouts or
missing receipts; its receipt SHA-256 was
`c0c3c679b592c56124d536b9acbb8dcce4768bb2e32dff934c06804d96851b08`.

After the historical fixture tests, restoration and source/model checks, the
Pymorphy backend gate passed. The scientific profile passed 25 modules and 96
tests, with zero failures, errors, timeouts or missing receipts and one skip:
`test_mlx_loss_parity_initialization_and_finite_gradient` requires an MLX
environment. Its receipt SHA-256 was
`f51098dcd2492bc3f05586438749cd5e2a237dc93e0e3c1ca06f9489de9ae484`.
MLX was not separately run at this source. The checkout remained clean and the
temporary clone, dependencies, restored fixtures and outputs were removed.
These are local checks, not hosted CI, device acceptance or qualification.

## Full inventory after complete-token collector check

At `cdaa2fbaf941ea4ffa19a02c038274caeb6c5087`, a clean temporary clone with
the pinned llama.cpp submodule and no initial `build/` ran both inventories on
Python 3.12.14. The stdlib profile passed 197 modules and 959 tests with zero
failures, errors, skips, expected failures, unexpected successes, timeouts or
missing receipts. Its receipt SHA-256 was
`a4b38367edca77fad871a1d434ac799c9c2e88575da00e74182ce28295a492a5`.

The declared scientific and hash-locked Pymorphy dependencies were installed;
the Pymorphy backend gate, historical data tests/restoration, model source and
fixture checks, and synthetic-label audit tests exited zero. The scientific
profile passed 25 modules and 97 tests with no failed modules, failures, errors,
timeouts or missing receipts and one skip. The aggregate did not retain the
skipped test's identity, so it is not asserted here. Its receipt SHA-256 was
`660871f384b904ea633ff0dfb46063fdf1e4248726d8454151d78c567842fa7d`.
The checkout remained clean. Temporary checkout, installed dependencies,
restored fixtures and outputs were removed. No hosted CI, Fold or independent
qualification is claimed; MLX was not separately run in this step.
