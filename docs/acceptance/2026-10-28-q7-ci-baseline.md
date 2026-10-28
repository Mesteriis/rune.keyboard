# Q7 — fixed licensed CI corpus and baseline

The source corpus, generator and disclosure identities were committed as
`3fb4000` before the new corpus was replayed. The 2,160 label-free inputs adapt
three exact FrequencyWords 2018 files under CC BY-SA 4.0. Full pinned source bytes,
URLs, SHA-256 values, attribution and modifications are retained under
`tools/ci/product-replay-v1/`; no `build/` recovery or network is required to
reproduce the input bytes. Selection is deterministic and does not inspect model
results. The synthetic frequency-list contexts are not natural sentences;
frequency and generated transformations do not establish spelling correctness.

The new corpus has 540 source groups and 720 rows per language. Three regression
entries preserve exact context and prefix-independent surface exclusions, while
the RU lexical entry also preserves normalized contexts and unproven-surface
quarantine. Unknown canonical families, article and sentence axes remain
explicitly unresolved; neither global registry coverage nor fresh qualification
is claimed. Original historical entries are preserved. Shared preparation checks
now reject disclosed surfaces despite case, whitespace, prefix or claimed-family
changes. Both old control namespaces keep their original identity hashes.

At the corpus-freeze checkpoint, all 40 corpus commands passed with input/source
SHA-256 bindings unchanged before/after execution. The final expanded set has
41 passing commands and 218 unit tests, including ten CI corpus/gate tests.
This includes six new corpus tests and a
minimal copied-tree subprocess check without `build/` or network-dependent code.
The observer pipeline finishes 121 tests, zero failures/errors, one disclosed
legacy scored-export conditional skip. Gzip and plain baseline decoding have
identical projections, bounded to 1 MiB per line and 256 MiB per file.

## Fresh capture

A clean checkout at `3fb4000`, without the legacy GGUF or scoring executable,
compiled the actual observer and ran two separate JVM processes on all 2,160
inputs. Both projections match SHA-256
`e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`.
The capture records 42.2 seconds compilation and 57.1 seconds total on the local
host, not hosted Ubuntu performance or cold-cache measurements.

The 26,364,565 canonical UTF-8 bytes are preserved losslessly as a 1,154,198-byte
`baseline.jsonl.gz`, with filename/timestamp-free gzip headers. The exact two
existing top-level host timing fields are excluded; all other observation fields
remain. `baseline-manifest.json` binds the compressed bytes, canonical projection,
input manifest/rows, source commit and historical source/asset identities, with
this acceptance link. The baseline is a separate commit after corpus freeze.
It is a regression reference, not a correctness label or new policy permission.

The CI entry point validates corpus bytes and both disclosure registries before
and after the real two-pass comparator. It does not automatically update a
baseline or require candidate production sources to retain historical hashes:
behavioral drift must fail the comparator and expose its row/JSON-pointer diff.
Changes to corpus/baseline require a separate reviewed version/update with an
acceptance link. The prior 12,000-row threshold mutation proof remains a distinct
receipt; it is not relabeled as a mutation of this new corpus.

[Corpus attribution](../../tools/ci/product-replay-v1/NOTICE.md),
[portable runner contract](../product-replay-ci.md), and
[prior parity/mutation evidence](2026-10-28-q7-portable-replay.md).

## Historical profile and actual Ubuntu execution

The CI entry point also runs the original versioned spelling/protected corpus:
12,000 rows, 4,000 per language, with its own separately attributed baseline.
Its canonical capture is the new `871ee8d` capture already documented in the
portable-replay receipt. All 90 compiled core/observer sources and 69 assets
were rechecked unchanged before adopting that snapshot. The historical profile
retains its original authored-data licensing scope and has three additional
multilingual regression disclosures plus RU surface/context quarantine. It does
not inherit the separate FrequencyWords corpus license or become fresh data.

The real two-profile CI command ran on local **Ubuntu 24.04 / ARM64** with
JDK 17, two CPU cores and 4 GiB. Both profiles ran twice and matched their
baselines: **14,160 rows per pass**, zero differences. The whole component took
184.84 seconds. The 2,160-row driver records 11.62 seconds compilation / 25.79
seconds total; the 12,000-row driver records 11.24 / 148.48 seconds. Additional
wrapper validation accounts for the rest. Compiler-cache JARs were byte-identical
to the pinned Gradle artifacts; the Android compile stub was copied unchanged.
This was the parity component with a prepared cache, not a complete Gradle/JVM,
native-build or hosted `ubuntu-latest` workflow, and is not cold-cache evidence.

Containers had network disabled, no capabilities, no-new-privileges, and read-only
source/cache/SDK mounts. Only their dedicated output mounts were writable. The
base JDK image was pinned by immutable digest; runtime/platform metadata and
actual Docker resource/mount settings are retained privately. Project source was
mounted into the local VM, not copied into an image or uploaded to a registry.

A second isolated Ubuntu variant changed only the short-source margin literal
to 1,000,000.0. The actual CI command exited **1**, with two deterministic mutant
passes and **160 differing rows** in the first 2,160-row profile. Its JSON-pointer
row diff is retained; the fail-fast wrapper did not run the historical profile
after that failure. No fingerprint/admission gate was bypassed. The main source
and original source bundle retained the original threshold bytes. Both task
containers and the task image were removed; raw evidence remains private.

The workflow invokes this two-profile parity component after the fresh Gradle
unit tests in the same job, then uploads both outputs with their attribution.
The remaining complete tools test jobs/heavy-dependency separation and actual
hosted Ubuntu workflow execution remain open for Q7. No push, hosted-CI success,
phone update or product admission change is claimed by this slice.

[Machine-readable CI baseline evidence](2026-10-28-q7-ci-baseline-evidence.json).
