# Warm reuse and watch lifecycle integration evidence

The final 15-test actual Android fixture passed on both local API26 and API37 AVDs. It uses real adapter/resolver/operation-lock/FileObserver code with synthetic files and an injected numeric runtime; it does not load real model weights or qualify model quality/performance.

Initial API26 failed two of twelve cases; initial API37 passed twelve. The separate deterministic old-watch control failed one test exactly as expected before the production watch fix was applied. The final fifteen include the original strict twelve assertions and three late-callback retirement/positive-current-event controls. All logs are preserved separately; no results are pooled or reclassified.

Runner: `io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner`, arguments `-w -r -e runeFailureArtifacts false -e class io.github.mesteriis.rune.keyboard.intelligence.inference.ActiveModelLifecycleInstrumentedTest`. The old-watch control selects only `#retiredWatchCallbacksAfterCloseCannotInvalidate` on that class. Each final AVD received the same recorded built APKs via successful install-r operations; hashes are build identities, not installed-APK readback attestations. No physical Fold run, remote CI, screenshot or hierarchy capture is represented.

The original failing kernel event mask was not recorded. The deterministic control establishes the permitted late-callback defect, and the corrected full suite passes; no particular historical inotify event is asserted. See the dated acceptance report for source references, review hashes and remaining release gates.
