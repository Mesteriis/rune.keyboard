# U16 / Q1 — stripped APK payload verified; source-path audit still fails

The app now obtains ndkVersion from the configured runtime library Android DSL.
The runtime recipe remains the authoritative pin (29.0.14206865); none of its
fingerprinted files, compiler flags, CMake sources, descriptor or qualification
constants changed. Configuring that module before the app makes the shared pin
available to the app packaging/strip tasks.

The native gate now opens the actual APK, requires exactly four native members
(two libraries × arm64-v8a/x86_64), rejects duplicate/unexpected members and checks
each extracted ELF with the pinned readelf. DWARF, compressed DWARF, .symtab and
embedded/debug-link sections refuse. Every library must equal the corresponding
runtime stripped output byte for byte; this proves stronger parity than comparing
only .text/.rodata. Existing runtime DT_NEEDED, export/JNI and source checks stay
in place. A malformed readelf result cannot pass. Temporary extracted files are
removed on exit. Paths or binary strings are never printed by the Python gate.
CI runs its eight Python regression cases before the existing packaged-APK gate.

The local release build, release privacy and runtime symbol gate pass, with no
"Unable to strip" message. The qualification artifact verifier retains runtimeBuildId
`356dc78ec8b156462d8384ca14f0e20ff831c66b83c38831f40edfd6bd645613`.
The adjacent evidence binds exact final build/log and artifact identities.
Final debug/test, release and profile builds, both privacy gates and debug/release
lint pass. An initial release-lint run found the diagnostics-only section layout
in main resources; moving that unchanged XML to debug/res fixes the source-set
boundary without suppressing lint. The failed run is retained separately.

| Packaged library | Bytes |
| --- | ---: |
| arm64-v8a libc++_shared | 1,374,336 |
| arm64-v8a librune_llama | 3,413,008 |
| x86_64 libc++_shared | 1,337,488 |
| x86_64 librune_llama | 3,859,104 |
| Native total | 9,983,936 |
| Universal release APK | 180,129,837 |

The previously present release APK was 278,395,385 bytes, with 108,236,792 native
bytes. It was saved privately before rebuilding and now fails the new gate with
NATIVE_DEBUG_SECTIONS. Four additional closed fixtures each replace only one
current packaged library with its old unstripped counterpart; every fixture is
rejected for debug sections. These fixtures are not installable release artifacts.
The old APK has no established source binding to current HEAD, so its complete
APK size difference is descriptive, not a controlled same-source A/B claim.

## Outstanding source-path requirement

The strict `--require-no-local-paths` audit **fails** with
NATIVE_LOCAL_SOURCE_PATH on the current release. Both librune_llama ABIs retain
161 strings containing machine-local source prefixes in .rodata, consistent with
compiled source-location literals. Both libc++ libraries have zero such strings.
Removing DWARF does not remove __FILE__-derived data. The ordinary packaged gate
proves stripped symbols and byte parity; it does not claim a source-path pass.
The strict option is a separate documented release check, not an inverted negative
test counted as success. Only fixed codes/counts are published; strings stay private.

Changing the runtime source-location compiler recipe would change its qualified
source fingerprint and requires corresponding qualification. Rewriting the ELF
payload or pins to hide the mismatch would violate the parity/qualification
requirements. That work remains open. Unstripped outputs stay local for later
symbolization, with no publication in this step.

U16 is not complete. Source-path elimination and release model-load/self-test/
scoring smoke on Fold and required emulator APIs remain unverified. Q1 additionally
requires footprint budgets, distribution/clean-source gates and release evidence;
this measured payload is only its packaging foundation. No release was published,
no phone update installed, and no native-model runtime smoke was run in this step.
