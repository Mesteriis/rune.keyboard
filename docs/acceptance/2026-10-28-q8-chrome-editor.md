# Q8: actual Chrome editor continuation on Fold

Two physical instrumentation tests now drive Rune in the installed Chrome, using
separate loopback-only public HTML pages. The normal page enables autocomplete;
the negative control disables it. Chrome actually supplies different suggestion
flags for these pages. The test records EditorInfo flag numbers and Rune session
availability on the IME main thread, without reading external payload through
InputConnection. Personal learning/feedback settings are temporarily disabled;
the complete original keyboard preference map is restored afterward.

## Measured outcomes

- Normal textarea: all five `teh ` inputs become `the `; exact Backspace Undo
  restores only the fifth original word; following Space and another `teh ` still
  produce the expected sixth corrected word, preserving the rejected fifth word.
- No-suggestions textarea: all five inputs remain literal; Backspace removes only
  the final separator. Rune's session stays enabled while the editor's suggestion
  restriction is respected.
- The native run passes both tests with no skips. An independent numeric DOM gate
  passes three ordered normal stages and two ordered negative-control stages,
  from 113 bounded records. These two proofs are required together.

Chrome can stop exposing the focused HTML editor in its accessibility tree even
while the IME connection remains active. The original field-resource assertions
therefore could not establish the final document. The final fixture performs
exact known-string comparisons inside its own page, exporting only integer
length/word/correction counts and boolean comparison flags to a loopback server.
No field text reaches that server. The host gate refuses missing/out-of-order
stages, wrong counts, unexpected fields, strings, booleans used as counters,
failed/skipped native runs or native success without DOM proof. The server
refuses other routes, arbitrary payload and unbounded receipts. No production
networking permission or runtime code is added.

## Failures and corrections to the test

The first trial used the WebView aria-description selector; Chrome instead
exposes the HTML resource ID. The next trial incorrectly expected correction in
an `autocomplete=off` field. Per-word observations proved five intact literal
words, a live Rune session and `suggestions_allowed=false`; this was correct
product behavior. Later resource-based trials exposed the accessibility gap;
a bounded refresh still lost the DOM field, so the measurement method changed
to the independent in-page oracle. The failed logs and receipts are retained
locally. They are not counted as product acceptance passes.

Closing a tab also leaves stale DOM accessibility nodes. Cleanup is verified
against the browser toolbar's exact owned loopback address, not absence of the
old page header. The final native assertions confirm both tabs closed. The server
is stopped, its single ADB reverse mapping is removed, and both coordinating
chats were told the Fold is free.

## Preservation and validation

Original preference values, protected existing data and model-file hashes match
after teardown. The system reordered otherwise identical enabled-IME subtype
sets; their original exact order was restored and all three IME settings then
matched. Diagnostic consent is unchanged. The enabled rotating diagnostic
streams advanced during synthetic input: current files are **not** claimed
byte-identical. Their complete before/after archives and rollback APK are private,
ignored and access-restricted; all original diagnostic bytes remain recoverable
from the pre-run archive.

All 1,355 app JVM tests pass; debug/test APK compilation, debug lint and the
architecture boundary pass. Eight oracle/server regression tests pass on Python
3.12 and 3.14, including omission, ordering, invalid-payload and receipt-bound
mutations. The seven existing inventory-runner tests and inventory check pass.
The oracle tests are wired into the stdlib CI job, and the workflow parses.
Hosted CI was not run. Production Android sources/configuration and the installed
app APK are unchanged from the prior accepted callback-calibration build; only
the test APK was updated for this slice.

Reproduction and the mandatory two-part verification command are documented in
`tools/qa/chrome-editor/README.md`. Exact source/APK/log hashes, browser identity,
public numeric outcomes and preservation receipts are in the adjacent evidence.

## Scope still open

This is partial APP-002 acceptance for an ordinary/no-suggestions HTML textarea
in the existing display configuration. It does not establish cover + inner +
landscape, fold/unfold, or the omnibox GO/backspace scenario. Telegram, Gmail and
Termux were present but were not driven in this slice; Samsung Notes was absent.
Q8 and the full APP-001…005 matrix remain in progress.

## Later package update — Q2 source/NOTICE slice

The Q2 update receipt records the exact new Fold APK and a fresh two-case native +
113-record DOM pass. With Rune originally disabled, one initial post-install
second-test setup refused IME selection before typing; the failure is retained.
The whole class passed on controlled repeat without reinstalling or changing the
fixture. Activation reliability is not claimed fixed, and full Q8 remains open.
See [the Q2 integration receipt](2026-10-28-q2-source-cascade-notices.md).
