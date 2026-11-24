# Q7: require editing-panel scenarios in the general Android report

The general Android CI report gate now requires all nine named
`EditingPanelInstrumentedTest` methods to pass. A sufficiently large report
with one of them absent or skipped can no longer satisfy this gate. This does
not change the test runner's scope, app code, or emulator behavior.

An independent requirement test first failed against the previous gate, which
did not require these methods. After adding them, the boundary-runner suite
passed 16 tests, including existing per-required-case missing and skipped
mutation controls; the Android shell suite passed three tests. The retained
older API 26 general report contains all nine methods, each passing. That
older report does not pass the current complete gate: twelve other required
methods added later are absent. It is therefore not evidence of a current full
suite pass. The newer isolated API 26/API 37 class runs are documented in
`2026-11-09-q7-editing-panel-occlusion.md`; full local and hosted CI remain open.
