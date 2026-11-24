# API 26 editor boundary failure: observed system overlay

During the full local API 26 ARM64 CI shell repeat, the general suite reported
`distinctEditorResetsManualShiftAndSymbolsThroughBinder` failed. At the time of
this receipt the suite is still running; this is not a full-suite result.

The retained emulator log shows the test tried to focus the plain field after
using the symbols layer. It waited for the Rune Delete accessibility node,
rebound the IME after that wait failed, then timed out waiting for `qa_scroll`
in `resumeQa`. The failure screenshot shows the QA activity and Rune keyboard
behind an Android spelling-suggestion menu on the seeded `leftright` text. The
captured accessibility tree exposes the system menu's Add to dictionary and
Delete entries and system navigation, but not the QA root or Rune keys. Thus the
observed overlay explains why those selectors were absent from that capture;
the reason the menu opened and whether it accounts for the initial keyboard
wait remain unproven. No application crash was established by this capture.

The raw emulator-only screenshot, hierarchy and log are retained under ignored
`build/q7-api26-editor-failure-20261029/`; they contain test-fixture text. A
separate reproduction after the current suite ends is needed before changing
the test driver or attributing this to the product. The previously reported
successful local API 37 run does not make the API 26 failure a pass.

A separate fresh API 26 ARM64 AVD with the same 320x640/160 dpi/2 GiB
configuration and software navigation ran the already-built debug APK and test
APK. The failed test passed in isolation (one test), then the full adjacent
`EditorActionInstrumentedTest` and `EditorBoundaryInstrumentedTest` classes
passed in the observed order (seven tests in 296 seconds), including the same
final editor-boundary test. Both instrumentation results reported `OK`; logs
SHA-256 are respectively
`f5922381ecdfc7927a9edab6ec09e2cb92fc803f7149eb86fa15c08fb2101d51` and
`ca5795f5141e1bfa531e558f90cfc8ce468bfed9fe0fae52443ca636f437e6a6`.
The separate AVD was deleted after the checks. These passing repeats do not
explain the earlier system menu or turn the still-running full-suite failure
into a pass. No test driver or production code was changed.
