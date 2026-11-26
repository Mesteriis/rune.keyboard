# Q7 API 37 theme test failure and targeted retries

The ongoing full API 37 general suite reported a failure in
`KeyboardThemesInstrumentedTest.liveThemeChangeKeepsEditorTextAndRebuildsAppearance`:
the synthetic field returned its empty-field hint while `hi` was expected. The
full test-runner log identifies line 79: the first assertion immediately after
typing, before changing a theme. The filtered TestRunner log SHA-256 is
`38af9b866b33dc67ad0e2df13cd2ebce26388348b21ce5423edf003223f2c315`.
The preceding test exercised every theme and palette, but causation and whether
the input connection was ready remain unproven. This is a failure of the full
run, regardless of the targeted retries below.

The same named method was run four times on a separate task-owned API 37 ARM64
AVD with the CI software-navigation option. All four direct instrumentation
runs reported the exact method start and success, one executed test, no skips and
`INSTRUMENTATION_CODE: -1`. The debug APK SHA-256 was
`de6f8a9e1e569be9cc7a7eabcdef9bdbc677f1ee3d3e254e51688cfa13d4a448` and the
test APK SHA-256 was
`affc8a4327ca76d9f25dcca8657247145df19baa01943327bdcb074e0cb42d24`.
The four retained local logs have SHA-256 values, in order:
`61e457186df60041010ad0a194b1a4fc9189aa36e27e0a5722853f0ac9c68b06`,
`ec72d5695589bbbb9056079d31cd23c6e4f8790209887c73c97528fe33b5f6d2`,
`a61146a0a0f974ddb75001005ac3ed651d9621c9b186dc77dbd7b8bb925029e5` and
`b12cec53bbd203aaaa376f827a094e057c9a1ce5c58df7bd2e08a51e0a4cb992`.

The retries establish only isolated success, not the cause of the full-suite
failure or full-suite stability. The retry AVD and its separate ADB server were
stopped and deleted; the original full suite continues on its own AVD. No
physical device was used. Q7 remains open.

A subsequent direct run on another disposable API 37 AVD executed the two
consecutive methods observed in the full run: first
`allFiveThemesCanBeSelectedAndTypedWith`, then
`liveThemeChangeKeepsEditorTextAndRebuildsAppearance`. Both exact methods
started and completed successfully, with no skips; instrumentation reported
`OK (2 tests)` and code `-1`. The log SHA-256 is
`3ea409a8cc5d578e0721925952a450fbb494d8aeb2eef154ab12f1c6b3804228`.
This single ordered-pair pass does not reproduce or explain the full-suite
failure and does not prove stability. The second retry AVD and its isolated ADB
server were stopped and deleted. The original full run remains failed.

The original CI-navigation general run has since finished. Its fresh JUnit XML
reports 353 tests: 304 passed, 48 skipped, one failed and zero errors. The sole
failure is the theme test above at line 79. The XML SHA-256 is
`294a171b1291ea737a94f3b0fed519b77e36c74a66c8b281178fb68f20a5cb4e`.
This is a failed full general run, even though the method and ordered pair
passed separately. The independently routed suites continue; their outcomes
must be assessed separately from this report.
