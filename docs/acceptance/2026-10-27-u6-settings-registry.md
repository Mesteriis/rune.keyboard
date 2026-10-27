# U6 — settings registry and experiment destination (partial)

This is the first U6 implementation slice, not full U6 acceptance. The shared
AdditionalFeature registry owns all 18 optional persisted keys, title/summary
resources, typed KeyboardSettings properties and page destinations. Settings
constructs every optional toggle from the registry; page lookup consults it and
the atomic disable-all transaction iterates it. A registry-only writer rejects
unknown/core keys before writing. Existing keys, defaults, migrations and legacy
writer methods are retained.

The seven actually Russian-only features move to EXPERIMENTS, together with
“Disable all”: word boundaries, phrase review, learned ranking, compact context,
dynamic-touch shadow/apply and manual candidate expansion. The evidence is the
current TypingFeaturePolicy, ExperimentModels, DynamicTouchContext and manual-pool
CandidateGenerator guards. Example collection and typo-pattern learning are
multilingual and remain in DICTIONARY. Existing APPEARANCE/TYPING destination names,
EXTRA_PAGE, requested-row lookup and search are retained. The guide documents the
new routes and corrects the disable-all count from 17 to 18.

Validation:

- All 1,199 JVM tests pass (zero failures/errors/skips). Four new tests verify the
  exact 18-key/property mapping against actual codec decoding, unique titles,
  one-transaction disable-all snapshots and unrelated preference retention,
  rejection of unknown/core keys, registry page ownership and stable page names.
- IME boundary, release privacy, debug lint and debug/test APK builds pass.
- Eight menu/tool instrumented tests pass on a fresh Android 36 arm64 emulator,
  including all seven experiment search destinations and 14 existing independent
  controls across recreation. The navigation test was then strengthened to await
  actual row visibility both after search and after recreation; its final rerun
  passes (one test). It also checks Back restores each query and direct EXTRA_PAGE
  opening exposes the disable-all row. No screenshot or manual TalkBack claim.
- A subsequent test-only build and lint pass. The strict device runner rejects
  ignored/assumption-skipped tests. The emulator is task-owned and disposable;
  cleanup is recorded separately. No phone or personal data was used.
- All 88 sources and 18 assets bound to the prior U5 ordinary replay are still
  identical. This is an identity check of prior evidence, not a new replay run;
  no new autocorrection accuracy or runtime-performance claim is made.

Still required for U6: dependency-driven enabled states, shared RU badge,
framework Switch and all affected casts/semantics, associated regressions,
manual TalkBack, and updated 02-settings screenshot. The review card stays open.
The adjacent JSON binds current sources, artifacts, commands and outcomes. Raw
local logs live under build/review-u6-registry-20261027/ and are not public phone logs.
