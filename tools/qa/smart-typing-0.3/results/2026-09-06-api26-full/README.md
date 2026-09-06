# API 26 full instrumentation — 2026-09-06

Current application suite at `27d07ea`: 131 tests, **128 passed**, three explicit
optional installed-model assumptions, zero failures/errors, 641.797 seconds.
The separate JNI contract class passed **6/6**, with no skips, in 0.058 seconds.
No full model was installed in this ordinary-CI emulator.

The fresh `rune_api26_20260906` AVD used the API 26 Google APIs arm64 image,
revision 3. `results.json` identifies all APKs and confirms their installed bytes
matched the local build artifacts. Compressed logs retain every result, including
the three named assumptions. Only status bundles with both class and test names
count as test outcomes; 1506 additional numeric status bundles are excluded.

This proves execution of the existing full suite on this source. Missing cases
in the consolidated editor/physical matrix remain open; passing test counts do
not add coverage for unimplemented scenarios.
