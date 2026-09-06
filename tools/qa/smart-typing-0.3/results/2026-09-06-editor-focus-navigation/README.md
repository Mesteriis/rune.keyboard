# QA editor focus navigation — 2026-09-06

The134-test API37 run failed before custom editor action dispatch. A one-case
regression reproduced it: the target was visible at(66,1973)-(1014,2097) but never
gained focus. Temporary numeric debug events showed the parent ScrollView
intercepting the single DOWN/UP at the correct center, immediately after scrolling.
The actual custom EditText received neither touch nor focus.

Initial `waitForIdle`, UiObject2 scrolling and disabling fling alone all failed;
those logs and source variants are retained. An accessibility idle or unchanged
geometry did not establish animation completion. Android's
[ScrollView source](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/widget/ScrollView.java)
(blob184933fb8288bb081e863a5883702ee49fe7d46c) checks both the scroller and edge
effects when deciding whether to intercept a new DOWN. Disabling both inertial
fling and overscroll stretch on the default debug QA surface removed interception.
Editor widgets, action dispatch, Binder connections and product IME code remain
unchanged. These tests do not qualify ordinary ScrollView animation behavior.

The diagnostic variant passed2/2: the formerly offscreen custom editor received
actual DOWN/UP and focus, and the already-focused editor restored the keyboard
after explicit hiding. Temporary event logging/overrides were then removed. The
final source retains only the debug navigation configuration and content-free
focus-failure ID/bounds/focus context in the driver. Legacy scroll navigation,
unchanged IME timeout, one focus tap and exact remote action/text assertions remain.

The final **trace-free API37 scope passed4/4**,188.177s: both navigation cases and
the existing multiline/six-action editor matrix. APK/source identities are in
`live-fake-focus-input.json`. The earlier full-suite failure remains in the134-test
archive; a complete139-test run is separate. No root cause or PASS is inferred
from a successful unchanged retry. Later non-normal editor extensions are outside
this receipt and require their own verification.
