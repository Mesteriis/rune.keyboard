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

## 2026-11-23 TalkBack language-order actions

On a disposable API 37 ARM64 emulator, TalkBack 17.0.0.889642762 with touch
exploration enabled focused the English and Russian **Move down** buttons.
Both native buttons exposed the same label. The screen reader could identify
the action, but the focused control supplied no language name. The fix adds
the language name to the accessibility descriptions for both directions in
the EN and RU interfaces. The visible labels stay compact.

The repeat used touch events injected at the virtual touchscreen through ADB.
A passive Android `UiAutomation` observer with
`FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES` recorded TalkBack focus events;
it issued no focus or activation actions. The observer found distinct labels
including `Move English down`, `Move Русский down`, `Move Español up`, and
the localized `Опустить язык «Русский»` and `Поднять язык «English»`.
The real IME also exposed `Symbols`, `Space` and `Delete` to TalkBack focus.

The first activation probe used a click event as its success signal and could
not confirm activation. The follow-up focused `Move English down` and injected
a double tap. Rune persisted the expected change from `ENGLISH,RUSSIAN,SPANISH`
to `RUSSIAN,ENGLISH,SPANISH`. A separate Android Settings control confirmed
that the same double-tap method opens the focused Apps page. The Rune observer
again saw no click event for the rebuilt row, so the saved ordering is the
independent activation check. Linear traversal and spoken audio were not
verified by this probe.
[Google TalkBack settings and feedback](https://support.google.com/accessibility/android/answer/6006589)

The new instrumentation method checks both descriptions and the endpoint
disabled states for all three languages before and after reordering. Android
debug lint passed. All six settings methods passed on API 26 and again on
API 37 with TalkBack disabled for those ordinary instrumentation runs. The
API 37 live screen-reader check used the same patched debug APK. Physical Fold
and the remaining settings screens still need reader coverage.

## 2026-11-24 TalkBack settings traversal and search

TalkBack 17.0.0.889642762 ran on a disposable ARM64 API 37 emulator with
touch exploration enabled. Touches went through its virtual touchscreen over
ADB. The passive event observer retained TalkBack focus events and native
Switch state. It did not issue any focus or activation actions.
[TalkBack gesture documentation](https://support.google.com/accessibility/android/answer/6151827?hl=en)

Sequential navigation reached the correction controls. Double-tapping
Candidate strip updated the persisted setting and returned focus to the
same Switch in its new state. The next swipe focused Double space inserts
a period. Show an undo button kept its stored checked state while disabled
and exposed the missing strip prerequisite. Turning the strip back on
restored that control's enabled state.

In Experiments, TalkBack reached the disabled Apply dynamic touch Switch,
including its RU badge and prerequisite text. Activating Dynamic touch
experiment enabled it. The bulk disable action reset both experiment
preferences. On Dictionary and learning, double-tapping Learning lab
opened the actual lab activity. The flow's event SHA-256 is
`d3682c593a9e1aecc841f2f0bed00da3674b7d7573b296521d7acf96320403d7`.

Selecting Candidate strip from search reproduced a focus defect. TalkBack
focused a combined description of the detail page. The next swipe landed
on Back. The settings directory's focusable container remained focusable
after opening the detail page.

The detail container now leaves its native children as focus targets.
Search transfers input focus to the selected control during touch
exploration. For a disabled control explicitly chosen in search, the
one-time accessibility focus action is scoped to that result. This
exposes the reason without enabling the control. Lint rejected the
initial version that forced accessibility focus on all search results.
The final code passes lint and only uses that action for disabled results
selected by the user.

With the fixed APK, Candidate strip received TalkBack focus as a native
Switch. The next swipe reached Double space inserts a period, and Back
restored the search query. An off-screen search result for Apply dynamic
touch received focus as a disabled Switch with its reason and badge.
Attempted activation preserved its stored `false` value.

| Trace | SHA-256 |
| --- | --- |
| Before the search fix | `4c704fa34a4018ccb2439172a9aab51d9fd172829fe6bd91e91cd693a4344823` |
| Fixed search and Back | `56a553da1a4f7f8d72348fde710f0d3b89f03f654d2c400548a44f9c1f7f5a4d` |
| Fixed disabled result | `b314eebd226e4867bfe3141331ecedf31b5dbcbb00ef9187ba6169d90434202d` |

All five AppMenu instrumentation cases passed with TalkBack off, including
search, activity recreation and Back. The instrumentation log SHA-256 is
`0c9933904a75ee1267ab9798a6d92ec3d0291538fe90a720f685b2b726710d3d`.
The debug APK digest is
`ed5b9aa674024143d89ae766cafd64228dbb94b207a4bc26e94f59964175a339`.

The observed scope is English settings, touch exploration, focus, and
activation on API 37.

## 2026-11-24 TalkBack text submitted to speech synthesis

On a fresh disposable ARM64 API 37 emulator, TalkBack 17.0.0.889642762
used a test engine implementing the Android
[TextToSpeechService API](https://developer.android.com/reference/android/speech/tts/TextToSpeechService).
The engine captured synthesis requests and returned silence. Gestures
went through the virtual touchscreen. The passive event observer verified
native Switch focus, checked state and availability. The Rune debug APK
from `8cc3d9bc` had SHA-256
`4f8e3cd86ac0249190b9766149035623d7d8a3e050ff3c64cc3bcb75725f1c2d`.

| Search result | Native state | Text submitted after choosing the result |
| --- | --- | --- |
| Candidate strip | Enabled, checked | ON, Candidate strip, the setting description, Switch, Double-tap to toggle |
| Apply dynamic touch | Disabled, unchecked | OFF, Apply dynamic touch, Experiment · RU, the prerequisite and remedy, Switch, disabled |

The focus trace SHA-256 is
`0792d6c53a513399704ae0e186b33d5f53d17507cfdcdde80ddb30704284e4ea`.
The captured English utterance JSON digests are
`b5e594ea6e3e918aec2de9c421d53896889fca73fe7a2880f50f8a12ea10e855`
for Candidate strip and
`ad975660235f6c50836a362e3c41258df1a20891fb5c848c7425fbd84f19ca82`
for Apply dynamic touch. This verifies the text supplied to synthesis.
Listening to rendered speech and the review's section 9 Fold run remain open.
