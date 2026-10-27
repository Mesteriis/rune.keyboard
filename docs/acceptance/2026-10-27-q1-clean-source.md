# Q1 — live Git checkpoint before the release APK

The app preReleaseBuild task now depends on releaseSourceCheck. A lazy task
collection attaches it after AGP registers variant tasks. The check has no outputs
or up-to-date result: each invocation, including reused Gradle configuration,
reads actual Git state. It requires a committed root checkout, empty porcelain-v1
NUL status including every untracked file and submodule contents, and initialized
recursive submodules at their recorded commits. Local submodule ignore settings
cannot suppress its explicit --ignore-submodules=none query.

JSON output contains commit, status count and readiness/reason only. Dirty source
has submodules=null because module readiness was not checked. Filenames and Git
stderr payloads are not printed. NUL records account for rename/copy source names;
spaces/newlines in filenames do not become extra records. The guard reads state
without stashing, clearing, committing or changing the original checkout.

Eight isolated-Git tests pass. They cover committed/ignored state, staged and
unstaged edits, deletion, untracked files, rename protocol, absent/nested roots,
uninitialized modules, locally hidden dirty module contents, module commit drift
and fixed-code CLI failure without filename disclosure.

The actual dirty main checkout rejects :app:assembleRelease with
RELEASE_SOURCE_DIRTY and leaves the existing APK SHA unchanged. The first Gradle
setup attempt failed because preReleaseBuild was not registered at script
evaluation; the final code uses lazy matching and the real refusal is verified
separately. :app:testDebugUnitTest still completes successfully in this dirty
checkout without executing the release checkpoint. No Android/runtime source or
asset changed in this step.

The positive build now passes from an independent local clone of implementation
commit ea94b15, with its recorded submodule initialized. No local signing file was
copied; the retained output is an unsigned release APK, 180,133,309 bytes. Before
and after the build the checkpoint reports zero status entries and one initialized
matching submodule. assembleRelease, apkFootprint, privacyGateRelease and the
runtime native symbol gate pass. The build uses the existing offline dependency
cache; this is a clean Git checkout build, not a cache-free/hermetic build.

The actual packaged-native gate and qualification metadata verifier also pass;
runtimeBuildId remains 356dc78ec8b156462d8384ca14f0e20ff831c66b83c38831f40edfd6bd645613.
All 69 source assets match the retained APK exactly. The strict local-source-path
audit still fails with NATIVE_LOCAL_SOURCE_PATH on this newly built artifact.
Native-model/device smoke remains unrun.

A controlled edit to CHANGELOG.md in the isolated checkout then repeats the same
Gradle command with configuration-cache reuse. The live checkpoint fails with
RELEASE_SOURCE_DIRTY and the unsigned APK hash stays unchanged. The saved original
file bytes are restored in finally; a subsequent checkpoint passes again. The
original dirty working repository is untouched. The first clone initialization
check correctly refused an unregistered submodule even though object checkout had
completed; explicit registration in that clone fixed its metadata before building.
That initial failure and the successful before/after checks are retained.

This is Git source-state validation, not a hermetic build, qualification, signing
or publication certificate. Ignored SDK/signing/build files remain ignored by Git.
Missing repository metadata and prepared dirty source fail closed. F-Droid source
preparation deletes wrappers/scandelete targets; integration of a clean pre-prepare
checkpoint and bound preparation effects remains open for the next recipe.
Historical recipes point to older commits and are not changed to current HEAD.
