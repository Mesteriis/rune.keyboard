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

## Disposable emulator recheck — 2026-11-10

On an isolated Android API 37 emulator, Chrome 145.0.7632.218 and the debug
application built from `a4a4de3d` were exercised with the explicit emulator
opt-in in the test harness. Without that opt-in, both cases were skipped. A
first run failed both teardown assertions because an earlier owned tab used the
same fixture address. With a fresh fixture on a different port, both native
cases passed and the independent numeric DOM oracle passed (51 no-suggestions
and 62 ordinary records). The failed run is retained alongside the successful
logs under `build/ci-editing-investigation/q8-chrome-emulator`.

The emulator check does not expand the physical Fold or application matrix
acceptance described above. The emulator and its local fixture were stopped.

## Current Fold recheck

On the current Fold debug application and test APK built from `b48d73c2`,
both physical Chrome tests passed with no skips. The independent numeric DOM
gate passed with 62 ordinary and 51 no-suggestions records. The two fixture
tabs closed, the one owned ADB reverse mapping was removed and the host fixture
stopped. The device reported `CLOSED` after the run; that observation does not
establish a continuously measured fold state or cover inner/landscape modes.

Rune's keyboard and diagnostic preference values and selected IME matched
before and after. The rotating diagnostic streams displaced two original files;
their exact prior bytes were retained in a local owner-only, Git-ignored recovery
directory. Do not delete that backup as a build artifact: it contains owner
diagnostics. The remaining original diagnostic files were still present. No
raw test logs or page text were retained, and the temporary fixture was removed.
The full APP-001–005 matrix and independent qualification remain open.

## Fold Chrome address-bar follow-up

An opt-in instrumentation test opens its own loopback Chrome tab and uses Rune
touches to enter a synthetic `.invalid` address. On the Fold it observed the
complete address, verified that Backspace removed the last character, pressed
the displayed Go key and observed the address retained while that key was no
longer visible. This does not independently establish that the whole keyboard
was dismissed. The test does not independently observe an HTTP request or a page
load, and it does not establish fold/unfold or landscape behavior. The device
reported its closed state before the run.

The test APK built in a clean temporary checkout and the physical test passed.
The owner keyboard and diagnostic preference values, selected IME and original
diagnostic bytes were unchanged. The owned Chrome tab and ADB reverse were
removed, the fixture stopped, and the phone returned to its launcher. Temporary
build files were deleted. The earlier private diagnostic recovery backup remains
retained and is not a build artifact. The existing CI report parser's 23 host
tests passed with the new opt-in test added to the known-skip inventory; this is
not a hosted execution or completion of APP-002.

## Gmail availability

An attempted synthetic `mailto:` compose intent did not resolve to Gmail.
The installed Gmail package was disabled for Android user 0; no test draft was
created. The package and its settings were left unchanged. APP-003 remains
unverified on Fold.

## Fold inner-screen recheck — 2026-11-10

On the unfolded Fold, using the installed debug app and test APK built from
`b48d73c2`, the two Chrome textarea instrumentation tests passed. The separate
numeric DOM gate also passed: 62 ordinary and 51 no-suggestions records, with
all required ordered stages. The address-bar instrumentation test passed as
well, with the same observation limits described in the address-bar follow-up
above. The device reported `OPENED` before each test class and after the run;
continuous display-state sampling, fold transitions and landscape were not
measured. This is not full APP-002 acceptance.

The fixture server and its owned ADB reverse mapping were removed, and the
fixture's temporary files were deleted. The three original IME settings matched
before and after. Three rotated diagnostic files no longer present on the
device were retained byte-for-byte in a private, ignored recovery directory;
these owner records must not be deleted as build artifacts. The tests' own
teardown restores and checks the keyboard preference map. A separate host-side
comparison mistakenly read a nonexistent preference filename with error checking
disabled, so its reported equality provides no independent preference evidence;
no independent diagnostic-preference comparison was made in this run.

## API 37 emulator CI route

The emulator-smoke workflow schedules the Chrome textarea suite on its
disposable API 37 AVD. The runner verifies the AVD identity and installed
packages before using a loopback server or changing browser setup. It refuses
an existing Chrome flags file or debug-app configuration and removes its own
reverse mapping and temporary setup on exit. The gate requires both named
instrumentation cases to start and pass, plus the existing ordered numeric
DOM gate. Numeric instrumentation progress reports are separate from test
results.

The first local clean-Chrome attempt loaded both pages but failed before typing
because Chrome's own notification prompt obscured the editor. The
instrumentation now declines that prompt only during the owned-emulator path.
On the next fresh install of Chrome data, both native cases completed and
the corrected host parser accepted the actual captures. Chrome
`145.0.7632.218` emitted 62 ordinary and 51 no-suggestions records on the
ARM64 userdebug emulator. The ordinary stages verified five corrections, exact
Undo and the sixth correction. The no-suggestions stages verified five literal
words and Backspace. This covers the textarea suite. Hosted x86_64 execution
and the remainder of the Fold third-party application matrix are open.

The complete runner then repeated both passes after clearing the disposable
Chrome app data, returned exit 0 and wrote the verdict. ADB confirmed the
reverse mapping and temporary browser configuration were gone afterward.
All 50 Android CI helper tests, eight Chrome oracle tests, and actionlint
passed. The most recent published run remained 40680972358 at `2c1ff975`
with a failed conclusion.

### Complete physical fold and unfold on the merged main tree

A physical Samsung Fold ran the debug app built from merge commit
`c42e83da32ea41696a0e48ab8d1b5064d7a9cef0`. Instrumentation and the
owned loopback fixture came from `5b5f1758`. The disposable test
checkout widened the real posture waits and used the exact loopback
URL to identify the Chrome test page. An ADB-forwarded DevTools
connection focused the empty textarea before measurement. After the
first checkpoint the harness left the textarea untouched and sent one
hardware letter on the cover display.

Android reported real base postures `CLOSED` and `OPENED`, with
display widths of 1968 → 1080 → 1968. Chrome measured a collapsed
selection at every checkpoint. The focus and exact-text assertions
passed at all four checkpoints.

| DOM checkpoint | Observed offset |
| --- | ---: |
| Inner display after four corrected words and Space | 16 |
| Cover display before additional input | 16 |
| Cover display after one hardware letter | 17 |
| Inner display after unfolding | 17 |

The debug app and instrumentation APKs built successfully, all 13
host oracle tests passed, the native run returned `OK (1 test)`, and
the independent DOM verifier returned `passed: true`. The original
app and test APKs were restored and matched their pre-run hashes.
The four secure IME settings and both preference maps also matched.
The owned tab and temporary ADB mappings were removed.

This passes the physical Chrome textarea criterion for passive
caret continuity on the merged tree. A separate emulator diagnostic isolated an apparent caret shift to
the fixture's textarea refocus tap. Continued
soft-keyboard visibility and the broader third-party editor matrix
remain open.

| Evidence | SHA-256 |
| --- | --- |
| Main debug app APK | `29bc43ff5070ed290b6b93826899629bfaf42027c231a68aed241f288a336757` |
| Instrumentation APK | `1a29e4b0b7e983b7d108d2c32845936e356a9e5c5e617151d884272557d9a87c` |
| Native result | `c551c0a7c9eba18e8aac278843a4f2ca1b5f9dd4658ced52f6e23917035a958e` |
| Numeric DOM stream | `5cc8b6cbf943c3a52aeb74222a2061115b594dc203c95c7df418e4fed5ae6efd` |
| DOM verdict | `21cf47cdf003a407d4fa301cf6c14150c12e47adf25a99935f239bb738d3c09b` |
