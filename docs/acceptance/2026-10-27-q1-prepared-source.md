# Q1 — exact F-Droid prepared-source checks

Real `fdroidserver 2.4.5` preparation of source commit 1b0a000 changes only
`app/build.gradle.kts`: the signing scrub removes its signing configuration and
assignments. Later build cleanup and scanning also delete six tracked files:
three root wrapper files, the unused numeric training baseline and two wrapper
files in the pinned llama.cpp example. Restoring these into the scanned source
or broadly accepting dirty Git state is not the chosen integration.

Commit 9a366a9 adds a separate explicit `runePreparedSource=fdroidserver-2.4.5`
mode. It accepts exactly the seven committed policy transformations, using
Git-object original hashes, replacement bytes/mode and absent deletion targets.
Every recursive submodule keeps its recorded commit. Every checkout must have
exactly the expected unstaged NUL-delimited status. Additional/staged/untracked
changes, symlinks, dirty policy, changed revisions and hidden Git index flags
fail. Ordinary release source checking stays strict. No ignored proof token,
generic dirty bypass, Git repair or missing-Git fallback was introduced.

The first real local `fdroidserver.build.build_local` run scans successfully
(zero fatal findings, the existing gzip and upstream Keynote warnings), then
fails `qualificationArtifacts`: its old submodule diff check rejects removed
example wrappers. Commit b8ca50f adds the same explicit mode to that verifier.
It first requires the complete global prepared checkpoint, then independently
permits only those two wrapper deletions. A regression proves that even a future
committed preparation policy admitting a C++ edit cannot bypass this independent
runtime check. The usual fingerprint still covers the compiled/runtime recipe.

Validation:

- All 27 source/qualification-bridge tests pass; the separate existing fingerprint
  test also passes. The earlier 22-test run had one fixture-cleanup failure while
  clearing two Git flags in one command; cleanup now uses separate commands.
- The second actual `build_local` run, at b8ca50f, again has zero source-scan fatal
  findings and the same two warnings. `qualificationArtifacts` passes with the
  unchanged runtimeBuildId `356dc78ec8b156462d8384ca14f0e20ff831c66b83c38831f40edfd6bd645613`.
  The app's 27 guard tests pass inside that real prepared checkout.
- Actual Gradle `:app:releaseSourceCheck` passes on the seven-change prepared tree.
  A controlled additional CHANGELOG edit fails with
  `RELEASE_PREPARED_SOURCE_DELTA` while reusing the configuration cache. Restoring
  the saved bytes makes the same cached command pass again. The default strict
  CLI rejects the prepared tree with `RELEASE_SOURCE_DIRTY`.
- Standalone prepared qualification verification passes after restoration.

**Full prepared-source assembly is still failing.** The second run stops at
`PrepareLlamaSource.cmake:15`: the native pristine-submodule check rejects the
same two wrapper deletions. That CMake guard participates in runtimeBuildId;
changing it needs a renewed identity and qualification. It must be integrated
with the remaining native recipe/source-path work rather than silently retaining
the old qualification pin. No new runtime recipe or qualification constant was
changed here, and no final F-Droid APK was produced.

Both runs used the genuine local F-Droid build function, a verified source-pinned
wrapper outside the scanned tree, Gradle offline mode and the existing dependency
cache. The SDK acquisition-only prebuild command was omitted because its pinned
CMake was already installed. Python source scanning used package SUSS defaults
with network blocked. Source tarball creation and the final binary scanner were
disabled and are not claimed; no build-server VM or next versioned recipe was
run/published. The helper's initial data-policy setup key error happened before
cloning and is retained separately, not counted as a build attempt.

Original working-tree changes were not stashed or altered. All destructive
F-Droid preparation happened in task-owned disposable copies. Raw logs and the
failed checkouts remain under the ignored build directory. The adjacent JSON
binds implementation sources, actual results and exact failure stages. Q1 and
the complete original review remain open.
