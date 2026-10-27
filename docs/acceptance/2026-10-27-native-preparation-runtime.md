# Native preparation and runtime requalification

The normalized native runtime is merged at 013c3ef. U16's native packaging,
source-path and exact-model execution checks are verified. Q1's real local
F-Droid preparation/build now passes. The whole original review and independent
distribution/whole-release acceptance remain open.

The initial strip-only change preserved runtime ID
`356dc78ec8b156462d8384ca14f0e20ff831c66b83c38831f40edfd6bd645613`.
Removing source-location literals and integrating the native preparation guard
require a separate recipe change. Its new ID is
`d48f6df2ed03cd11d3182abe453fb3a5bd126aea92f2bc06ab747b201f84565f`.
The candidate kept the model gate closed until the execution evidence below
existed. Its intermediate prototype and old backend IDs are explicitly rejected
by the updated fingerprint regression. Weights, scoring arithmetic, runtime API,
lexicons, spelling-policy version and confidence thresholds did not change.

CMake's explicit F-Droid mode runs the complete committed prepared-source
checkpoint and the qualification verifier's independent two-wrapper-only
submodule check. Arbitrary C/C++ edits remain refused even if a future preparation
policy describes them. Normal builds retain the pristine-submodule requirement.
The pinned upstream archive is patched privately; example wrappers and the
intermediate tar are removed from that generated copy. No deleted wrapper is
restored into the scanned source tree.

Compile-time file/debug prefix maps replace both the source root and generated
binary directory with stable `rune-source`/`rune-build` prefixes. The first
prototype removed machine paths but retained AGP directory hashes, and its two
llama libraries differed between normal and prepared roots. The refined recipe
removes that dependency too. No packaged ELF string was rewritten after linking.

Both current unsigned universal APKs are **180,096,157 bytes**, SHA-256
`cfcb1e1989a5dab4447066a31ca2812ebd78c7f78e75b608d38818107291a785`:
one from the clean normal checkout, one from genuine local
`fdroidserver.build.build_local` 2.4.5 preparation. Their complete APK bytes match,
not only their four native libraries. This observation uses the same host,
toolchain and existing offline dependency cache; it is not independent or
cache-free build-server reproducibility.

The four native payloads total **9,957,040 bytes**. They match the runtime's stripped
outputs and the release-native instrumentation APK. Packaged `.debug_*`, `.symtab`
and forbidden JNI/network/log symbols are absent; `JNI_OnLoad` remains exported.
The strict `/Users/` and `/home/` audit passes. All four `.text`/`.rodata` sections
also match their unstripped originals. Those four originals are retained privately
for symbolization. All 69 source assets match the APK exactly. The existing
183 MB APK and component/ABI budgets pass without raising limits.

Execution evidence:

- All **1,254 app JVM tests** pass, with zero failures/errors/skips. Release/profile
  privacy gates, debug/release lint, app/debug-test/release/profile builds,
  IME dependency boundary, forbidden dependencies, native symbol and APK footprint
  gates pass. The source/qualification bridge runs its 27 tests in release builds.
- All **12 native Python tests** pass, including four real-Git/CMake preparation
  fixtures and the compiler optimization/model-extraction checks. Seven fresh
  host CTests pass, including the exact-model scalar scoring oracle, 632-sequence
  tokenizer equivalence and real tokenizer cancellation. The model is exactly
  396,704,416 bytes, SHA-256
  `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
- **21 runtime instrumentation tests** pass across physical Fold SM-F966B/API 37,
  ARM64 API 26 and ARM64 API 37/16 KiB emulators. Each target runs six ordinary
  tests and one strict exact-model test, with no skips. The latter now performs
  an actual native self-test before scoring: nine successful requests and 27
  scored candidates, plus cancellation/error/reload recovery checks.
- Fold pilot/full release-native benchmarks pass with 27/180 measured requests,
  nine configurations and 20 full-run observations per configuration. Installed
  library hashes are checked independently by the benchmark and match the app
  release bytes. Four-candidate wall-time samples are:

| Language | p50, ms | p95, ms |
| --- | ---: | ---: |
| EN | 29.290 | 57.841 |
| RU | 158.322 | 249.014 |
| ES | 107.399 | 135.728 |

The adjacent JSON contains exact statistics; these are descriptive samples, not
population percentiles or complete IME latency. Digest verification warms the
filesystem. This is not cold-storage or unplugged battery acceptance.

The physical production service test uses the real importer, activation/native
self-test, private Binder client, adapter and duty/idle worker in a separate
`.qualification` application. First/warm replies take 549/160 ms wall and
175/145 ms native. Over 60,001 ms, 15 requests complete and 105 are UNAVAILABLE;
the model process uses 8,080 CPU-ms under the unchanged accounting limits.
After 65,004 ms idle, RSS falls from 576,401,408 to 147,075,072 bytes, with 70 CPU-ms
idle work. This demonstrates the tested limiter and page release, not absence of
all leaks or whole-device energy use. The app/test packages were absent before
installation, byte-verified and removed afterward; the default IME is unchanged.

The standalone release-native test APK is explicitly debuggable for private
`run-as` staging of the verified local model. Its native bytes still match the
actual release APK; that match, not the fixture flag, is the release-native proof.
The first staging attempt exposed the prior non-debuggable fixture and failed
before model tests. No app release/debuggability setting was relaxed.

An explicit `-PruneNativeQualification=true` debug build gives the app its own
`.qualification` application ID/storage. Ordinary IME tests reject that package.
Reviewing cleanup exposed a second risk: rejecting setup before its settings
snapshot still allowed old teardown to disable the default Rune IME and clear
fixture preferences. A real disposable-emulator red/green test proves the old
driver disables an installed owner IME; the fixed driver leaves all three secure
IME settings and fixture preferences unchanged, including repeated teardown.
The failed first host restore lacked quoting for subtype separators; its log is
retained. The final seeded red/green run uses quoted controlled commands and
touches no physical device. All task-owned emulators/AVDs are removed.

Fresh baseline/candidate historical product replays complete all **12,000 rows**.
Their projections are identical after excluding only `hostStageNanos` and
`fullTokenGenerationNanos`, SHA-256
`33c3a96fed5b3322601f6b7a0307e3a4b62bfbc9bc7650b82bf644a1afffd8a3`.
Both runs use the same hash-bound driver from the owner's working tree. This is
historical regression evidence, not fresh quality qualification or native
inference. Existing EN/ES quality-gate failures and Q6 provenance gaps remain open.

Real local F-Droid source scanning has zero fatal findings and the two previously
recorded gzip/Keynote warnings. The SDK acquisition-only prebuild was omitted
because the pinned CMake was installed. Source tarball creation and final binary
scanning were disabled. Missing-Git exports, an independent build server, the
next versioned recipe, x86_64 execution/remote CI matrix, signed whole-release
onboarding/offline input/settings and publication remain separate gates.

The adjacent JSON binds code, artifacts, metrics and private logs. The fast-forward
merge preserves all 13 existing dirty tracked files and 98 untracked paths;
their private preservation hashes are not published. Device connections, model
locations, settings snapshots, raw backups and diagnostics stay in ignored local
storage. All phone operations used ADB, with Fold access coordinated and released.
