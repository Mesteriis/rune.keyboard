# Number-row settings navigation review — 2026-09-06

Spec verdict: **PASS**. Code-quality verdict: **PASS**. No actionable issue found in the one-line test-only correction.

Reviewed the exact working diff in `app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/ImeTestDriver.kt:397`: adding `setSwipeDeadZonePercentage(0.375)` to the existing vertical `UiScrollable` search in `setNumberRowThroughSettings`. Current file SHA-256 is `5eff3d828681f2e87c0074cd87657000fc5d2b6d7738bef258dc110fcf9361bb`. The only implementation delta in this file is that added line.

The adjustment leaves 25% of the scrollable height between swipe endpoints, consistent with the retained physical trace changing a 2,016-pixel swipe into a 630-pixel swipe on the 2,520-pixel viewport. This gives the existing bounded search smaller steps. It does not add a retry, enlarge a timeout, change the target selector, change preference state directly, or substitute a different setting. The same resource-derived localized label is reacquired and clicked after scrolling (`ImeTestDriver.kt:391`), and the exact persisted preference check and next-input-view restoration remain unchanged (`:403`).

The affected test still enables the number row before the owned-token sessions and verifies actual numeric/hostname input without a layer change. It retains exact remote editor text, composing/commit counter checks, same-session positive mechanical cleanup, immediate Backspace restoration, connection/key identity and no-readback assertions (`MechanicalPunctuationInstrumentedTest.kt:73`). The navigation fix does not weaken that evidence.

Read `build/smart-typing-0.3/physical-final-20260906/number-row-investigation.md` and the relevant retained log outcomes. The original cover run was 26 PASS/1 navigation failure; the unchanged isolated case then passed, while the unchanged complete mechanical class reproduced the same navigation failure (4 PASS/1 FAIL). Those failures remain evidence and are not dismissed as a flake. The one-variable shorter-swipe class completed 5/5 PASS in 101.773 seconds. The now-completed affected-case logs also show API 26 1/1 PASS in 56.401 seconds and API 37 1/1 PASS in 56.755 seconds. These were root-owned executions; this reviewer did not run them.

This evidence supports the smaller navigation step as a scoped fixture correction. It does not prove the hypothesized asynchronous Settings rebuild or a particular framework event race, and it does not identify a production punctuation defect. The passing class duration is not comparable with the earlier prematurely failing class as a performance measurement. No additional repeat is requested by this source review; root owns completion of the already-running required gates.

Only read-only filesystem inspection and this report write were performed. No implementation edits, tests, builds, device, model, Gradle or network operations ran. Raw phone XML/screenshots were not opened.
