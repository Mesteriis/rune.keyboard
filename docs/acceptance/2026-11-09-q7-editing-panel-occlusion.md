# Q7: editing-panel failures and emulator starting-window evidence

The full Android CI shell at `f343e913` was interrupted after the general
suite reported 147/366 cases, 16 skips and three failures in
`EditingPanelInstrumentedTest`. The complete suite did not finish and this is
not a passing CI run. The three failures expected editor content but observed
the empty composing fixture's hint instead.

The isolated API 37 emulator's system log recorded 13 untrusted-touch
occlusion events and 37 starting-reveal animation timeouts during that run.
For the recorded dropped touches, Android identified a fullscreen Rune QA
starting window above the IME. These records establish that touches were
rejected, but do not prove that all three individual failures have this cause,
or why the starting window persisted.

Matching `TestRunner` start and finish markers to the system log narrows the
association: the three failed methods respectively contain 4, 1 and 4 rejected
touches and 10, 4 and 12 starting-reveal timeouts. The first such timeout in
the captured log occurs during the preceding `rawEditorsHideMenuCommandsAndPasswordEditorsHideEntry`
method, which the general runner reported as passing. This correlates the
system condition with every failed method; it does not establish which dropped
event caused each assertion or why the system entered that condition.

The editing-panel class now uses the existing emulator-restricted failure
artifact rule. It captures the screen and hierarchy before driver teardown;
clipboard restoration remains in `@After`. No production code changes.

On a fresh isolated ARM64 API 37 emulator with CI animation scales zero, a
temporary stress test performed 30 fresh composing-editor launches and
verified a real key press after each. It passed. All nine editing-panel methods
then passed, including the three that failed in the interrupted suite. That
run recorded zero untrusted-touch occlusion events and zero starting-reveal
timeouts. The temporary checkout, test APKs, test class, emulator and isolated
ADB server were removed. This isolated success does not explain the earlier
sequential failure, establish the full workflow shell, or verify hosted CI.

On a fresh isolated ARM64 API 26 emulator, the same nine-method class passed
without skips or failures. In a second temporary test APK, an intentional
assertion failure after typing in the composing field produced a valid PNG and
an XML hierarchy containing the editor before teardown. The induced failure is
a negative control, not a product test pass. An earlier API 26 setup stopped
before tests because `logcat -c` failed; the fresh retry omitted that step.
Both temporary checkouts, APKs, captures, emulators and isolated ADB servers
were removed. The original interrupted run's diagnostic logs remain available
for the unresolved starting-window investigation.
