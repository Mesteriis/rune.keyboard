# Personal typing: integration evidence (2026-09-15)

## Delivered behavior

1. Russian exact dictionary membership guards rare correct words. The APK contains a
   reproducibly generated OpenCorpora index of 3, 063,710 forms (28,591,430 bytes), mapped
   and validated on a worker. Missing/corrupt evidence vetoes Russian word substitutions.
2. Automatic admission is separate from visible suggestion order. Equally plausible
   candidates in different or ambiguous lemma families remain manual suggestions. The
   guard runs on immediate, delayed local and delayed model correction paths. Existing
   spelling/model qualification remains authoritative; personal evidence cannot grant it.
3. Explicit accepted candidates, keep-original choices, confirmed undo and close manual
   retypes produce distinct bounded local signals. Ordinary Backspace alone is not a
   rejection. Failed/stale/reentrant edits never train. Turning learning on/off starts a
   fresh owned context; undo and finish boundaries cannot leak stale retype evidence.
4. Physical key contacts calibrate bounded per-key offsets only after explicit word
   confirmation. Layout, language, viewport size, orientation and exact geometry isolate
   profiles. Accessibility clicks, alternatives, cancelled/multi-pointer gestures, private
   fields and unconfirmed automatic replacements do not train. Tap likelihood changes
   manual suggestion order; it does not silently change the character dispatched by a key.
5. Repeated, spelling-validated continuations appear after an owned space and insert only
   after an explicit tap. One/two-word continuations use one/two-word context. IDs bind to
   the current session and candidate epoch. Imported frequency never certifies spelling.

## Controls and privacy

Personal learning, touch personalization and phrase suggestions are separate settings,
all absent/malformed/unsupported values default off. Existing correction guard is always
active. InputPolicy.SENSITIVE, no-personalized-learning flags, nontext fields, selection,
language/layer and editor ownership checks remain in force. Stores are bounded atomic
files under no_backup with background I/O, shared process ownership, explicit reset and
no network operations. Reset UI confirms success only after both stores acknowledge disk
writes. Private chat exports/profile artifacts remain in ignored build/private; none are
tracked, bundled or uploaded.

The offline profile exporter produces at most 1, 024 supported phrase entries from the
existing local style model. An exported profile is private data and must be imported
through Settings; it is not a spelling approval list or neural weight update.

## Verification

Environment: JDK 17, repository-pinned Android toolchain, Android API 37 emulator.

- `:app:testDebugUnitTest`: 848 tests, 0 failures/errors/skips.
- `python -m unittest discover -s tools/morphology -p 'test_*.py'`: 62 tests, PASS.
- `:app:connectedDebugAndroidTest` filtered to `PhysicalTouchInstrumentedTest` and
  `PersonalizationInstrumentedTest`: 7 tests, 0 failures/errors/skips. Covers physical
  contacts and exclusions, exact dictionary in APK, profile import/invalid import,
  durable personal reset and durable touch reset.
- `:app:lintDebug`, `:app:assembleDebug`, `:app:privacyGateRelease`: PASS.
- `:app:imeIntelligenceBoundary`, `:app:forbiddenRuntimeDependencies`: PASS.
- Qualification metadata verification and debug/release diagnostics packaging: PASS.
- `git diff --check`: PASS.
- Independent review found three integration issues; all fixed with regressions, scoped
  re-review clear. Logs and reports retained under ignored build/personal-typing.

Initial build failed because the isolated worktree lacked the native submodule and was
pointed at an absent SDK. Local pinned submodule and installed SDK restored; gates above
ran without bypassing qualification or test tasks.

## Limits

No new human-labelled unseen accuracy claim, speed/energy claim on Fold, or neural
fine-tuning result. Synthetic tests verify mechanics and exclusions. Tap training skips
insertion/deletion alignments. Russian dictionary guard adds about 28.6 MB to APK assets.
There was no connected physical phone during final validation; deployment to the user's
phone was not performed. Release artifact is unsigned without the user's release key;
the debug APK is the available installable test artifact.
