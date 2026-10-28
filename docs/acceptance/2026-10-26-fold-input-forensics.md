# Fold input and Undo forensics

> Historical material from 2026-10-26. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

The owner explicitly requested another Rune window while Android MCP was blocked. Android MCP confirmed exclusive handoff with no active/pending phone controllers. The installed main APK was verified as the previously accepted `b348bb37f969032f79278686642756a8d2ee330a7482be437f6fb072c946bf31`.

## Input observer

Added `FoldAutocorrectionInstrumentedTest.repeatedRealTouchInputAndUndoKeepTheRequestedCharacters`. It exercises the existing two unresolved episodes using `спосибо `, `ты можешь позвоеить позже `, and the correct control `ты можешь позвонить позже `. The middle phrase intentionally retains its already-known automatic abstention; retaining it is not counted as a newly fixed typo.

The observer records requested tap coordinates and helper-call durations. Its stronger variant also attaches non-consuming listeners to the actual in-process Rune key views, collecting bounded DOWN/UP receiver labels, coordinates and timestamps. Listeners are detached in `finally`. Requested labels and both actual receiver sequences must agree before a phrase result can pass. This catches wrong-key delivery even if a later correction accidentally makes the final text match. It uses no editor payload reads or screenshots, and never changes diagnostic consent.

- First repetition run: 12 rounds × 3 phrases = 36 phrase executions, 12 exact Undo checks, 720 requested taps. Passed.
- Receiver-observed run: four rounds × 3 phrases = 12 phrase executions, four exact Undo checks. All 240 actual DOWN/UP pairs matched the requested letters and coordinates; every phrase and Undo check passed.
- Requested pauses alternate 50/100 ms. In the first run, the complete touch helper call itself measured p50 63 ms, p95 83 ms, maximum 104 ms, including foreground observation and synchronous injection. Thus those requested sleeps are not a claim of exact 50/100 ms onset cadence, isolated IME latency or a cold-start measurement.

The two original intermittent episodes did not recur in these 48 phrase executions and 16 Undo checks. Their causes are **not** declared fixed or explained. This is targeted reproduction of exposed examples, not independent spelling qualification or natural typing accuracy. No product model, threshold, dictionary protection or main APK was changed.

## Preference-restoration fault found during the window

The external state check found that the saved last-used-language preference differed from the fresh pre-window snapshot; all four personal stores were unchanged. Reconstructing only that key produced an exact match to the original complete semantic preference fingerprint, so no other setting was guessed.

An attempted fixture change unbound Rune before restoring preferences and added an in-process equality check. A temporary standalone lifecycle test and a three-phrase/one-Undo follow-up passed within instrumentation, but the language changed again after instrumentation exited. The external delayed check caught it. This attempt was reverted, including its temporary recovery test/entrypoint; its source and logs remain in ignored evidence. Those extra three phrase executions and 60 receiver pairs are retained as experimental observations, not added to the current observer's 48/16 acceptance counts.

After all test processes finished, Rune was unbound and stopped, the exactly reconstructed original preference map was restored while inactive, and Rune was relaunched/reselected. This did not clear application data or restore older personal-store contents. The remaining late-write cause requires further investigation; an in-process preference comparison alone is insufficient proof of final owner-state preservation.

## Validation and handling

- Current Android test APK: built successfully; `:app:lintDebug` passed.
- Both current-observer physical invocations: `OK (1 test)`, no failure/skip status; all declared editor-payload-read counters stayed zero.
- Raw native logs, failed state checks, rejected restoration attempt, bounded per-method journals and before/after fingerprints are private under ignored `build/fold-input-forensics-20261026/` (0700 parent, archives/XML 0600).
- This window changes test diagnostics only. The previously installed main APK remains the current Rune product build.

Final external verification after test-process recovery, application restart and a delayed recheck: the complete original preference fingerprint and four original personal-store fingerprints match, including the original last-used language. Rune remains selected; the installed main APK hash is unchanged. Three task-created cache snapshots were collected/validated and removed only by their exact generated names. Both coordinating chats were explicitly notified of release; no phone commands followed that release.
