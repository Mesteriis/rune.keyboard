# U8 — external-edit ownership boundary guard (partial)

The editor commands at 4ab8792 must not be exposed before their unknown adjacent
text is separated from Rune’s owned word. The existing awaitEditorSelection clears
context but, after a changed callback, permits a fresh composing suffix immediately.
An initial regression reproduces that failure (59 targeted tests, one failure):
the suffix is adopted as a Rune word even though it may continue pasted text.

TypingSessionController.prepareExternalEdit now finishes/disowns the current span,
optionally waits for actual selection, and requires a new Rune whitespace boundary.
New text before that boundary is committed literally without creating a composing
word, candidate identity, punctuation transformation, retained context or phrase
learning. The rich typing entry also takes this path before correction/mechanics.
A single Rune Space owns only that newly inserted delimiter and restores normal
pending-space composition; other trailing whitespace retains only its own suffix.
Earlier unknown characters are never adopted into context. Selection callbacks,
ordinary finish/invalidation and a layer-style boundary do not remove this guard.
A true session end/disable resets it. Dispatch refusal cannot revive ownership.

The old caret-wait helper also protects a newer reentrant wait: a failed finish or
changed session returns without clearing the newer flag. A separate targeted
regression first reproduces the same-session overwrite (68 tests, one failure).
A sentence-capitalization control already passes through the existing Undo-state
cleanup; no separate capitalization patch was needed.

Validation:

- All 1,218 JVM tests pass with zero failures/errors/skips. Ten new cases cover the
  opaque suffix, late own acknowledgements, layer invalidation, no-movement entry,
  mechanics/phrase isolation, whitespace recovery, newline suffix, fresh-session
  reset, different/same-session reentry, rejected finish and old capitalization.
- IME/scoring boundary, release privacy, debug lint and debug/test APK builds pass.
- Eight final Android 36 arm64 emulator scenarios pass without skips: two new
  service/controller guards, three command-executor cases and three prototype
  controls. The new tests call the actual resident controller and service edit
  executor, then use the real Binder connection to :qa_editor. Public editing
  actions are still not wired; test-only reflection supplies this caller.
- In the paste case, the fixture types an owned prefix, prepares the external edit,
  pastes a fixed public fragment supplied by the test process, and types `teh`.
  The adjacent suffix remains literal with no composing word/candidate/context.
  After a Rune Space, the same qualified `teh → the` correction works again.
  In the cut case, removal between fixed left/right fragments cannot correct the
  newly inserted adjacent suffix. Actual field text and numerical selection are
  observed by the test; all six InputConnection payload counters remain zero.
  Paste is explicitly checked to stay in the same session for this evidence.
- A fresh 12,000-row ordinary product replay has zero changed projections after
  excluding only hostStageNanos/fullTokenGenerationNanos. Both projection hashes
  are identical and all metrics match. The baseline was reused only after checking
  every one of its 88 source bindings and 18 runtime assets before this edit.
  The final candidate is recompiled from bound current sources. This ordinary
  harness never calls prepareExternalEdit; native/JVM checks above cover that path.
  Existing EN precision/volume gate limitations and the ES holdout’s one aggregate
  false change remain; zero new false changes is not full release qualification.
- The test-owned emulator is stopped/deleted. No owner data, physical Fold,
  clipboard acquisition by the IME, downloaded-model scoring or latency claim.

Remaining U8: connect reducer/layer/popup/repeat and service candidate invalidation;
choose the new guard for entry and editor-resolved actions before dispatch; retain
protection correctly across app-driven input restarts/editor identity changes;
apply single-line/raw presentation restrictions; test the full public path in
EditText/WebView/Compose and Fold; manual TalkBack and clipboard/privacy/user copy.
The guard currently belongs to one controller session and the native proof is
same-session EditText only. The whole U8 card and review remain open. Adjacent
JSON records exact sources, APKs, commands, logs, replay bindings and outcomes.
