# Q7: current-product replay and required backend checks

The current source ran the same local replay command used by the CI workflow.
Both independent double runs were deterministic and matched their frozen
projections: 2,160 multilingual label-free rows and 12,000 historical spelling
rows, with zero differing rows. Timing fields are excluded by the frozen
projection; this is not a performance or fresh-holdout quality measurement.

The corpus generator and both permanent exclusion registrations passed their
checks; ten replay tooling tests passed. The pinned MLX CPU backend passed all
seven required cases without skips. The separately pinned Pymorphy backend passed
all five required cases without skips. An initial offline MLX dependency resolve
failed because the pinned NumPy wheel was absent from that cache; installing the
pinned requirements through the package registry resolved it, after which the
actual gate passed.

[Numeric evidence](2026-10-29-q7-current-replay-evidence.json) binds the source
commit, replay projection and receipt hashes and backend versions. Raw logs and
receipts are under `build/review-hosted-editor/` and `build/review-q7-*-20261029/`.
No physical device, model weights or app package was changed. This is local
execution, not a hosted CI rerun; Q7 and the full review remain open.

A subsequent fresh `./gradlew --no-daemon testDebugUnitTest --rerun-tasks
--offline` completed successfully on source `42dabd6c`: 1,390 app JVM tests and
19 runtime-llama JVM tests, with zero failures, errors or skips. Both module test
tasks appear in `build/review-hosted-editor/q7-fresh-jvm-20261029.log`; the XML
reports were counted separately. This does not replace the pending hosted and
Android-device checks.

## Current-source repeat

At `b7318582`, the CI product-replay entry point completed again with exit 0.
Both independent double runs were deterministic and matched their frozen
baselines: 2,160 multilingual rows and 12,000 historical rows, zero differing
rows and zero tolerated score differences. Corpus regeneration and both
disclosure checks also passed before and after replay. This was the local
controller path with no model calls; it does not establish a hosted CI result,
physical-device behavior or independent quality qualification.

The command log, receipts, comparison reports and observations remain under
`build/ci-editing-investigation/q7-replay-current` and its `-historical`
sibling. To avoid retaining approximately 544 MiB of generated output, the
six large JSONL observation/projection files were gzip-compressed after
verifying the decompressed SHA-256 against each original; receipt paths refer
to the uncompressed names and require decompression for direct reuse. The
rebuildable generated JARs were removed. No phone or model assets were changed.

## Repeat after expanded exclusions

At `3750ce9aa9efafe42faefc7f5c35a6ffb3e43cad`, a clean temporary checkout with
the pinned llama.cpp submodule and no initial root `build/` resolved the pinned
replay compiler offline and ran the CI replay entry point. Both two-pass
comparisons passed with zero differing rows and zero tolerated score
differences. The 2,160-row projection SHA-256 was
`e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`;
the 12,000-row projection SHA-256 was
`b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512`.
Both matched their corresponding frozen baselines. The disclosure checks ran
before and after each replay. The checkout remained clean and the temporary
checkout, compiler project cache and replay outputs were removed.

This is local model-free controller parity on disclosed corpora, not hosted CI,
physical-device acceptance or independent quality qualification.
