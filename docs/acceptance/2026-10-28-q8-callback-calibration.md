# Q8: receiver-side callback calibration

The debug IME now exposes an explicitly started, 128-entry RAM-only trace of
six fixed boolean flags. It records only callbacks for Rune-owned editors.
There is no text, position, app identifier, file, network or log access in the
trace provider. End clears it; overlapping begin is refused. Release/profile
providers are exact stateless no-ops, checked by the architecture gate and
negative mutation tests. The normal diagnostics format and recording consent
remain unchanged.

Native instrumentation drives real Rune keys and InputConnection/Binder calls
in an Android EditText and an offline HTML WebView. It reports flag sequences,
public test outcomes and numeric counters, never a screenshot or UI hierarchy.
All payload-read counters must stay zero. Four scenarios cover same-region
no-op, selection before composition, external prefix shift and five consecutive
WebView words. A private initial QA editor and a diagnostics writer fence isolate
persistent-store assertions from pre-existing lifecycle writes. Package/field
checks guard the direct InputConnection operation and public editor lookup.

## Calibration

Final measured outcomes and exact APK/source hashes are in the adjacent evidence
receipt. The fixture requests a 100 ms two-phase delivery; it does not assume that
Android delivers every producer callback. The receiver-side sequence establishes
what reached Rune. On both tested platforms the split callback disables Smart
Typing and later span cleanup preserves `teh `, including its first letter.
This is conservative availability, not a successful automatic correction.

The no-op test measures the absence of a delivered same-region callback rather
than fabricating one. Correction and exact Undo still work. Prefix insertion
preserves `X hello`, disables Smart Typing and accepts later literal `x` without
losing the existing word. The offline WebView test checks all five words and
reports how many corrected and whether the last one corrected.

## Failures retained

The first API 26 run failed three methods because the driver's exact fixture-mode
allowlist omitted the new modes. Its WebView case passed. The allowlist was fixed.
The first Fold run reached all four functional outcomes but failed all four
persistent-store assertions: setup had left pending ordinary-editor SESSION and
CONFIGURATION records. A private first editor plus explicit writer fences fixes
the test boundary without deleting records or changing recording consent.

Before/after owner archives show those diagnostic files only gained lifecycle
metadata, with no INPUT or text-payload events. Original diagnostic bytes are
retained. Full preference maps, personal data, model inventory and IME selection
are checked separately after final device teardown. The rollback APK and private
archives remain local, ignored and access-restricted.

## Integration checks

All 1,355 JVM tests and 72 diagnostics-boundary tests pass, with zero skips.
Debug/test APK compilation and debug lint pass. Source commit `ed275e5` passes
`imeIntelligenceBoundary privacyGateRelease privacyGateProfile` in a separate
tracked-clean checkout, offline, with the source-clean guard passing both before
and after. No signing material was copied.

Both previous replay receipts were revalidated against every bound file: all
174 and 177 hashes still match. Their 2,160 and 12,000-row deterministic baseline
results remain applicable to the unchanged replay implementation; this slice did
not rerun those JVMs or change their baselines.

The Fold has the exact tested debug APK. Its four native tests and all four API
26 tests pass with zero skips; both produce the same flag sequences. All six
personal-store snapshots stay unchanged within each final test, and the complete
post-teardown owner checks preserve original preference values, existing
protected data/model bytes, original diagnostic bytes and IME settings. The only
appended diagnostic events are SESSION/CONFIGURATION lifecycle metadata. The
owned emulator is stopped/deleted and both coordinating chats have been told the
Fold is free. Five unrelated pending files retain their original hashes; all
98 original untracked paths remain.

## Remaining scope

This calibrates owned EditText/WebView profiles on API 26 and Fold, not the full
APP-001 through APP-005 compatibility matrix. No admission threshold, timing
window, model, ranking or Undo authority changes. Silent unreported span removal
and editor cleanup refusal remain the documented simulator limitations. Q8 stays
in progress.

## Current Fold follow-up

At source `b48d73c2`, a clean temporary checkout built the debug application
and test APK. The application was updated on Fold with `adb install -r` after
its signer matched the installed app; installed APK bytes matched the build.
The selected IME, preference file bytes and original diagnostic-file bytes were
unchanged immediately after installation. The existing test package was then
updated with a matching signer.

All four `EditorCallbackProfilesInstrumentedTest` methods passed on Fold with
zero skips, using the private QA editor and disabled failure artifacts. The
instrumentation's personal-store checks passed, the selected IME remained
unchanged, and all original diagnostic bytes were still present. The aggregate
byte comparison of all shared preference files changed during this first run;
the before-image was not retained, so exact per-file or semantic equality for
that first run is **not established**. The driver attempts to restore the
captured preference map. A subsequent single no-op scenario passed and showed
unchanged keyboard and diagnostic preference values and bytes; the separate
Android ActivityThread IDs preference changed. This repeat cannot retroactively
prove the first run's preferences were identical. No raw logs or user text were
retained. Temporary build files were removed. This is not the full APP-001–005
matrix, a hosted CI run, or independent qualification.

The QA driver now checks both the preference commit result and equality of the
restored map, rejects unsupported value types and attempts to restore IME state
even if preference restoration fails. A clean temporary checkout with this
driver built the test APK; the physical Fold no-op/Undo scenario passed with
that APK. Keyboard and diagnostic preference values, the selected IME and all
pre-existing diagnostic bytes matched before and after that run. This exercises
the successful restoration path on device; a simulated preference-write failure
was initially not run. A subsequent four-case instrumentation test used an
in-memory fake to verify successful restoration, a failed commit, mismatched
readback and an unsupported value type. All four passed on Fold without
changing the owner's preference values or selected IME. The first test build
failed on an unspecified empty-map type; the corrected build passed. The
device-wide cleanup after an injected failure was not separately exercised. The
earlier four-test run's per-file snapshot remains unavailable.

## Fold Termux raw-editor follow-up

On the Fold, an explicitly created Termux 0.118.3 session exercised the
`TYPE_NULL` editor with Rune touches. The test observed a fresh shell prompt,
typed a synthetic string, checked Backspace, completed `true`, pressed Enter
and observed the shell return to a prompt. It does not measure the command's
exit status or cover inner/landscape displays. The device reported `CLOSED`
before and after; fold state was not continuously monitored.

The [matching Termux source](https://github.com/termux/termux-app/blob/v0.118.3/app/src/main/java/com/termux/app/TermuxActivity.java)
describes the `ACTION_RUN` session path; process and foreground checks were
also performed on the actual device. The first run stopped before entering text because the original keyboard was
Russian. The repeated test temporarily switched to English and restored the
original language and complete preference snapshot in `finally`. Before each
run the owned terminal was checked for a single shell and no other processes;
the newly created shell was closed afterward with terminal EOF. The selected
IME, keyboard and diagnostic preference values and original diagnostic bytes
were unchanged. No terminal transcript or raw instrumentation log was saved;
temporary build files were removed. The earlier owner-only diagnostic recovery
backup remains retained. This is partial APP-005 evidence, not full Q8 closure.
