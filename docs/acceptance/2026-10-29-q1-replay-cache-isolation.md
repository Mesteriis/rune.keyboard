# Q1/Q7 replay resolver cache isolation

The standalone replay-toolchain Gradle invocation created `.gradle` binaries
inside `tools/ci`, which is in the F-Droid review-data scanner's scope. On a
workstation that ran the resolver, `tools/fdroid_data_policy.py` correctly
refused those unreviewed local files as `UNREVIEWED_OR_STALE_DATA_SET`. Git
ignored the cache; a clean Git status did not prove its absence. The policy is
not weakened and no scanner suppression is added.

The CI resolver now sets `--project-cache-dir` to an absolute directory under
`RUNNER_TEMP`, outside the source checkout. A disposable fixture containing all
31 current policy entries and the exact standalone resolver passed the real
policy check; the offline Gradle task verified all five pinned JARs using an
external project cache; the policy still passed afterward. A deliberate binary
under the fixture's source-local `.gradle` was refused. All 12 data-policy unit
tests passed. The fixture uses the existing host dependency cache, not an
independent build-server or distribution run.

The old ignored cache was subsequently moved intact to
`build/q1-preserved-replay-project-cache-20261029`. The direct policy check on
the current working tree then passed with 31 entries. Running the actual
standalone resolver with an absolute project cache under `build/` verified all
five JARs, left no source-local `.gradle` and the direct policy passed again.
For a local standalone resolver run, pass an absolute cache path outside `tools/ci`,
for example `--project-cache-dir "$PWD/build/replay-toolchain-project-cache"`.
The first exploratory fixture used a relative cache path; Gradle resolved it
under the temporary project. The final proof uses an absolute path as CI does.
