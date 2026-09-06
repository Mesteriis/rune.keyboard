# Diagnostics Task 2 device-test scoped re-review — 2026-09-06

Spec verdict: **PASS for the requested source fixes**. Quality verdict: **no remaining findings in this scoped re-review**. Both original P2 assertions and the exact-payload P3 are resolved, and the Activity recreation synchronization change addresses the recorded API 26 race without weakening consent assertions. This does not mark Task 2 device execution or broader diagnostics implementation/gates complete.

Reviewed only the frozen `TypingDiagnosticsInstrumentedTest.kt` at SHA `3fe38be44e4298c101e3bdb62ce432082864c20fa9a397f00c7726a08fc1c1c6` against the original review artifact and `task-diagnostics-task2-review-fixes.md`, plus narrow existing source/log context needed to check the assertions. The frozen hash agrees with its identity receipt; the live test file was byte-identical at review completion. No source edits, Gradle, devices, model calls or delegation. Original review, initial source and device failure evidence remain unchanged.

## Resolution of the original findings

**P2 metadata values — resolved.** All METADATA snapshots now pass through the validator automatically, including the metadata-only phase and sensitive/delete comparisons. Explicit positive checks require at least one row; off/deleted snapshots may be empty. Each nonempty row must have the exact eight fields, schema integer 1, actual String values matching the fixed kind/reason enum names, actual Int/Long values within the documented session/revision/count/index bounds, and a real Boolean modelUsed. Numeric-string, arbitrary-string, floating-point, null and incorrectly typed values cannot pass through a coercive getter. The metadata-only phase also checks its disabled public canary is absent. The test therefore closes the specific arbitrary-values-with-valid-keys bypass identified in the first review.

**P2 text-only provider/IME path — resolved.** After real two-dialog text consent, metadata is asserted off and its snapshot empty. The test launches a fresh actual editor, types `textonlycanary` using Rune keys, requires it in TEXT, refuses the pre-consent canary, and requires METADATA still empty with preferences text=true/metadata=false and zero editor payload reads. It then continues through both-on capture and text-off/metadata-on growth. This exercises actual integration independence instead of relying only on preference values or the pure recorder unit test. The preserved provider source is a singleton and the real service attaches `TypingDiagnosticsProvider.create(this)`, consistent with observing that same recorder; this is a dependency trace, not a new provider audit.

**P3 exact candidate/correction/Undo records — resolved.** The candidates assertion now requires original `helllo`, count one and exactly one array element equal to `hello`. The model automatic boundary requires original `helllo`, `input=" "`, `result=" hello "`, modelUsed=true and selectedIndex=0. Undo requires ACCEPTED, restored original `helllo`, `result=" helllo"` and context `a helllo`. EDITOR_ACCEPTED records are required for contexts `a hello ` and `a helllo`. The leading spaces match actual composing segments: the owned replacement/Undo region starts at offset 1 after `a`, while the restored full context includes that `a`. The existing actual editor text/span checks (7,8 after correction; 1,8 after Undo) and zero-read counters remain intact. No threshold, model response, input or expected editor behavior was weakened to satisfy the recorder.

## Recreation synchronization

The lifecycle callback is installed on main before `recreate()`. It only releases the latch for a SettingsActivity instance different from the captured prior Activity at RESUMED, so the old Activity cannot satisfy the wait. Lookup/recreation failures are caught on main and rethrown on the instrumentation thread. The test waits at most ten seconds for that replacement event and separately up to the existing five-second UiAutomator limit for `settings_scroll`; only then does it settle and check text remains off, no positive dialog exists, and the text toggle is available. `row()` also waits for the scroll root before attempting its scroll lookup. This is state synchronization, not a larger fixed sleep or an exception suppression.

The callback is removed in a finally block after success, captured main failure, resume timeout or root timeout. Waiting occurs on the test thread so it does not prevent recreation. These are bounded waits while the main looper responds, not a watchdog against an unresponsive instrumentation main-thread call. The existing precondition/cleanup ownership and synthetic-recorder deletion remain unchanged.

## Recorded evidence and remaining execution

The preserved API 26 initial log records `UiObjectNotFoundException` for `settings_scroll` in the recreation case, with 6 tests and 1 failure. The new synchronization is directed at that failure; the old outcome is not relabeled or replaced.

`root-task2-gates-first.log` records completion of `:app:compileDebugAndroidTestKotlin` and subsequent Android-test tasks. The same command later fails at `:app:lintDebug` with 145 reported errors, so this review describes Kotlin compilation only and does not report a successful overall build or lint gate. No revised device test result was supplied or generated for this re-review. Root must still execute the revised cases on API 26/API 37 against their matching APK/source receipt. Task 1 findings and source/packaging gate changes in the author's memo are expressly outside this re-review verdict.

## SHA-256 bindings

| Artifact | SHA-256 |
| --- | --- |
| Frozen/live revised device test | `3fe38be44e4298c101e3bdb62ce432082864c20fa9a397f00c7726a08fc1c1c6` |
| Frozen `identity.json` | `a5fb25acc4d5cea2f7bc2e23182c077e734e1a1bc7f232b36d35821ce41b5b8d` |
| Fix memo | `3172c24b968f8ecf679f991430b7055ae1cd875178b6f61b0aad4acdfaa0a4ce` |
| Initial `task-diagnostics-device-diff.txt` | `2681e777bc7f38b0086b687b41d1e123dbaacb46bd8264e67b66d632de0cdf80` |
| `root-task2-gates-first.log` | `25629d4a921407e79f65a74da35eaa38029b448270d4f07547502bee66378dd7` |
| Preserved initial `api26-initial.log` | `6c7bf3490301b1aa3438398cf6e92bd762c2828ea14724db0093a70a004941f3` |
