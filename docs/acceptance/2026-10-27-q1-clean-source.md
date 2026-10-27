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

A positive full release build from a separate clean checkout is pending at this
implementation commit. It must be bound to its exact source revision and final
artifact before that acceptance is claimed.

This is Git source-state validation, not a hermetic build, qualification, signing
or publication certificate. Ignored SDK/signing/build files remain ignored by Git.
Missing repository metadata and prepared dirty source fail closed. F-Droid source
preparation deletes wrappers/scandelete targets; integration of a clean pre-prepare
checkpoint and bound preparation effects remains open for the next recipe.
Historical recipes point to older commits and are not changed to current HEAD.
