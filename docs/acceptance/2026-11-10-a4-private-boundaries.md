# A4: private-editor boundary fixture

A new explicitly opted-in physical Fold fixture exercises four public cases
through the real IME and a separate private QA editor: preserve `инн` before
period and colon, correct `смотруть` to `смотреть` before each boundary, and
restore the exact original by Backspace. Colon enters the symbols layer. Every
case asserts zero editor-content reads and exact before/after hashes of all six
personal-store roots, including diagnostic files. Personalization and numeric
quality collection are disabled for synthetic input and the driver's teardown
restores and checks the captured keyboard and secure IME settings. The test is
not an ordinary-editor or full device acceptance claim.

In a disposable API 37 arm64 emulator with separate ADB server and explicit
`runeBoundaryPrivateFixture=true`, the built debug app and test APK ran all four
methods with zero failures or skips. Instrumentation reported `OK (4 tests)`.
App APK SHA-256 was
`3502c81352f7ee346232ebb76c2336bef3b29268e464a81a8823cc934586f1b9`;
test APK SHA-256 was
`4c7ddc794ebc48260639ffd0c37dc086676826907a6601704a243f93a21bfc23`;
the synthetic instrumentation log SHA-256 was
`42fae4e11c0a4ff83bf1265f11dfbdc0c834a48c561d7a92e03ef4ebc4144e6f`.
Both APKs came from the same clean local clone plus the fixture and skip-list
changes. The Android suite planner's 23 focused tests passed. CI's general suite
lists these opt-in cases as expected skips; no hosted run is claimed.

The test did not run on Fold in this slice. Physical screen and ordinary-editor
acceptance, the independent natural control corpus and A4 as a whole remain
open. The disposable emulator, separate ADB server, temporary checkout, APKs
and raw synthetic logs were removed. The owner Fold and its data were untouched.

## Fold inner-screen run

At `724b9a49`, the exact emulator-tested instrumentation APK above was built in
an isolated checkout and installed as an update to the existing test package on
the owner Fold. The main Rune APK was not installed or uninstalled. The Fold
reported `OPENED` before and after the run; continuous hinge state was not
measured. The test package that preceded this run was restored afterwards and
its complete installed APK matched the saved bytes.

The first invocation reported four failures during setup: the QA activity did not
become visible, and none of the four typing assertions ran. The device's focused
window was the expanded notification shade. After collapsing that shade, the
colon correction/Undo case passed individually, then the remaining three cases
passed together: four physical successes total, zero skips. This supports the
private-editor paths on Fold; it does not establish ordinary-editor behavior,
all punctuation controls or independent quality qualification.

On the final comparison, all six personal-store roots, including both diagnostic
streams and numeric quality, matched their pre-retry file hashes. The four
captured secure IME settings matched. The debug diagnostics preference file
matched byte for byte. The keyboard preferences XML differed byte for byte,
but its parsed typed preference map matched the separately saved pre-retry XML
exactly. The first failed invocation's driver independently checked its saved
pre-invocation preference map on every teardown; no teardown mismatch was
reported. Its original XML bytes were not saved, so independent host comparison
of the original pre-first-invocation preference map is unavailable. No prior
values were guessed or overwritten. The notification shade was collapsed and
the QA driver returned to the home screen.

Synthetic log SHA-256 values, in order: initial failed run
`594bda86e2ee97a5d8d4db8468566a7ded113cecb43a0e221b273b8bfcfdbeb8`,
individual successful retry
`dba031d9765dcb99a1d758de6c85b0009f95fd8943952f0f082bdc9f20534f0c`,
and three successful remaining cases
`32529d636d81ee9c904e12c11a4532dae8e73f8236b920c5132f9cccca2ca87f`.
An initial host wrapper also used the shell's read-only `status` variable after
the single successful test; the native test result above was retrieved from
its actual instrumentation output rather than treating the wrapper as a pass.
The temporary clone, APKs and synthetic logs were removed. Two private pre-run
diagnostic backups and the pre-retry preference snapshot remain in ignored
owner-recovery directories; these are owner data, not disposable build output.
A4 still needs its ordinary-editor and independent-control acceptance.

## Ordinary editor and review phrase

The fixture now supports an explicitly requested ordinary QA editor in addition
to the unchanged default private mode. Synthetic learning and numeric metrics
remain disabled. Ordinary sessions honor the owner's existing debug diagnostics
settings, so their synthetic events can be recorded and rotate diagnostic files;
the fixture does not assert unchanged diagnostic bytes in this mode.

The four existing individual boundary cases passed without skips on a disposable
API 37 emulator and on the unfolded Fold. A fifth test then typed the exact
review phrase `живу в спб. смотруть.` in one ordinary editor session. On both
API 37 and Fold, `спб.` stayed unchanged, `смотруть.` became `смотреть.`, and
Backspace restored `смотруть` with the preceding context intact. All checks
used the real keyboard and confirmed six zero editor-content-read counters.
The existing four private cases also passed again on the emulator. The Fold was
`OPENED` before and after, not continuously observed. The five ordinary Fold
cases were run as a four-case invocation followed by a one-case invocation;
no all-five invocation is claimed. The 23 Android suite-planner tests passed.

The four-case Fold and emulator APK SHA-256 was
`ec6dfc7c97224b1b8d095d52a1ace51226b18abf2263dfa9fea195592f006300`;
the subsequent phrase-test APK SHA-256 was
`78043cc26ee35d0da5cc96196df0623103f13a6cb139325ff4a92ad3a8ed775a`.
The ordinary four-case emulator and Fold logs had SHA-256
`0f623d905cf782c3e3974eda2875f39b3d6f8c289249022bbdee4688c19d82ad` and
`998cef557995a637f96a65cc70b75cfd4cf782381ddbef3403d7d85cc1fb2bb0`;
the phrase-case emulator and Fold logs had SHA-256
`7e12e6e615e0f6267b689917de172d138033302ebc76de9cfae3dc911bc6cc82` and
`c854469cc46ed27834ec2cdca4be09c709a38953ed17a0945ce79dfc43914ce3`.
The raw synthetic logs were removed with the temporary builds.

Before each physical invocation, diagnostics and both preference XML files were
copied to a new private owner-recovery directory. After each, typed preference
maps and four secure IME settings matched; personal typing, touch, learning,
control and quality-store hashes matched. The diagnostic directory changed.
After the first invocation, one of eight original diagnostic files was no longer
present in full as a contiguous file in the phone's current diagnostic files;
after the second, two of the eight files captured immediately before it were no
longer present in full. Both pre-invocation versions remain in the private
backups. Presence was tested as exact contiguous content, so these counts do
not assert that every smaller fragment was lost. No owner logs were overwritten
with the backup, and the app's original test APK was restored byte-for-byte.
The main Rune APK was not reinstalled. ADB was used with an explicit device.

## Current-source category gate

The 140 disclosed authored controls were replayed twice each at all three
boundaries against the current product controller. Every replay exited zero and
was deterministic; the source-, asset- and input-bound gate passed. The table
is identical for space, period and colon:

| Category | Rows | Changed | Undo failures |
| --- | ---: | ---: | ---: |
| Abbreviations | 54 | 0 | 0 |
| Synthetic domain labels | 43 | 0 | 0 |
| List headings | 43 | 0 | 0 |

The compact [receipt](2026-11-10-a4-current-controls-evidence.json) retains the
source, asset and toolchain hashes, three original receipt hashes, projection
hashes, status and category counts without local paths. The controls are
previously disclosed authored examples; their frequency and independent natural
representativeness are not established. The raw task-owned replay outputs and
logs were removed. Physical boundary acceptance is now evidenced, but those
control-corpus limitations remain and no broader independent accuracy claim is
made.

## Guard for ordinary QA with diagnostics enabled

The physical runs above showed that a synthetic ordinary session can rotate the
owner's diagnostic files. The fixture now checks persisted debug-diagnostics
preferences before capturing stores, changing IME settings or opening the QA
field. If metadata or consented text collection is enabled, ordinary QA fails
unless `runeAllowDiagnosticRotation=true` is explicitly supplied. The flag is
an operator opt-in after a verified owner backup; the fixture cannot verify that
the backup actually exists. The check does not modify consent or preferences,
and cannot guarantee safety against a concurrent settings change after the
check. Private mode remains available without this flag. Existing diagnostic
backups from the Fold tests remain owner data and were not modified.

In a disposable API 37 emulator, separate real instrumentation attempts with
synthetically enabled metadata and consented text each failed at this guard
without the flag; the metadata attempt also confirmed the selected IME was
unchanged. With the flag, the ordinary correction/Undo case passed; with
recording disabled, it passed without the flag. A private correction/Undo case
also passed with metadata enabled and without the flag. The final test APK was
rechecked for both metadata refusal and explicit-opt-in success. A new permanent
instrumentation test passes all eight combinations of metadata, text and opt-in;
the Android suite-planner's 23 tests pass locally. No new Fold test or app
installation occurred in this slice.

The final test APK SHA-256 was
`cfadf7e572f848cdd936e6e342d41360381d1d500c2a4dec81c963ad5f381024`.
The negative, positive and permanent policy-test synthetic log hashes were
`433efce91f16298255bc3d311bb620bf52010404466a670cb40dc9923bea4ec7`,
`55b4ccc7376baf9a45ffe1a38cd65865b70ebc6ea715138b89fb92fd8f1fddcd` and
`ce23738fe0f82ee60af44d75ec3c6f16fc97fc1ec8912d5146e54c0e069be577`.
One initial host command used zsh's reserved `options` variable and generated
an invalid instrumentation command; it did not constitute a native test. The
corrected command and its actual native results are described above. The
task-owned emulator, separate ADB server, temporary APKs and logs were removed.

## Punctuation fixture on the refreshed CI candidate

The exact ordinary debug and instrumentation APKs from candidate
`123d0a52` ran five `FoldBoundaryPrivateInstrumentedTest` methods in each
of two editor modes on a fresh ARM64 API 37 emulator. Each mode matched
all five method identities and recorded five starts and five passes,
with no skips or failures. Both modes exercise ambiguous abbreviations,
a useful correction, exact Undo on period and colon, and a full review
phrase. The tests verify six zero content-read counters and unchanged
personal stores in each mode.

| Public synthetic editor mode | Passed | Instrumentation log SHA-256 |
| --- | ---: | --- |
| Private | 5 | `75853785ae3cd0b748c7a20496783d2a10489144f9a4a46daa49789012856d00` |
| Ordinary | 5 | `5897ed322b37b9e115050920f61de15d7aadcc543d791fe096c25e5809705ee8` |

The AVD, isolated ADB server and both APK copies were removed. The
five identities are opt-in and skipped by the general CI suite. Earlier
physical evidence is recorded above. Independent natural-control
qualification remains open.
