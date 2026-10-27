# U1: visible Undo defaults and source parity — local acceptance

Four regressions failed against 240b9b8: missing fresh/default migration behavior,
missing atomic preservation of schema-3 Undo-off, and missing next-word Undo for
model and canonical corrections. That run executed 140 tests with four failures.

Settings schema 4 defaults visible Undo on for fresh maps/current schema. Schema
3 remains supported; its missing key stays false, and explicit boolean choices
remain authoritative. Every existing writer now persists the decoded Undo choice
with normalized Smart Typing fields before stamping schema 4 in the same editor
transaction. Thus an unrelated setting cannot turn an old missing/off choice on.
Future numeric schemas remain preserved and effectively disabled; malformed values
fail closed. The UI toggle now belongs to Smart Typing, immediately after the
mode control. Read-only decode still does not write preferences.

Ready model, late model and admitted canonical Space corrections create a
previous-word ticket for visible Undo. Their tickets have refinementAllowed=false:
no refinement request can be created even when a test separately enables its
qualification and thresholds. Existing local refinement behavior is unchanged.
The ticket preserves the original correction and live next-word suffix. Backspace
behavior, Original → Undo → remaining ordering, maximum visible cells and the
8-second visible window retain their existing contracts. No confirm-original
behavior or new protection chip was added.

The late canonical path remains refused by its existing local admission check.
A supplemental test initially assumed it was admitted; source inspection showed
that this was incorrect. The final negative regression preserves that refusal
rather than broadening admission to satisfy an Undo test. No spelling threshold,
source qualification, model parameter or packaged data was changed.

Validation:

- Final full JVM suite: 1,174 tests, zero failures/errors/skips; six new tests.
  Includes schema-3/4 enabled preference parity, explicit/off/future migration,
  ready/late model and canonical next-word Undo with refinement denied, and late
  canonical refusal. Existing 8-second, stale-action, ownership, failure and
  local-refinement regressions pass.
- IME intelligence boundary, release privacy gate, app/test builds and lint pass.
- Current-source replay of the exact 4,788 + 3,648 + 3,576 historical public inputs
  completes all 12,012 rows. Boundary/Backspace documents and commands, admission
  results and exact restoration match the before-change run; no error rows or
  Undo failures. This is historical regression evidence, not fresh qualification.
- Seven Android 36 emulator instrumentation tests pass: real model-service/editor
  Binder ready/late paths and real canonical input retain visible Undo after the
  first next-word letter; actual UI clicks restore only the prior word; real
  preferences preserve schema-3 off during migration; settings placement/toggle/
  recreate work; candidate order/action and hidden stale-cell tests pass.
- One additional real-settings EN/RU copy/persistence regression passes. The model
  backend in the Binder fixture supplies public numeric test scores; those tests
  are execution/ownership evidence, not downloaded-model quality or performance.

USER_GUIDE and ARCHITECTURE disclose the default, migration and downgrade effect:
older schema-3 readers treat stored schema 4 as future and disable effective Smart
Typing until a compatible build returns. Existing unrelated guide changes remain
unstaged. Copy now describes show/hide and the source-independent Undo window.

The disposable emulator and fresh AVD were removed after tests completed. The
adjacent JSON binds sources, APKs, replay inputs/receipts and actual check outputs.
**U1 remains open for the review's physical Fold acceptance.** No Fold installation,
paired-phone action, remote CI or full-review completion is claimed by this step.
