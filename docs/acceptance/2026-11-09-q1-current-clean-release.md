# Q1: current clean-source local release gates

## Current CI build-gate repeat

A clean temporary clone of `285d896ee37e72223b8b5482af25e2c5552bd985`,
with the pinned native submodule and no initial `build/`, passed the exact
offline Gradle build-gate task list from the current workflow: lint, debug,
unsigned release and profile assembly, both privacy gates, IME intelligence,
forbidden runtime dependencies, native symbols and APK footprint. The source
checkpoint passed before and after; the temporary checkout and artifacts were
removed. This is local evidence, not a signed release, F-Droid scanner run,
independent builder, hosted CI or full review acceptance.

A clean temporary clone of committed source `ef9763a2` with its initialized,
pinned llama.cpp submodule passed the release source checkpoint before and
after the build. No signing files were copied into the checkout. The offline
Gradle run passed the complete `:app:testDebugUnitTest` suite (1,396 tests,
zero failures, errors or skips), lint, debug, unsigned release and profile
assembly, release/profile privacy gates, IME intelligence and forbidden runtime
dependency boundaries, native-symbol gate and the fixed APK footprint gate.

The separate native-runtime verifier passed both with and without its strict
local-source-path check on the resulting unsigned release APK. The build's APK
was 180,122,941 bytes with SHA-256
`6651a55ca79a8154f87013d959744a45f2043ca2bb0af4c0cf4de880b8bf412c`.
The merged manifest contained the targeted input-method visibility action;
`QUERY_ALL_PACKAGES` and `RECORD_AUDIO` permissions were absent. Rune's
existing INTERNET permission is unchanged.

This is a local unsigned build and static/host test evidence, not a signed
release, F-Droid build-server run, hosted CI, model qualification or a physical
Fold installation. The temporary source, APK, build outputs and logs were
removed after the checks; no owner signing material or installed app was used.

## Current diagnostic change follow-up

The clean-source checks were repeated on `d61df14f`, which includes the later
production diagnostic changes. A temporary local clone with the pinned
`36b1015` llama.cpp submodule passed the source checkpoint both before and
after the offline build, without owner signing files. Gradle passed debug JVM
tests, debug lint, debug/release/profile assembly, both release and profile
privacy gates, the IME and forbidden-dependency boundaries, native-symbol
gate and release APK footprint gate. The 139 fresh JVM XML reports contain
1,401 tests, zero failures, errors or skips. The separate native runtime check
passed on the unsigned release APK with the strict no-local-paths option.

The APK was 180,122,941 bytes, SHA-256
`d649ac58349c4a50de41f633e46e352a80f9937ee96e74aa87990492166b2e4c`.
The temporary clone and its build outputs were removed; command logs, exit
codes and a numeric receipt remain locally under
`build/ci-editing-investigation/q1-clean-current`. This is not a signed
release, F-Droid build-server result, hosted CI run or Fold acceptance.

## Repeat after corpus-exclusion updates

At clean source `999bb3213083b655a756c6df8733fbbb5c7986b1`, a temporary
checkout with the pinned llama.cpp submodule and no owner signing files passed
source checks before and after an offline build. Debug JVM tests (139 XML
reports; 1,401 tests, zero failures/errors/skips), debug lint, debug/release/
profile assembly, release/profile privacy, IME and forbidden-dependency
boundaries, native-symbol and APK-footprint gates all passed. Strict packaged
native verification including the no-local-path check passed. The unsigned
release APK was 180,122,941 bytes with SHA-256
`20d9244e1ac4a4c215331c3cbdff657325d535410e25585d0871bb9c16f927c3`.

A second fresh checkout of the same source, on the same host and cached
toolchain, separately passed release assembly, release privacy and footprint
gates and produced an APK with the same byte count and SHA-256. This proves
only that local two-build comparison, not independent build-server
reproducibility. The earlier `d61df14f` APK had the same size but a different
SHA-256; its cause was not investigated during this repeat. The earlier build's
temporary APK was no longer available at that time. Both new temporary source
trees and APKs were removed. Logs, actual exit codes and numeric receipts are
retained under `build/ci-editing-investigation/q1-post-corpus`; no signed
release or physical-device acceptance is claimed.

## Repeat after historical exclusion expansion

At `75e096a0942b377c2bd74b9f1ed31928b1d27d1f`, a clean temporary clone with
the pinned llama.cpp submodule and no owner signing files passed the source
checkpoint before and after an offline build. Gradle passed debug JVM tests,
debug lint, debug/release/profile assembly, release/profile privacy, IME and
forbidden-dependency boundaries, the native-symbol gate and APK-footprint gate.
The 139 JVM XML reports contain 1,401 tests and no failures, errors or skips.
The unsigned release APK was 180,122,941 bytes, SHA-256
`0a01db3b666412c3693e8b05acfddfd098926225a64d2c0fcdeded03cecfbfdf`.

The temporary checkout, APK, logs and build outputs were removed. The separate
strict packaged-native verifier, F-Droid scanner, hosted CI, independent
build server, signing and Fold acceptance were not run in this repeat.

## Cross-commit APK difference

Both `d61df14f` and `999bb321` were rebuilt in separate clean temporary
checkouts on the same host and pinned toolchain. Their APK hashes exactly
reproduced the previously recorded hashes. The APKs contain the same set of
entries; comparing the uncompressed contents of every entry found only
`META-INF/version-control-info.textproto` differed. The compared ZIP metadata
fields (timestamps, compression method/size, flags and external attributes)
also matched.

For both commits, the Gradle `extractReleaseVersionControlInfo` output matched
the corresponding APK entry by SHA-256 and contained the corresponding source
commit. Replacing that commit with the same placeholder made the two metadata
files byte-identical. Thus the two local builds differ in their embedded Git
revision metadata; the uncompressed application payloads otherwise match.
This does not establish independent build-server reproducibility or compare
signed releases. Temporary APKs and source checkouts were removed. Command
logs, exit codes and comparison receipts remain under
`build/ci-editing-investigation/q1-apk-comparison`.
