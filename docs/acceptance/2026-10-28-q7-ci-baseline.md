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

## 2026-11-23 clean host replay and unit tests

Clean local checkouts of `8b721f2bbe4bfc985f202430314250f82a17a840` on
macOS ARM64 started without root `build/` outputs. The pinned llama.cpp
submodule was used for the fresh JVM build. Gradle executed all 43 tasks for
`:app:testDebugUnitTest --rerun-tasks` in 59 seconds and returned zero. The
139 XML reports contain 1,413 tests with zero failures, errors or skips.

The standalone Gradle resolver checked all five compiler JARs from the pinned
toolchain. The workflow's `product_replay_ci.py` command used JDK 17 and that
toolchain. Each corpus ran twice and matched its tracked baseline exactly.

| Corpus | Rows per pass | Differing rows | Tolerated score differences | Projection SHA-256 across both passes |
| --- | ---: | ---: | ---: | --- |
| FrequencyWords | 2,160 | 0 | 0 | `e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea` |
| Historical multilingual | 12,000 | 0 | 0 | `b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512` |

The replay driver reported 21.47 and 65.85 seconds respectively, including
8.87 and 9.03 seconds for compilation. The separate rejection control changed
the active short-source margin from `0.24699818316768785` to `1000000.0` in a
disposable clone, preserving the frozen qualification fingerprint. Both mutant
passes agreed with each other. The comparator returned exit 1 with 160
row-level differences in the first profile, and the wrapper stopped before the
historical profile. The first mutation setup attempted to match the literal
alone and stopped before writing because the frozen fingerprint contains the
same value. The executed variant matched the active declaration exactly.

The local Python 3.12.14 runs used the workflow's shell steps in order. The
standard-library profile passed all 14 steps and all 1,037 tests in 210
modules, with zero failures, errors, skips, timeouts or missing receipts. Its
receipt SHA-256 is
`220a6425ca6aa52ef3d5ec572b65010bbe454411e8c6286908806a1950fc8c6a`.
The scientific and MLX dependencies were preinstalled in separate environments
using cached wheels. The Pymorphy install used its hash-locked requirements.
The scientific profile restored the original public-data fixtures into its own
checkout, then ran 30 modules and discovered 124 tests. It passed 123 and
skipped the MLX parity and finite-gradient test, which passed under the
dedicated MLX CPU job. That job passed all seven tests and the live Pymorphy
job passed all six tests. There were no failed modules, errors, timeouts or
missing receipts. The scientific receipt SHA-256 is
`284351c504915e2b101579dfed77c3381a48cecde961c0e2f0f74703fadf7bd1`.
The hosted checkout, setup and artifact-upload actions were outside this run.

`actionlint` 1.7.12 returned zero for the current workflow files. Its first
offline invocation stopped before analysis because the module was absent from
the local cache. The successful invocation used a temporary Go module and
build cache.

The latest hosted `ci` run visible on 2026-11-23 is the
[failed run for `2c1ff975`](https://github.com/Mesteriis/rune.keyboard/actions/runs/40680972358).
Its previous-source replay and both Android boundary jobs failed. Hosted CI
on the current source and physical-device acceptance remain open.
The temporary checkouts, environments, caches and raw outputs were removed
after verification.

## Current clean stdlib repeat

At `d46c8668`, a clean checkout with the pinned llama.cpp submodule and
Python 3.12.14 passed all 13 remaining shell steps for the CI stdlib profile.
The isolated module runner completed 1,048 tests across 210 modules with no
failures, errors, skips, timeouts or missing receipts. The preceding CI
steps executed 103 additional unittest cases and the workflow's standalone
source and documentation checks. The module runner receipt SHA-256 was
`77ce3c2ccc2fcf4a5c76962122804010cc6c75b5c39367c75166f3c659e702f0`.
The source, output and logs were removed after verification. This repeat
covers the stdlib shell steps on macOS. Hosted actions and the scientific,
JVM, replay and Android jobs have separate evidence.

### Clean stdlib repeat through the supervised v2 recovery

At `84618831`, a clean checkout with the pinned documentation submodule
ran the 14 stdlib shell steps from the workflow under Python 3.12.14.
The first 13 exited zero. The initial local call to the last step failed
before Python startup because Bash received the unevaluated Actions matrix
expression. Running the resolved `stdlib` command exited zero. Its
isolated profile completed **1,074 tests in 210 modules** with zero
failures, errors, skips, timeouts or missing receipts.

The [verification receipt](2026-11-24-q7-stdlib-84618831.json) binds the
workflow revision, the original step results and the isolated module
receipt. The local report archive was verified before the temporary
checkout was removed. Hosted execution and later revisions have separate
acceptance requirements.

## Current clean scientific and MLX repeat

At `09636a26`, a clean checkout with Python 3.12.14, the pinned
scientific packages, and the hash-locked morphology requirements passed all
four local workflow steps after dependency installation. The workflow restored
the versioned historical data and model fixtures before running the scientific
profile. That profile discovered 124 tests in 30 modules. It passed 123 and
skipped the MLX parity and finite-gradient case because MLX lives in the
separate environment. The receipt SHA-256 was
`3f022db410c0fde1f6233e3c7aec11d5d3798b9a527f853f8af0da57afbb04e0`.

The live Pymorphy gate passed all six tests, with receipt SHA-256
`1e1a748fb245394cf775d78ed151a41bca78f5e970ea6297eed03a41b2fbef36`.
In a second clean checkout the pinned MLX CPU gate passed all seven tests,
including the skipped parity and gradient case. That receipt SHA-256 was
`4f7020adb937cda4ae3979721a19fef89f35f5e3905a001ce511022298f50ee3`.
Both local checkouts and environments were removed. Hosted workflow
execution stays open.

## Local replay and JVM checks on the CI candidate

Candidate `0ecfca8c951d2` and the pinned llama.cpp submodule were checked out
into a fresh directory. Offline Gradle with JDK 17 passed
`testDebugUnitTest --rerun-tasks`. Its 139 JUnit XML files record 1,413
tests with zero failures, errors or skips. The workflow replay-toolchain
resolver passed separately.

The production replay wrapper exited zero. Its success gate requires two
matching passes and zero differing rows against the frozen baseline for
both the 2,160-row FrequencyWords and the 12,000-row historical
multilingual profile. The retained local command summary captured the
first projection digest, `e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`.
The complete wrapper log SHA-256 was
`2d3f61a02711eba9dab69d41e238f741e07b735a19a3d9b36c433debfb0928f8`.

A second disposable checkout raised only the active short-word margin
to `1000000.0` and retained the qualification fingerprint literal.
The two runs agreed with each other. The baseline comparator rejected
160 rows, returned exit 1 and stopped before the historical profile.
The mutation remained in the disposable checkout. Both checkouts and
generated reports were removed. These are local runs on the exact
candidate source. Hosted execution remains open.

The latest published main-branch CI run was checked on GitHub Actions.
It completed with failure at `2c1ff9751e74`. The build and all three
Python jobs succeeded. Both Android boundary jobs and the current-product
replay step in the unit-test job failed. This run identifies the published
base. The local candidate evidence above covers `0ecfca8c951d2`.
[GitHub Actions run 40680972358](https://github.com/Mesteriis/rune.keyboard/actions/runs/40680972358)

## Recovered v6 registry and cold fixture replay

The corrected local stdlib profile on the `2b2d52dc` sources passed
1,083 tests in 210 isolated modules under Python 3.12.14. It reported
zero failures, errors, skips, timeouts and missing receipts. The profile
receipt SHA-256 was
`1fc65cc50a8e7004f1c2feeaafe40827cadf84de42d98edcb80d349509dd2f43`.
The earlier run across the integration edits reported three affected
modules as failed. The corrected run started after those fixes.

A clean checkout of candidate `2c8a2af925ba` started with both v3/v4
archives and both excluded v6 texts absent. The workflow replay command
regenerated both archives from the pinned public sources and verified
their original digests. The two v6 texts stayed absent. The exhaustive
test-inventory check, F-Droid data policy, numeric asset notice and
documentation links passed.

The same checkout passed 101 targeted tests across the available-v6,
article and target attribution, public ledger, archive identity and
historical control registration suites. The temporary checkout and
generated outputs from both runs were removed. Hosted execution remains open.

## API 37 follow-up suites on the v6 candidate

The Android sources, native runtime, QA fixtures and workflow are
identical in `0ecfca8c951d` and `2c8a2af925ba`. The v6 checkout used
the ordinary debug, instrumentation and Compose fixture APKs from
`0ecfca8c951d` after verifying all three against their recorded hashes.
The five CI follow-up commands exited zero on fresh, isolated ARM64
API 37 emulators.

| Suite | Verified result |
| --- | --- |
| Synthetic restart | Four passing write and reload phases for rejection and confirmed words |
| Editing process death | Both left- and right-context processes died and recovered with the foreign suffix isolated |
| Voice fixture | Five passing unavailable, enabled, gesture, stale and next-keyboard scopes |
| Chrome | Two passing native cases and both independent numeric DOM profiles |
| Night learning | Four passing fixture cases on a separate fresh night-window emulator |

The combined local receipt SHA-256 was
`0b4c30f9001755b03e0e5d664ea3e1c100816bac6acdf0b25dc437ac901c9969`.
Both AVDs, the dedicated ADB process, APK copies and raw reports were
removed. The API 37 general boundary run, hosted x86_64 execution,
physical Fold checks and natural scheduler dispatch remain open.

## API 26 follow-up suites on the v6 candidate

The same hash-checked APKs and unchanged Android source trees passed
all four API 26 follow-up commands on fresh isolated ARM64 emulators.
The restart receipt reports four passing write and reload phases.
Both process-death scopes passed, including the API 26 fallback
IME path. All five voice scopes passed. A separate clean night-window
emulator passed all four night-learning fixture cases.

The combined local receipt SHA-256 was
`49bf4fa78ad7ae57c622a94f9ccdd8e90286fb135cb3680fd7acd10ba823ea50`.
Both AVDs, the dedicated ADB process, APK copies and raw reports were
removed. These results cover the follow-up commands. The full
connected boundary runs and hosted execution have separate evidence.

## Exact Rune Text scoring on isolated candidate builds

Candidate `2c8a2af925ba` built the separate native-qualification
application and test APKs. The published Rune Text GGUF matched the
embedded 396,704,416-byte size and SHA-256 before and after private
ADB staging on both ARM64 emulators.

The first host verdict rejected the extra numeric instrumentation
bundle. On API 37, the raw JUnit output showed one passing case for
each of bounded scoring and private Binder. The repeat explicitly
verified the metric bundle and the JUnit identity sequence. Both
methods passed on API 26. Bounded scoring passed again on API 37.
The API 37 Binder repeat failed at the first replacement request,
`reply(2)`, with “Bounded model reply timed out” after the four-second
reply wait. The repeat records this as a test failure even though
the shell transport returned zero.

The repeat receipt SHA-256 was
`c44f02bb6d3ff8b2f1371bd8b39e8be2ea5723cfedb240fdbfdfc010619aaa1d`.
The private model copies, both AVDs, APKs and transient logs were
removed. API 37 Binder repeatability and the installed-model typing
and exact Undo path remain open.

## Fresh API 26 general boundary report

The connected general scope for `0ecfca8c951d` exited zero on the
isolated ARM64 API 26 emulator. The fresh JUnit report matched all
398 identities discovered directly from the instrumentation APK.
It recorded 339 passing cases, all 59 known skips, and zero failures
or errors. An independent comparison against the versioned skip
inventory confirmed exact equality.

The discovery SHA-256 was
`15ed9fc987589ae1f7d11d98b5129146e104588d4c09d44a5824eb513e2f2ec6`.
The JUnit report SHA-256 was
`79475e0e5b42239123c3f52bfb87e99f333e0a9e7402f17958e75bd5744508e1`.
The separate boundary scopes and API 37 run each have their own verdict.

The full API 26 invocation subsequently passed all 11 scopes. The
ten opt-in scopes added 24 executed cases with zero errors, failures
or skips. They cover personal admission, case rejection, confirmed
words, Compose, emoji memory, export navigation and picker,
qualification lifecycle and safety, and the native runtime.
The boundary policy receipt SHA-256 was
`94522a1e47f1eecbfce178c0d571e148219a5974e3ef453f61fa4dfaa5f90c35`.
The API 37 follow-up below has its own verdict. Hosted evaluation remains open.

## Fresh API 37 general boundary report

The connected general scope for `0ecfca8c951d` exited zero on the
isolated ARM64 API 37 emulator. The fresh JUnit report matched all
398 identities discovered from the instrumentation APK. It recorded
339 passes, 59 skips, zero failures and zero errors. An independent
comparison against the versioned inventory confirmed exactly those 59 skips.

The discovery SHA-256 was
`ed85cee9d6cc6dcfb863a4537095d5d8afb9223cee12b8978585aa40c1702b9e`.
The JUnit report SHA-256 was
`a649bcd34ae0962b58f1d093b76dba11f831b1bc50ebfc340c3428144e2f132e`.
The full API 37 invocation subsequently passed all ten scopes. Nine opt-in
scopes added 23 executed cases without errors, failures, or skips. Each
fresh JUnit count matched the boundary policy receipt. The opt-in scopes
covered personal admission, case rejection, confirmed words, Compose,
emoji memory, export navigation, qualification lifecycle and safety,
and native runtime. API 26 separately covers the platform-specific
document-picker scope. The API 37 policy receipt SHA-256 was
`e298257525c04bc1dccb795d18dbc7f20a28486f31c0d0b38330bc846e8f3323`.
The isolated emulator and checkout were removed. The release-native Binder
repeat and hosted evaluation have separate acceptance checks.

## API 37 Binder request trace

A disposable qualification build of `2c8a2af925ba` added numeric
worker tracepoints around preparation, submit, cancellation, queue
admission, scoring and the watchdog. The exact GGUF passed host and
private-file hash checks. Each of four repetitions canceled request
1 and successfully scored its successor, request 2. The original
successor reply timeout was not observed in these repetitions.

Three complete repetitions passed. In the other repetition, request
4 returned `UNAVAILABLE` after the nine-second refill wait. The
trace shows its submission without queue entry and no watchdog event.
This establishes the location of that refusal. It leaves the earlier
successor timeout and the precise reason for request 4's refusal open.
No runtime limits were changed in the disposable build. The trace
receipt SHA-256 was
`61015a41697fe9d4c58da923b1169465f0af5040e2ec894d89d060b6ee67a5ad`.
The instrumented checkout, model, AVD and raw logs were removed.

An eight-run admission trace then identified the later refusal. All
eight first successors scored successfully. In the one failed warm
case, the worker had 67,538 credit units at request 4. The real
admission floor is 112,500. The other seven tests passed. The trace
receipt SHA-256 was
`adab55b00fefa4e6687dad99912e9c1e8736900de8c27e6c47e15be5be53f2f4`.

The instrumentation test now tracks a conservative credit bound
from the same UID's service CPU usage and the existing refill rate.
It preserves the nine-second minimum wait and fails if sufficient
credit has not returned within 50 seconds, before the 60-second idle
unload. It sends one warm request through the production Binder and
checks exact score equality. The original successor timeout remains
open.

The changed test passed all three API 26 runs, including a cold
instance that needed 32,512 ms of refill before the warm request.
The other two waited 9,092 ms and 9,082 ms. API 37 passed the warm
request in one of three runs after 9,066 ms. The other two stopped
at `reply(2)` before refill sampling, reproducing the original
first-successor timeout. The combined receipt for the changed
test had SHA-256
`d8e3c01df328173c950585c01607ef6e088f2ac17be8b2c2d05d2366ea36db25`.
The test checkout, AVDs and model copies were removed.

### First-successor timeout traced to the shared wall deadline

A second disposable qualification build buffered the numeric events
and flushed them at unbind. Seven of eight API 37 repetitions passed.
The failed repetition received both submissions, canceled request 1
and queued request 2 during preparation. Preparation completed and
request 2 entered the scorer. The watchdog canceled that score at
3,001 ms after preparation began. The worker recorded 59,884 CPU
credit units at cancellation and discarded the canceled reply.
The instrumented test therefore timed out while waiting for request 2.

The trace reproduces the wall-deadline mechanism of the earlier
timeout on the ARM64 emulator. The cold load and first score share
the existing three-second window. The trace receipt SHA-256 was
`681d5e2aafb3b1f302f67929ef747ebca6036ec1884b084d88271fc0877e48a4`.
The temporary trace build, AVD and downloaded model were removed.

The JVM regression sends and cancels a queued word during
preparation, then blocks its successor in the scorer. The virtual
clock verifies that scoring stays active at 2,999 ms and stops at 3,000 ms,
with positive remaining CPU credit and no stale reply. All 37 tests
in the preparation, duty-worker and scoring-infrastructure suites
passed. The JVM receipt SHA-256 was
`a6d8601b43da1797086dcf0e0e0ccff7f74ecd284cc331deef71c753b1ea9584`.

Cold-path timing on physical hardware and repeatability of the
real-model acceptance remain open.

### Release-native Binder fixture

A disposable qualification build at `0d1a40b919ea` used Android
Gradle variant fallback from an external init script. The fixture
passed the normal source-identity gate. Its four packaged native
payloads exactly match the stock release APK at the same revision.
The release APK SHA-256 is
`dfe77780e969722137fc6dbeea66bc45466800ff14f6d92389776a4d941bbb4c`.
The probe then ran six separate process starts on an isolated ARM64 API 37
emulator with the exact published model. The first attempt timed out awaiting
the first successor after the canceled preparation request. The other five
attempts returned both the first successor and the request following a refill.
In those passes, first-successor wall time was 438–658 ms, with 85–171 ms in
native scoring. The immediate request returned `UNAVAILABLE` in all five;
the post-refill request completed in 56–60 ms wall time after a 9,050–9,073 ms
wait. The numeric receipt SHA-256 was
`266a07146eb0ab7b2631c00dc23b6b4cfa8db78e621a62c38c9bafed37935753`.
The first timeout leaves the cold Binder repeatability check open even with
release-native libraries. The AVD, staged model, and fixture were removed.

### First-score phase timing with release-native libraries

A separate disposable app build at `0d1a40b919ea` captured numeric phase
times at the Kotlin adapter. Its four native payloads matched the same stock
release APK. It ran six process starts on an isolated ARM64 API 37 emulator
with the exact published model and the same private Binder test.

The first run again timed out at the successor. Metadata resolution took
22 ms, runtime setup took 10 ms, and the model-load call took 358 ms
wall time, including 357 ms inside native load. The first scorer call
spent 2,636 ms before returning after cancellation. The next five
runs passed. Their model-load calls took 158–191 ms wall time and first
scorer calls took 99–219 ms. These measurements isolate the failed run's
delay to the first scorer call, which still includes lazy context creation,
tokenization, and decode. A finer split and a repeatable cold-path result
remain open. The numeric receipt SHA-256 was
`4305b7e6d019735eba818bd6dd3ec680c4bace504c56bd14e85240c657f1b902`.

### Standalone Android split of context creation and scoring

The existing native `startup-benchmark` target was cross-compiled for ARM64
with the pinned NDK and `RelWithDebInfo` from `509e4cf145b6`. It ran on an
isolated 16 KiB API 37 emulator with the same exact model and the same fixed
four-candidate request as the Binder test. The standalone executable runs
the shared scalar scorer outside Binder and the worker watchdog. Five process
starts completed three model/context cycles each, with four requests per
cycle. All 60 requests passed the benchmark's exact within-process score and
token-count comparisons.

| Phase | First process, first cycle | Later processes, first cycles |
| --- | ---: | ---: |
| Model load, wall | 382.3 ms | 107.5–123.9 ms |
| Context construction, wall | 3.1 ms | 2.3–2.7 ms |
| First `Scorer::score`, wall | 11,144.3 ms | 78.5–123.6 ms |
| First `Scorer::score`, process CPU | 16,602.4 ms | 260.6–380.3 ms |

Within the first process, the second fresh model/context cycle still took
2,127.3 ms for its first score. The third took 177.6 ms. Context creation
across all 15 cycles took 2.3–4.2 ms. The anomalous interval is inside
`Scorer::score`, after context construction. Its underlying cause and the
first-successor timeout on physical hardware remain unverified. The emulator,
model copy, cross-build and logs were removed. The receipt SHA-256 was
`960fb8210d6a61458e6308c5df0ec12eba519b3de1820269b38d3400a44a2940`.

### Fresh emulator timing comparison

The standalone benchmark ran in three fresh API 37 AVDs in immediate,
settled, immediate order. The same executable, published model, and guest
checksum procedure were used on each AVD. The settled condition waited 60
seconds after staging verified inputs. Each AVD ran two new benchmark
processes for 72 successful fixed-request scores in total.

| Guest | Uptime at first process | First scalar score | First score in second process |
| --- | ---: | ---: | ---: |
| Immediate A | 13.29 s | 11,171 ms | 80 ms |
| Settled | 73.61 s | 99 ms | 105 ms |
| Immediate B | 13.33 s | 10,782 ms | 2,282 ms |

The first score in both immediate guests used more than 16 seconds of process
CPU. The settled guest used 337 ms of process CPU for its first score. These
runs associate the large transient with the beginning of emulator uptime.
There was one settled guest, and the test ran outside Binder. A settled
Binder run and the physical cold path retain their own acceptance checks.
The three AVDs and all temporary inputs were removed. The receipt SHA-256 was
`1eaf18090e53c02a3f9ab9889ff4bd51325361350fb651469018b56fc2edf780`.

### Release-native Binder in a settled guest

The same private Binder test ran six separate app process starts with the
exact model and four unchanged release-native payloads. The first test
started at 87.74 seconds guest uptime, 60.02 seconds after staging. All six
tests verified the first successor after canceling request 1, followed by
exact score parity after the refill. The first successor took 343–419 ms
wall time and 74–144 ms in native scoring. The immediate request was
admitted four times and returned `UNAVAILABLE` twice. No watchdog policy,
CPU credits, memory policy or test assertions changed. The AVD, fixture,
model copy and logs were removed. The numeric receipt SHA-256 was
`3c11593c123acad353e00f8ce9ba9d3f82fd935b6a38be4a074365ad954a61cd`.

This verifies repeatability on one settled emulator. The earlier failures
under emulator startup load remain in the evidence, and the physical-device
cold path and hosted verification still require their own results.

## 2026-11-24 JVM and Android checks on candidate 123d0a52

Two fresh temporary checkouts tested the exact hosted CI candidate
`123d0a5246b4e173a787102ede60b24c8cdc786d` with the pinned
`36b10154383b60eb15baac2c7a40d2a5f784faa7` llama.cpp gitlink.
Offline JDK 17 Gradle `testDebugUnitTest --rerun-tasks` returned zero
with all 48 tasks executed. The 139 app reports had 1,415 tests and
the three runtime reports had 19. No failures, errors or skips were
reported. The JVM log SHA-256 is
`acbab93a762a973bc35dc9d4ef30805c8036b1dc8effe01c38f1027bfaf2081c`.

The second checkout built both APKs offline. Debug APK SHA-256 is
`0b26a98d99e77603872d717b8737f9dac28838f03fbed7d6b00e6307da2d5c71`
and instrumentation APK SHA-256 is
`daa3444b99b8b0185a736e2255d87f2101a009d81334d9e146fb388dece290ee`.
Five live candidate controls covered English apostrophe protection,
manual pronoun selection, the Spanish control, canonical case Undo and
Russian immediate Undo. Three contextual punctuation cases covered the
independent Binder editor. Five menu cases covered settings search,
recreation, Back, theme persistence, insets and preview editing.

| Owned ARM64 emulator | Kernel page size | Starts and passes | Instrumentation log SHA-256 |
| --- | ---: | ---: | --- |
| API 26 | 4,096 bytes | 13 / 13 | `8891dc10b3e94bd4c4127f4e3e9ddb9e71132e03e07f1d5f5717285406ae8446` |
| API 37 | 16,384 bytes | 13 / 13 | `7162478589d5c4cf1d2aef766f7c1ae3e2aa5176c29400d4888e3adfcab0b405` |

Both runs produced the same 13 distinct method identities, with no
skips or test failures. The JVM and targeted instrumentation runs
cover the exact candidate locally. Full Android boundary runs on this
revision, hosted x86_64 CI and physical acceptance remain open.
The checkouts, APKs, emulators and isolated ADB server were removed.

### Coverage of the 59 general-suite skip identities

The manifest and Android job on candidate `123d0a52` were audited by
class and method identity. Twenty-seven skipped identities have an
explicit route elsewhere in the same job matrix. Counts below are unique
across API levels and expressed as routes observed in source.

| Android job route | General skip identities it can execute |
| --- | ---: |
| Opt-in boundary scopes | 10 |
| Synthetic profile restart | 4 |
| Editing process death | 2 |
| Voice fixture | 6 |
| Chrome textarea | 2 |
| Night-learning fixture | 3 |
| **Total** | **27** |

The other 32 identities have separate acceptance prerequisites.
Twenty-four require a physical Fold, including the Chrome address bar
and an owned Termux session. Five punctuation cases allow an explicit
emulator fixture, and use a separate Fold check for physical acceptance.
Three tests require the exact installed model. The dispatched native
model workflow validates host contracts and does not run those three
Android methods. This inventory describes routing and fixtures. Test
outcomes are recorded in the corresponding run receipts.

The five separate punctuation identities [passed on API 37 in private
and ordinary editor modes](2026-11-10-a4-private-boundaries.md#punctuation-fixture-on-the-refreshed-ci-candidate)
using the exact candidate APKs.

### Candidate 123d0a52 API 26 run interrupted by the local timeout

The full local boundary runner discovered 399 test identities from
the instrumentation APK. The outer process reached its 2,400-second
timeout during the general suite. Its partial JUnit XML contains 354
discovered identities, with 302 passes, 50 skips and two failure records.
Forty-five discovered identities have no XML record. The partial XML
and discovery list have SHA-256 digests
`a54f497fd432453a5140936601861e45564df03f3d74b6fe0368334371b0876a` and
`5179b2c73a7eefc6d41cb084fc0453e48202bef52a40736cbed3d556948f7668`.

The date/time case hit an immediate missing accessibility node while
its fixture was waiting for the editor to settle. The last diagnostics
case has an empty failure record and no assertion stack in the
interrupted report. The full boundary receipt was not written. The
separate API 26 night fixture stopped before boot because its local
runner attempted an immediate reuse of the previous console port.
The hosted job already provides 90 minutes. A fresh local boundary run
needs that time allowance and a separate port for the night guest.

The night fixture was rerun from the same candidate commit and its
hash-checked ordinary APKs on a fresh API 26 guest with a separate port.
All four synthetic cases passed, including observed promotion and the
learning-lab follow-up. The receipt SHA-256 is
`044d463a729bf8b5b9d88c59b46a255304c9cfce56a29218e038b7f7a42d5417`.
The checkout, APK copies and isolated guest were removed. Natural
scheduler dispatch and the interrupted boundary run remain open.

### Non-normal editor settling follow-up

The date/time stack from the interrupted run points to a missing field
node at the start of a snapshot. Inside the bounded non-normal editor
wait, a missing field or stats node now resets the consecutive-snapshot
check and allows the next poll. Both nodes and two matching snapshots
are still required. The editor text, selection, composing span,
no-read and model-activity assertions remain in the scenario.

An initial implementation passed both full non-normal and suggestion-
flag classes on API 26 and API 37, with 11 passes and two additional
date/time passes per API. An exact second build preserved the original
field-then-stats observation order and ran both methods listed in the
interrupted report on each API. The final fixture source SHA-256 is
`a70950323fa3a40a84c8c42b4c5993dfb4756aa83c290b04078f8c57bb3327ca`.
Its instrumentation APK SHA-256 is
`6595f43be70118d8060215a2c5cd7451d4d53e1dd03ef09f2c44116926f86b75`.

| Owned ARM64 emulator | Date/time and diagnostics consent passes | Final instrumentation log SHA-256 |
| --- | ---: | --- |
| API 26 | 2 | `372924ff63b4b4a971dd17690d2fe7550c1115eb3c4c597ad513e6b4060a4a83` |
| API 37 | 2 | `3cd925031387188a696ff62e7b01609f351874482da775bca0bd402006948f8a` |

Both final runs emitted two starts and two successes with zero skips.
The targeted result covers the two recorded methods. The full boundary
run remains open. Test APKs, guests and temporary output were removed.

### Candidate 123d0a52 API 37 local interruption

The older local runner also reached its 2,400-second deadline in the API
37 general scope. It discovered 399 identities and did not produce a
complete boundary receipt. The separate night fixture could not start
on the immediately reused console port. Its process exited 1 after
both scoped setup failures and released its guests and temporary files.
The newer API 26 retry uses a 90-minute boundary budget and separate
console ports for boundary and night fixtures.

### Candidate 75d06f6f API 26 general boundary

The retry completed the general scope on the isolated ARM64 API 26 emulator.
The fresh JUnit XML matches all 399 identities discovered directly from the APK.
It records 340 passes, the exact 59 versioned skips, and zero failures or errors.
The runner independently reported exit 0 and `freshResultVerified=True`.
The discovery SHA-256 is
`5179b2c73a7eefc6d41cb084fc0453e48202bef52a40736cbed3d556948f7668`
and the JUnit XML SHA-256 is
`7a9f7ca3e3681e0a3ffb9ac5792f171cc68481e45e5fa4af8b2cffa2498def57`.

The complete boundary invocation passed all 11 scopes. Its ten additional
scopes added 24 passes with zero failures, errors or skips. The policy
receipt SHA-256 is
`a16177208272bc1e35aeccf0f084c270c9255a1a9b611e46371cb5c834e50de6`.

All four supplementary runners also exited zero. The receipts were:

| Route | Receipt SHA-256 |
| --- | --- |
| Synthetic profile restart | `e0eb05f5760e9fc9a3635bd3e0c3009ea3b641897a0b5054474c50f4c132f59d` |
| Editing process death | `52057cb342dc420b8d28c770ca90aeaab062847e93d30c0d3080d5ba6bbea984` |
| Voice fixture | `4c0329b7862b9d4a258e62c9cc7be21fad6f19d87510d78782c0b33f2e9762b7` |
| Night learning | `044d463a729bf8b5b9d88c59b46a255304c9cfce56a29218e038b7f7a42d5417` |

The full local wrapper exited zero and removed its checkout, temporary APKs
and isolated guests. The U14 implementation and its five required cases were
tested separately in [the U14 receipt](2026-10-28-u14-expanded-ui.md#expanded-row-in-the-ime-window-with-talkback).
The full API 37 candidate run and hosted execution remain open.

### Required expanded-candidate regressions

The general report gate now requires four real-IME expanded-candidate cases
and the same-window candidate-strip case to execute successfully on both
Android CI versions. The cases cover English and Russian selection, typing
with the row open, Back and reopening, and stale touch cancellation. A
report mutation test verifies rejection when any of the five cases is missing
or skipped. All 54 Android CI runner tests passed.

### Candidate 687361c8 API 37 general boundary

The local ARM64 API 37 guest used the 16 KiB system image. The general
scope exited zero and reported `freshResultVerified=True`. The fresh
JUnit XML matches all 400 identities discovered from the instrumentation
APK. It records 341 passes, the exact 59 versioned skips, and zero
failures or errors. All five required expanded-candidate cases passed.

The discovery SHA-256 is
`509c9bdba2b6773176e917198dcde5bdf6faa61ca1b1006bfd532a9faa3b9676`
and the JUnit XML SHA-256 is
`e5ae93647bf5f3d0097d636f6b65d08a0c2885ebf4f6058d09e79c6ff527a747`.
The complete boundary invocation exited zero. Its machine-readable
receipt reports success and has SHA-256
`f2775bb063ca34d28b00502fd5ad315a83cd8c431d6ecc45f6629835f02ab5bb`.

### Candidate 687361c8 API 37 supplementary scopes

The local wrapper on the same exact candidate
`687361c8ac48eee16217c23b7510c18129817f6f` exited zero with
`FULL ANDROID LOCAL FAILURES []`. Synthetic profile restart, editing
process death, the voice fixture, the opt-in Chrome editor route and
night learning completed successfully. Chrome ran two native tests and
the numeric DOM oracle passed both profiles across 113 records. The
separate night guest also used 16 KiB pages.

| Route | Receipt SHA-256 |
| --- | --- |
| Editing process death | `d99762ae4a54da1eaeae3e4c104cd6a8f467bebb5194f641cd2e692fe93019be` |
| Voice fixture | `1f8a9f5df241d275dc253f7f5c302f56b342a996b62a2ef87377795d3fa2f78d` |
| Chrome editor | `755513a9282fed5c82c0458da823aa8817102da77f83eb481b3b023a5f030e31` |
| Night learning | `891142364eb9e207ed5acfc929f353b4f5ca3a3a1e3623c9a6a137ef1f6d46d3` |

The run removed its temporary checkout, APKs and guests. Hosted
execution remains open.

### Clean stdlib run through the Joint control recovery

The source-only stdlib run at `47b4b325fa20a8d1cf0cc5aa0b01093ad226572e`
recorded 1,106 tests in 211 modules, one failure and zero errors or
skips. Its receipt SHA-256 is
`f458297bf55fe237aef1c5f6bbeb9b131cb915911b7a1dfba1177197493bcc0f`.
The spelling corpus builder correctly returned `BLOCKED_OVERLAP` for
the word used by the incomplete-coverage fixture. The recovered Joint
Original control entry contains that surface. A direct check confirmed
one surface overlap and zero lexical overlaps for the previous fixture.
The replacement uses an artificial word and has zero overlaps, so it
reaches `BLOCKED_COVERAGE` and exits 2 without producing a corpus.
All 11 spelling builder tests passed with the replacement fixture.

The fresh source-only rerun at `7ec3b33237d58d348f699cd82461c8b15b069377`
passed all 1,106 tests across 211 modules with zero skips, failures or
errors. The throwaway checkout used the verified llama.cpp gitlink,
started without a build directory and was removed after the run.
Receipt SHA-256:
`41476fb2c6fd650a60b80c19aa75ad28e588c8c144d3665ef4ba3a839d8a9f18`.
Hosted execution remains open.
