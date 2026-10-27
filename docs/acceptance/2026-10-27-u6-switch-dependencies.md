# U6 — native switches and settings dependencies (partial acceptance)

This continues the registry/page slice at e06082b. U6 remains in progress because
its explicit manual TalkBack acceptance has not been performed. It does not close
the whole review or establish physical Fold acceptance.

All shared settings toggles, including debug diagnostics, now render a framework
android.widget.Switch. SettingsToggleRow gives the native switch a combined title,
optional RU badge and summary/reason, with native checked/enabled semantics. Row
and label nodes do not create additional accessibility targets. Touching the full
row still invokes its existing action. Native Switch clicks return to the confirmed
value before invoking that action: async writes and consent dialogs cannot display
an unconfirmed opt-in. Disabled row/native calls do not persist a change.
Language-selection checkboxes remain independent multi-select controls.

The registry owns settings-level prerequisites. Seven Russian-only experiments
share the visible “Experiment · RU” badge and require Russian among enabled
languages. Phrase suggestions, word boundaries, abbreviations, phrase review,
visible Undo, learned ranking, compact context and manual candidate expansion
require the candidate strip for their UI control. Dynamic-touch application
requires its shadow experiment; the shadow experiment is independent of the
candidate strip. Unavailable switches retain the stored choice, expose the first
missing prerequisite and become available again when it is restored. These checks
do not promise live editor/resource availability. Disable all stays available.

Collection and pattern learning remain independent multilingual opt-ins. The
learning-lab navigation summary reports their conjunction for night checks; manual
evaluation/reset remains accessible when collection is off. No worker, learning,
correction/admission or storage-format behavior changed.

Validation:

- All 1,202 JVM tests pass with zero failures/errors/skips, including three new
  dependency/property-retention tests in addition to the four registry tests.
- IME boundary, release privacy, debug lint, debug and test APK builds pass.
  A later test-only build/lint also passes.
- Twenty-five distinct final emulator scenarios pass in bounded groups (19 settings
  and six diagnostics), with no failures or skips. The adjacent receipt binds the
  raw successful outputs and exact method set. They include
  five new dependency/native-semantics/touch tests, five menu tests, three typing-tool
  tests, five typing-control tests, one schema-3 Undo migration test and all six
  diagnostics tests. The strict runner rejects ignored or assumption-skipped tests.
  Earlier separate 12-test and 8-test runs passed. A subsequent 20-test combined
  run had 19 passes and one failure: after a coordinate click on the text-diagnostics
  Switch the scope dialog was not observed. That failure is retained; its cause
  was not established from the post-teardown state. Consent tests now activate
  the native Switch through framework ACTION_CLICK, retaining all dialog/state
  assertions. A separate test still injects real touches into the visible Switch
  and label and verifies both persisted changes. This is not a claim that the
  earlier coordinate failure was a diagnosed/fixed product defect. An extended
  combined 25-case run reached its 240-second host observation timeout; its partial
  stdout was not preserved by the earlier capture helper, and no pass is inferred.
  Later target-process absence was observed before any new run. The final groups
  use a streamed-to-file helper that retains partial output and a typed timeout
  outcome. They partition the same assertions into bounded explicit runs. In an
  additional four-case diagnostics run, three pass and the management navigation
  test fails: the delete control is absent after its coordinate navigation click.
  The saved synthetic screenshot/tree confirms settings remained active. Navigation
  is now also activated through the existing view ACTION_CLICK; deletion and
  stream-removal assertions are unchanged. Final diagnostics coverage runs all six
  methods. The separate 19-case settings run has unchanged test sources and an
  identical production APK; the receipt binds both test APKs explicitly.
- Tests exercise native Switch and full-row clicks, actual observed-bounds touch,
  framework accessibility activation, checked persistence and
  recreation, disabled programmatic dispatch, RU-off dependencies and common
  badge/name/role/state, dynamic-touch gating, all four night-setting combinations,
  14 existing independent controls, search/visible requested-row/recreate/Back,
  disable-all data retention and both separate diagnostics confirmation dialogs.
  The old Undo section assertion now checks the actual next mechanical control:
  its former Tools section moved to EXPERIMENTS. Diagnostics UI selectors target
  the single named native Switch while in-process row IDs remain stable.
- The Russian distribution 02-settings screenshot is replaced by a fresh native
  capture on this disposable Android 36 arm64 emulator. A second experiment-page
  capture is adjacent under images/. Both were inspected visually. The empty
  per-app locale list is observed before capture and restored after Russian
  capture. Images show synthetic post-test settings, not promised fresh defaults
  or Fold UI. No pixel editing, physical-device images or personal data were used.
- All 88 prior ordinary-replay source bindings and 18 static assets still match;
  no new replay execution, accuracy, performance or native/API-26 acceptance is
  claimed by this settings-only change. The emulator is stopped/deleted afterward.

Outstanding U6 acceptance: manual TalkBack traversal, announcement and activation
on the real settings screens. Native-node and UiAutomator evidence above is useful
but does not substitute for that manual check. The whole review remains open.
Exact source/artifact/log identities and outcomes are in the adjacent JSON.
