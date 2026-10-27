# U8 — cross-process EditText selection prototype

U8 explicitly requires a device prototype before choosing the selection mechanism.
This test-only slice supplies that evidence. It does not implement or qualify the
editing panel. Production main/debug sources and the built production APK are
unchanged from the U6 slice at a444f78.

EditingSelectionPrototypeInstrumentedTest captures the resident Rune service’s
actual InputConnection after checking the selected package. It dispatches events
on the IME main thread into the existing ObservedEditText in :qa_editor. Outcomes
come from the fixture’s numeric selection/length/call counters; sendKeyEvent(true)
alone is never treated as movement. The emulator guard runs before ImeTestDriver
can change a setting. No failure screenshot rule, personal fixture, clipboard read,
model injection or production editing API was added.

Observed Android 36 arm64 outcomes:

| Protocol | Observed selection | Ordinary arrow after the protocol | Payload reads |
| --- | --- | --- | --- |
| Two Left pairs with only META_SHIFT_ON | Collapsed 2,2 from caret 4 in fixed ASCII input; no extension | Right moves to 3,3 | 0 |
| SHIFT_LEFT down/up around two Left pairs, arrow meta=0 | Anchor 4, extent 2 | Right collapses to 4,4 after Shift-up | 0 |
| SHIFT_LEFT down/up plus META_SHIFT_ON on two Left pairs | In fixed a+emoji+b input: 4,3 then 4,1, without splitting the emoji’s UTF-16 pair | Right collapses to 4,4 after Shift-up | 0 |

The successful bracket protocols each report four Down/four Up events. The
flags-only negative control reports three/three. Six payload counters — before,
after, selected, extracted, surrounding and snapshot — are exactly zero both
before editing commands and afterward. Numeric cursor-caps requests are outside
this payload-read assertion. Test preparation commits only the fixed public seed
through the Binder connection; it is not editor-content acquisition.

The initial exploratory run has three failures and is preserved. Its flags-only
probe expected extension but observed 2,2, establishing the negative control.
Both explicit-Shift probes reached the required selection/release assertions but
found snapshot=1 after accessibility ACTION_SET_TEXT preparation. The corrected
fixture changes that preparation to direct commitText and asserts zero counters
before any editing event, with no subtraction or ignored counter. All three final
tests pass with no skips. This isolates the successful command path from the
initial preparation’s snapshot observation; it does not claim a diagnosed product
privacy defect or remove a production snapshot read. No production source changed.

Decision for the next implementation slice: bracket each extending-arrow command
with explicit Shift Down/Up and retain arrow meta for editors that use event flags.
Always release in finally; do not retain a held synthetic Shift between user actions
or retry with a second selection protocol after an uncertain action. This is an
EditText-supported choice for further validation, not universal editor compatibility.

Boundary/privacy/lint and debug/test builds pass. The first compiled draft was
corrected before device execution to avoid nesting the existing keyboardSnapshot
main-thread helper inside runOnMainSync. Complete logs, build exits, raw initial
failure, final numeric protocol traces and APK/source identities are bound by the
adjacent JSON. The isolated emulator is stopped/deleted. No Fold was used. The full
JVM suite and product replay were not rerun for this instrumentation-only slice.

Still required for U8: editing layer and entry popup; direction/selection/context-menu
commands and repeat; TYPE_NULL and single-line restrictions; ownership invalidation
and awaitEditorSelection for cut/paste; explicit test-process clipboard setup;
post-paste foreign-boundary regression; JVM reducer/executor/layout coverage;
EditText/WebView/Compose integration, physical validation, manual TalkBack and
clipboard/privacy/user documentation. The card remains in progress.
