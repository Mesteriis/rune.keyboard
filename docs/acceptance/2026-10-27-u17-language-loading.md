# U17 — defer Russian assets until enabled (partial)

PersonalTypingResources now requests RU morphology/rare and experimental assets
only when the enabled-language snapshot contains Russian. Obtaining the shared
ExperimentModels handle performs no asset I/O. The process owner keeps a strong
language-preference listener and starts loading on a later RU enable in the same
process. An atomic start guard plus the experiment owner's existing lock prevent
repeated requests from replacing already published handles. Disabling RU after a
request retains the existing work/mappings; this is startup deferral, not eviction.
Ready subscriptions stay pending while RU is deferred and remain cancellable.

Five fixed, content-free trace names were appended without changing existing
ordinals: resourcePrepare, dictionaryLoad, dictionaryReady, contextualAssetsLoad
and contextualReady (all with the Rune# prefix). Ready markers are emitted only
on success; load sections close in finally. The architecture lists the complete
vocabulary and loading lifecycle. No new setting, store, model or threshold was
added.

Validation:

- A cold-process instrumentation case first saves EN-only settings before
  obtaining the resource owner. For a one-second observation it sees unavailable
  lexical handles, all checked model readiness flags false and no completion.
  It then enables RU, waits for real packaged assets, checks actual memberships
  and all contextual/revision readiness, toggles languages three more times and
  verifies identical handles and one completion. A cancelled subscription stays
  cancelled. The test restores its original language list.
- The same test fails on d252cbb on API 26 with the precise assertion
  `Disabled RU must not complete a background load`, then passes on the candidate.
  That task-owned ARM64 emulator has configured RAM 2,048 MiB and measured
  MemTotal 2,054,364 KiB. The candidate also passes on physical Fold/API 37.
  These are actual ADB runs with no skipped instrumentation cases, in the separate
  `.qualification` application guarded before any preference mutation.
- Three secure IME settings are unchanged in each run. The Fold was coordinated
  with both other device chats. Its initially absent qualification app/test
  packages were removed after the run, and the window explicitly released.
  The main Rune package was not updated or selected. The owned API 26 emulator
  remains available for the next U17 profile slice.
- Final JVM suite: 1,275 tests, zero failures/errors/skips; fixed trace vocabulary
  test includes all five markers. Debug lint, app/test APK builds with
  `-PruneNativeQualification=true`, and scoring-boundary verification pass.
- A fresh candidate packaged-reader replay, after strict asset preflight,
  matches the previous bound packaged run on all 12,000 ordinary rows. Only the
  two host timing fields are excluded. Projection SHA-256 is
  `33c3a96fed5b3322601f6b7a0307e3a4b62bfbc9bc7650b82bf644a1afffd8a3`.
  The new telemetry enum is included in compilation; the Android lifecycle is
  covered by the native test, not the host harness. Source/asset/reference/output
  bindings are in the adjacent evidence JSON. Existing EN/ES quality limitations
  and the absence of native inference in this replay remain unchanged.

Two earlier build attempts stopped on lint's UnclosedTrace analysis of the
asynchronous worker. After the second failure the worker was split into a
synchronous traced load method and a separate bounded asset reader, without a
suppression or weakening lint. The corrected builds above pass. Initial ADB
preflights also stopped before installation because pm path returns nonzero for
an absent package; the runner now checks the package inventory explicitly. Those
attempts and final successful outputs are retained separately.

The debug lifecycle timers are single instrumented observations, not a startup
benchmark or before/after performance result. U17 stays open for profile-build
traces and PSS/startup comparison on Fold and constrained API 26, followed by the
owner-package update and typing regression.
