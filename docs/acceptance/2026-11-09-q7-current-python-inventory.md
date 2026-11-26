# Q7: current standard-library Python inventory

## Current JVM CI preparation

In a clean temporary local clone at `a35595b2`, with the pinned llama.cpp
submodule and no initial root `build/`, `./gradlew --offline --no-daemon
:app:testDebugUnitTest` exited zero. Its 139 XML reports record 1,401 tests,
zero failures, errors or skips. The tracked checkout remained clean, and the
temporary clone, output and build files were removed. This is a local JVM run;
it is not a hosted CI, Android instrumentation, full release or device result.

## Public-history preflight

At `03ad7b82`, Gitleaks 8.30.1 scanned the unpublished commit range from
`origin/main` to HEAD and returned exit 1 with 2,089 generic-key findings.
An isolated rescan identifies 2,014 as `surfaceKey` fields in the two
source-bound historical text projections, and one as a navigation receipt
name. Of the remaining 74 hexadecimal findings, 51 match the content of a
tracked source file in the corresponding commit; nine are explicitly labelled
hash values, including two raw-log digests; and the remaining 14 occurrences
all match `tokenizers.py` from a hash-locked morphology dependency. The latter
was checked in a freshly created Python 3.12 environment installed with
`--require-hashes`. This classifies the scanner's findings; it is not a proof
that the history contains no other secrets or private information. A separate
current-diff check found no private-key headers,
the connected Fold identifier, or machine home paths; it is not a general
secret or private-data audit. Scan outputs and temporary environments were
removed. No commits were pushed and no hosted workflow was run.

## Repeat after joint collector and Android gate changes

A temporary clean local clone at `c1cf4227` with the pinned llama.cpp
submodule and no initial `build/` ran the complete standard-library profile
using Python 3.12.14. All 197 modules and 965 tests passed with no failed
modules, errors, skips, expected failures, unexpected successes, timeouts or
missing receipts. The raw receipt SHA-256 was
`9a6658fbde6535aab71feb58301e2a595201a130fb055832adcf323238e57055`.
The tracked checkout remained clean and the temporary clone and outputs were
removed. This does not establish scientific-backend, Android, hosted CI,
physical-device or independent-corpus acceptance.

The initial invocation failed before starting tests because the pyenv shim did
not select Python 3.12; the successful run used the installed interpreter's
absolute path. The failed invocation's temporary clone was also removed.

## Repeat after Spanish control-surface exclusions

A clean temporary checkout of `96db00e8c8f60dadaa975e2b15c95be34d2be586`,
with the pinned llama.cpp submodule and no initial `build/`, ran the complete
stdlib inventory under Python 3.12.14. The runner exited zero: 196 modules and
953 tests, with no failed modules, failures, errors, skips, expected failures,
unexpected successes, timeouts or missing receipts. The checkout remained
clean. The temporary checkout and output were removed. This does not establish
hosted CI, scientific backend, physical-device or independent-corpus results.

A clean temporary clone of source `8dc604b1`, with its pinned llama.cpp
submodule initialized and no initial root `build/`, ran the versioned Python
inventory using Python 3.14.6. Inventory validation found 183 standard-library
and 24 scientific modules. The standard-library profile completed all 183
modules and 905 tests: zero failed modules, failures, errors, skips, expected
failures, unexpected successes, timeouts or missing module receipts. The raw
runner receipt SHA-256 was
`e1ab67e3c9e8d524cd61e197b5692e0585d2c802b9b0bbb4ebb73b8bb88cfdaf`.
The clean checkout and raw output were removed after recording the result.

A second clean checkout repeated the same inventory using the project-prescribed
Python 3.12.14. All 183 modules and 905 tests passed with zero failures, errors,
skips, timeouts, expected failures, unexpected successes or missing receipts.
Its raw receipt SHA-256 was
`024838cd2c40a36d457bc0d8681d6302e638579fd2b9b16e4123814825b7c510`.
The second checkout and raw results were also removed.

The inventory covers the versioned `tools/typing_experiments` and
`tools/morphology` modules, not all `tools/ci` tests. Seven separately invoked
CI-helper modules covering the new Tatoeba input and observed registrations,
phrase comparison, boundary Undo, post-Undo continuation, its registration and
the Android boundary report gate passed 29 tests in the main checkout on both
Python 3.12.14 and 3.14.6. These
are local tests; the 24 scientific modules, hosted CI, device acceptance and
independent qualification were not run as part of this check. Passing the tests
does not establish complete registry coverage or close Q6/Q7.

## Current-source repeat

At `ebe2fc6e`, a fresh temporary clone with the pinned llama.cpp submodule and
no initial `build/` ran the standard-library inventory again. Both Python
3.12.14 and 3.14.6 completed all 183 modules and 912 tests, with zero failed
modules, failures, errors, skips, expected failures, unexpected successes,
timeouts or missing receipts. The checkout remained clean and was removed.

In the main clean checkout, eight separate CI-helper modules passed on each
Python version: the six Tatoeba phrase/Undo registration and comparison
modules, the Android boundary report tests and the historical word-ranking
synthetic-label audit. Each version ran 37 tests with no skips. Logs, exit
codes and individual receipts remain locally under
`build/ci-editing-investigation/q7-current-python-clean`. This is not a fresh
scientific-backend run, hosted CI, device acceptance or independent corpus
qualification.

## Repeat after Taiga and neighbor exclusions

Two clean temporary checkouts of `b7d361bb869bb2e1a588764897e8d508ece8e7af`,
with the pinned llama.cpp submodule and no initial `build/`, ran the complete
stdlib inventory. On Python 3.12.14 the runner exited zero and reported PASS
for all 186 scheduled modules. Its aggregate test/skip counts were not retained
by this invocation and are not asserted here. On Python 3.14.6 the runner
exited zero with 186 modules and 925 tests, zero failed modules, failures,
errors, skips, expected failures, unexpected successes, timeouts or missing
receipts. Both clean checkouts and their outputs were removed.

Four CI-helper modules covering both neighbor registrations, ranking audit and
backend-gate refusal passed 14 tests on each Python version in the main clean
checkout. The backend-gate suite intentionally runs simulated failures and
skips to verify rejection; those probe outputs are not failed outer tests.
This is local stdlib/CI-helper evidence, not a fresh scientific profile, hosted
CI, Fold acceptance or independent qualification.

## Repeat after Wiktionary exclusions

A clean temporary clone of `750e9e44f752dec5a42dc71590b632d7129c6c68`, with
the pinned llama.cpp submodule and no initial root `build/`, ran the complete
190-module stdlib inventory with Python 3.12.14. The runner exited zero,
meaning every scheduled module returned zero and produced a nonempty test
receipt. The captured output was truncated before the aggregate counts could
be retained, so test and skip totals are unknown; this result does not assert
that there were no skips or expected failures. The checkout remained clean;
the temporary checkout and runner outputs were removed. Scientific tests,
hosted CI, Fold acceptance and independent qualification were not run here.

## Current stdlib inventory after v6 target recovery

At source commit `7676bc24`, the versioned stdlib runner completed all 202
tracked modules on Python 3.12.14: 987 tests, zero failures, errors, skips,
timeouts or missing module receipts. The runner exited 0. The only staged
change during the run was a separate public-history scan receipt; this was a
local run in the existing checkout, not a clean-source archive, scientific
profile, Android workflow or hosted execution. Temporary module logs and the
runner receipt were removed after their totals were checked.

## Current scientific profile in a temporary clone

At `91a8e343`, a temporary local shared clone using Python 3.12.14 installed
`tools/typing_experiments/requirements.txt` and the hash-locked morphology
requirements with `uv`. The inventory check and Pymorphy backend gate passed.
The CI historical-data, model-source and model-fixture tests, the synthetic
label test, and the corresponding fixture preparation steps all exited zero.
The scientific profile exited zero with 30 modules and 123 tests: no failures,
errors, timeouts or missing module receipts, and one skipped test. The skipped
test identity was not retained in the aggregate output. The clone, environment,
fixture outputs and raw logs were removed after the run.

This is a local macOS ARM64 run, not Linux hosted CI or Android acceptance;
dependency installation used `uv`, so it is not an exact workflow-shell repeat.
A passing test profile does not establish independent model qualification.
