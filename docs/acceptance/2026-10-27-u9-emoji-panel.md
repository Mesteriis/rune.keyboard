# U9 — native emoji panel and isolated insertion (partial)

Symbols and Symbols Alt now expose Emoji in allowed editors. Letters retain their
existing default bottom row; the optional letters-row setting is still pending.
The reducer refuses entry in sensitive, raw-key, number, phone and date/time
editors. Symbols add a 0.9-unit entry, reducing Space from 5.65 to 4.75 while the
row remains ten units. The native panel uses three row heights for categories and
GridView, plus a fourth for ABC/Delete/Space/Enter. Candidate-strip visibility
retains the existing typing policy, so the four-row check excludes that strip.

GridView/BaseAdapter recycles TextViews with localized CLDR names. A horizontal
native strip selects categories; Paint.hasGlyph is checked lazily and cached for
visited entries. Catalog loading happens on first panel creation/opening, without
network work. These structural properties do not prove the opening/startup budget.
Recents are view-local RAM only, at most 32 unique sequences, added only after an
accepted commit. Incognito hides recents and never adds to them. No persisted
recents option was added. Skin-tone selection remains a separate stage.

Insertion uses CommitText, finishes owned composing without correction or word
learning, and clears ranking/revision context. A native regression exposed a
missing boundary proof: after that clear, the next `teh` had a candidate but Space
kept it literal. The final controller records only the numeric caret after the
accepted palette delimiter. Direct ABC return preserves this proof; external
cursor changes, invalidation, session end and deletion outside owned context
revoke it. Unknown external-word fencing remains in force. No synthetic whitespace
or earlier text is inserted into model context. The preview now uses the same
grapheme-boundary helper for its local Backspace.

Final validation:

- 1,246 JVM tests, zero failures/errors/skips, including policy/weights, exact
  commit, isolated context, finish refusal, external fencing, next-word correction
  and revocation of the numeric boundary proof.
- Fifteen source/generator tests, imeIntelligenceBoundary, privacyGateRelease,
  lintDebug, assembleDebug and assembleDebugAndroidTest pass; combined exit zero.
- Twenty-three native scenarios pass on one isolated API 36 arm64 emulator:
  three emoji cases, eight public editing cases and twelve existing
  WebView/Compose/preview/editor-boundary cases. Compose uses the separately
  source-bound fixture, with runeComposeQa=true and no skips. The installed Rune
  APK SHA matches the final local debug APK.
- Emoji cases prove literal `teh😀`, subsequent `teh → the` at Space, accepted
  recents with a localized name, native named/selected category actions, named
  TextView cell click actions, unchanged four-row content height, ZWJ `👩‍💻` and
  flag `🇪🇸` insertion and one-Backspace deletion, and hidden incognito recents.
  All six payload-read counters stay zero before deletion; ordinary grapheme
  deletion may use the existing bounded non-sensitive editor read.
- Fresh ordinary replay: all 12,000 rows exactly match the previous projection
  after excluding only hostStageNanos and fullTokenGenerationNanos. All 88 source,
  18 scoring-asset and driver bindings are checked. EN calibration volume and EN
  holdout precision/volume gates remain failed; ES holdout retains one aggregate
  false change/1,000 controls. No renewed full quality qualification is claimed.

Development failures are retained separately, not counted as passes: the first
native run had two failures (missing next-word correction and empty-field hint
comparison); waiting for a candidate did not repair the real correction failure.
The second native run still failed that correction case. A sentinel prefix fixed
the empty-field assertion, and numeric delimiter ownership fixed the product bug.
Two early revocation-unit runs omitted actual ordered editor acknowledgements;
the corrected fixture acknowledges them and verifies fresh candidate ownership
before asserting refusal. The final native/JVM results above follow those changes.

U9 remains open: optional letters-row key/settings, opening/cold-start/PSS budgets,
old API 26 font and glyph cases, modifier insertion coverage, physical Fold on
both displays and manual TalkBack traversal. Named native actions alone do not
prove a complete TalkBack review. The task-owned emulator was stopped/deleted;
there was no phone action or update. The full owner review remains open.

## Private-field complex emoji deletion gap

The real-IME emoji fixture now supports an explicitly opted-in physical Fold
using a `NO_PERSONALIZED_LEARNING` QA editor, disables learning and metrics,
and compares diagnostic and other personal-store contents. Recents remain an
ordinary-editor-only assertion. A new private-editor case checks that the
panel keeps its height, hides recents, inserts a literal emoji and performs no
editor payload reads. It is required by identity in the Android CI general
report gate; 23 host gate tests passed.

An API 37 ARM64 disposable emulator ran four private cases. Two passed: the
private palette/height case and the existing incognito-recents case. Two failed:
one Backspace after `👩‍💻` left `👩‍`, and one Backspace after `👍🏽` left `👍`.
The private editor intentionally forbids editor text reads, and the current
executor uses code-point deletion for that policy. No conclusion is drawn
about the later flag or second modifier assertions, which those failures
prevented from running. A separate ordinary-editor suite passed all five cases,
including ZWJ, flag and modifier deletion. This is a real uncovered U9/U3
compatibility gap, not a passing private deletion test. A fix must preserve the
no-editor-read boundary and safely handle selection and ownership changes.

The modified debug app and test APKs built offline in a temporary clone with
the pinned runtime submodule; the emulator, isolated ADB server and build clone
were removed. The physical Fold fixture has not been run, and a future host
must back up and verify owner diagnostic files even for private tests. No
production deletion policy or app APK was changed. Hosted CI, Fold, manual
TalkBack and full U9 acceptance remain open.

## Private-field owned emoji deletion fix

Source `35459b2a` keeps a single eligible emoji-panel insertion as an owned
composing span in NPL fields. Backspace may replace that span with empty text
only after its exact selection/composition callback is acknowledged; it never
creates a composing region over existing editor text. An unacknowledged delete
is refused, and the owned span is finished before subsequent typing, input
finish or invalidation. External-selection handling, rejected editor calls and
session termination discard or finish ownership. The mechanism keeps numeric
positions only and does not read editor text. It relies on the editor honoring
the Android composing protocol; it does not infer or repair arbitrary foreign
text, and code-point fallback outside Rune's own span is unchanged.

On a temporary clean-source-derived build, all 1,407 JVM tests passed, including
new tests for acknowledgement, moved cursor, refusal, an editor that silently
drops composition, lifecycle finish and old segmentation. The final production
source passed debug lint and both 2,160- and 12,000-row frozen replay profiles
against their baselines. The release/profile privacy gates, IME-intelligence
boundary and dependency gate passed on a clean checkout of `35459b2a`. Earlier
release gate attempts first rejected dirty source and then an unregistered
submodule; the successful run used the registered pinned submodule. The Android
report gate's 23 host tests passed; the new private emoji deletion method is a
required CI case.

On disposable ARM64 API 26 and API 37 emulators, each five-case private suite
passed with zero skips: ZWJ, flag and modifier insertion/deletion, continued
input, panel height and recents privacy. Payload-read counters were checked
after private deletions. An earlier API 26 run failed on the newer
`🧑🏽‍💻` sequence because old ICU segmented it; the final code treats one
palette action as one owned insertion and the subsequent API 26 run passed.
A six-case ordinary API 37 suite and the separately required CI case passed on
the preceding candidate, before that private-only ICU adjustment. Hosted CI
was not run.

The exact debug APK built from `35459b2a`, SHA-256
`4bfa47e97c4085fe635d859835393631fc1060b60ca77fa05b4edef17a84610a`,
was installed as an update on the physical Fold. All five private scenarios
passed with no skips. Host snapshots confirmed the four IME settings, shared
preferences, personal and diagnostic stores, and model-directory identity
matched before and after. The original test APK was restored and verified;
the updated app APK remains installed. The per-run recovery copy was removed
after successful verification; the older owner recovery archive with a
previously displaced journal remains intact. The device reported `OPENED`
afterwards. The temporary source/build clone and disposable emulators were
removed. Cover screen, manual TalkBack, nonconforming editors and complete U9
acceptance remain open.

## External editor changes after private emoji insertion

Three new real-IME QA editor cases exercise the private owned emoji composition
followed by an editor-side rewrite, a cursor move to the start, or removal of
the composing span. They assert the exact resulting synthetic text and
continued input, and verify zero before/after/selected/extracted/surrounding/
snapshot payload reads. The editor explicitly reports these changes; these
cases do not simulate a silent mutation with no callback or arbitrary third-party
editor behavior.

All three cases passed without skips on disposable ARM64 API 26 and API 37
emulators with the private fixture, and again on API 37 with the ordinary CI
fixture transitioning to a private field. Their identities are required by the
Android general-report gate; its 23 host tests passed. The debug app and test
APKs were built offline in a temporary clone. The test APK SHA-256 was
`2ca0ff11fca82030f4e047a3dff48cba7c7ca841860b3ca69d760cf9e942c33d`.

All three cases also passed on the physical Fold using the installed app APK
whose SHA-256 matched the earlier `35459b2a` validation. The temporary test
APK was replaced by the exact saved original after the run. Before/after host
checks matched the four IME system settings, shared preferences and all six
personal/diagnostic store roots by file content; the installed app remained
unchanged. The per-run recovery copy was deleted only after those checks, while
the older owner archive containing the previously displaced journal remains
intact. The device reported `OPENED` afterwards. The temporary build clone and
emulators were removed. Hosted CI, silent or nonconforming editor behavior,
cover screen and manual TalkBack remain open.

## Private WebView emoji deletion

An offline WebView QA field explicitly requests `NO_PERSONALIZED_LEARNING`.
The new real-IME test verifies the flag on the active editor, inserts and
removes a ZWJ emoji and a flag, then inserts an emoji followed by a letter.
It checks exact fixed synthetic text through the QA accessibility surface and
checks all six Rune editor-payload-read counters remain zero. The test is
required by identity in the Android general-report gate; its 23 host checks
passed. The prior version of the test passed on disposable ARM64 API 26 and
API 37 emulators. After adding the editor-flag assertion and diagnostic queue
fences, the final test passed on API 37 both with the private fixture and with
the default CI fixture. API 26 was not rerun after those test-only additions.

The first Fold attempt completed the test body but failed its teardown store
comparison: two diagnostic files had appended records and an internal
`WebViewChromiumPrefs.xml` file changed. Both diagnostic files preserved their
entire previous content as a prefix. The appended rows were two `SESSION/START`
records in each stream; the examined text fields were empty. No cause for the
new session records is established. The prior test APK and four system IME
settings were restored, and a private pre-run owner archive was retained; the
WebView preferences were not overwritten. The test fixture now fences the
recorder before and after the private test's store comparison, but the initial
failure cannot be retroactively converted into a pass.

The revised test passed on Fold against the installed app APK previously bound
to `35459b2a`; the test APK SHA-256 was
`7c05fdac0dc422ff8683fc19b4cbf1aec8a066cc883ac3be3ac105b44e234675`.
The original test APK was restored and verified. Host checks matched four IME
settings, shared preferences and the six personal/diagnostic store roots by
file content, and the app APK was unchanged. The repeat's temporary backup was
removed after verification; the first attempt's private recovery archive and
the older owner archive remain. The device reported `OPENED` afterwards. The
temporary build clone and emulators were removed. This is an offline QA WebView,
not third-party application coverage; hosted CI, cover display and manual
TalkBack remain open.

## Private Compose emoji deletion

The separately built Compose QA app now accepts an explicit private-input extra
and sets `NO_PERSONALIZED_LEARNING` on its input connection. The new real-IME
case verifies the flag, inserts and deletes a ZWJ emoji and a flag, then inserts
an emoji followed by a letter, with all six editor-payload-read counters zero.
It uses the Android emoji grid's `performItemClick` for the fixed public items;
this checks the real grid dispatch and Compose InputConnection, not a physical
tap or TalkBack. Two initial API 26 attempts could not locate the scrolled
accessibility cell; the test was changed to explicit grid-item dispatch before
the successful runs. The independent debug Compose APK and Rune debug/test
APKs built offline, and Compose QA `lintDebug` passed.

The targeted case passed on disposable ARM64 API 26 and API 37 emulators. The
four-case Compose suite passed on API 37 before the later physical-only guard
was added, and the final test APK's targeted case passed again on API 37. The
Compose-specific CI suite now requires all four named cases, while its general
suite explicitly inventories the new case's expected no-fixture skip. The
Android report gate's 23 host tests passed. Hosted CI was not run.

On Fold, only this private case can opt in; the clipboard-using Compose cases
remain emulator-only. The first physical run's test body completed but its
store check failed: two diagnostic files appended session/configuration events.
All previous diagnostic bytes remained as prefixes, and the inspected text
fields of the appended records were empty. The prior app/test packages and four
IME settings were restored, the temporary Compose QA package was removed, and
an owner recovery archive was retained. The cause of those setup-time records
was not established. After fencing diagnostics, avoiding a redundant Compose
launch and comparing the test body separately, the repeat passed on Fold. Host
checks matched the four system IME settings, shared preferences and all six
personal/diagnostic store roots by file content; the Rune app APK was unchanged,
the exact prior test APK was restored, and the temporary Compose QA package was
removed. The repeat backup was removed after verification; the first attempt's
owner archive remains intact. The device reported `OPENED` afterwards.

The final test APK SHA-256 was
`fa278bfe929580b224a8387cc6b8dfcd963e854af0107718b9e71741f07019c8`;
the independent Compose QA APK SHA-256 was
`55832a66d85c1d07a5b328f123c620c56930cfabe8af7c676542ee2a23946d94`.
Temporary build clones and emulators were removed. This is one independent QA
Compose editor, not a general claim about third-party apps, silent editor
changes, other Fold displays, physical emoji-tile touch or manual TalkBack.
