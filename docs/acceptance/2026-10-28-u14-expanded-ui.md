# U14: expanded strip UI, emulator acceptance

When the current coordinator permits spelling suggestions and a validated hidden
candidate exists, a separately labelled 48 dp button appears beside the three
existing strip cells. It opens the current hidden snapshot in a touchable row
below the strip, over the keys. The keyboard's height and key instances do not
change. A second press closes the row. The control exposes button semantics and
localized show/hide accessibility labels; hidden candidates retain their
correction descriptions. Updating the strip dismisses the row and revokes the
snapshot. An explicit hidden choice goes through the coordinator and guarded
controller transaction; neither Space nor automatic admission selects a hidden
candidate. The coordinator checks owner policy, language, epoch, and the
single-use session/revision-bound snapshot again at selection time.

The final debug and instrumentation APKs build successfully. All 1,358 JVM
tests pass without skips, `lintDebug` and the scoring-boundary verifier pass.
On each of the API 26 and API 37 emulators, 17 instrumentation tests passed:
16 strip/view tests and one actual Rune IME test selecting a hidden candidate in
the isolated QA editor. The strip test verifies open/close, accessibility label
and 48 dp control, first-three labels, unchanged keyboard height and key objects,
and cancellation when an in-flight popup touch is followed by a strip update.
These are accessibility-node checks, not a manual TalkBack session.

For each manual-expansion setting, two current-controller replays of the 12,000
regression rows matched one another and their corresponding prior baseline on
all projected fields, including visible candidates, Space and Undo. These are
controller replays, not popup interaction measurements. The adjacent receipt
binds source and APK hashes, tests and replay receipt hashes; the raw replay
outputs remain in ignored build directories.

An earlier combined build/lint run failed on two `SuspiciousIndentation`
findings while a source file was being edited concurrently. The final run on
stable source passed lint; the failed invocation remains disclosed. No Fold
installation, Fold layout test or manual TalkBack test was performed in this
slice. U14 remains open until the Fold display and remaining accessibility
acceptance are completed.

## Fold candidate-view follow-up — 2026-11-10

On the connected Fold, the installed app and test packages ran two existing
`CandidateStripInstrumentedTest` methods individually using explicit-device
ADB. `originalUndoAndCorrectionKeepTheirOrderAndUndoAction` and
`expandedCandidatesStayOverKeysAndCancelHeldTouchOnRefresh` each reported
`OK (1 test)`. The latter exercises a synthetic keyboard view in an Activity:
opening and closing the expanded row, selecting a candidate, retaining the
underlying keys and rejecting a held touch after refresh. The reported physical
screen size before the run was 1968×2184; the device state after it was
`OPENED`. The posture was not monitored continuously. This is view-level
physical evidence, not a real-IME typing, complete Fold layout or manual
TalkBack acceptance.

Before the run, the owner diagnostic directory and shared preferences were
copied to a private temporary tar, and four system IME settings were captured.
The tar bytes and each system setting matched after both tests. The temporary
backup was removed after the comparison; other personal stores were not
inspected. Neither package was installed or updated. Installed app SHA-256 was
`7c8b13f2bec0b5e9ac23cb0dd0a4ab44f3edcfd6e6de4dcbde0a5dd14faf222a`
and test package SHA-256 was
`c78808f9b6c19b7309e689dc6edbb05467e0df30c9fdfb16a8400113e2578038`.
Their exact source build identities were not independently established in this
run. No hosted CI was run; U14 remains open for its real-IME Fold layout and
manual accessibility requirements.

## Real-IME physical fixture preparation — 2026-11-10

The existing three real-IME expanded-candidate scenarios now permit a physical
Fold only with both `allowPhysicalDevice=true` and
`runeFailureArtifacts=false`; they still run normally on owned emulators. The
fixture snapshots the non-diagnostic personal stores, disables learning,
example collection, touch adaptation, metrics and app profiles during
synthetic typing, and checks those stores before driver teardown. The driver
restores the pre-test preferences and device IME settings. The separate host
must preserve diagnostic files because they can rotate during a real IME run;
this fixture does not assert their preservation.

After an initial compilation failure from a missing `Context` import, the
corrected debug app and test APKs built offline in a temporary clone with the
pinned runtime submodule. An isolated disposable API 37 ARM64 emulator ran all
three real-IME tests with zero failures: select an English hidden candidate,
select the Russian `метро` candidate, and type outside the expanded row without
selecting a stale candidate. The emulator and its separate ADB server were
removed. The physical fixture itself has not yet been run on Fold and the
explicit physical guard has not been separately exercised there; this is not a
physical layout or TalkBack acceptance. Hosted CI was not run.

## Fold real-IME expanded candidates — 2026-11-10

On the physical Fold, the three `ExpandedCandidatesInstrumentedTest` methods
passed with zero skips: explicit selection of a hidden English candidate,
selection of Russian `метро`, and typing outside the expanded row without
selecting a stale candidate. The explicitly opted-in test APK was built in an
offline temporary clone from source `49f778ee` with the pinned runtime
submodule; its SHA-256 was
`743c29d3c2266359eeff31364f966cd84d2cc4a35ff347304fa017fe67ed9277`.
It was installed as a test-package update only; after the suite the previous
test APK was reinstalled and its bytes matched the pre-run copy. The main app
APK was not updated, and its exact source build identity was not independently
verified. The device reported `OPENED` and 1968×2184 after the run; posture was
not continuously recorded. The scenarios use a synthetic QA editor, not a
third-party app, and do not establish manual TalkBack or cover-screen layout.

Before any package change, the host privately saved the four IME system
settings, prior test APK, shared preferences and six personal/diagnostic store
roots. After the tests, each of the four system settings matched; shared
preferences and non-diagnostic personal stores matched by file content. Five
diagnostic files changed. Among eight original diagnostic files, three were
unchanged, one was preserved as a prefix of its current file, three were found
in another current file, and one was not found as a contiguous byte sequence
in the current journals. The complete pre-run owner archive, settings snapshot,
original test APK and test log remain in a private ignored recovery directory;
they are owner data, not disposable build output. No current diagnostic file
was overwritten. The temporary source/build clone was removed. Hosted CI and
manual accessibility remain open.

## Private physical fixture and diagnostic retention

The physical fixture now opens the existing `NO_PERSONALIZED_LEARNING` QA
editor from setup onward and includes diagnostics in its before/after
personal-store comparison. It does not change the owner's diagnostic consent
or switch preferences. The two English expanded-candidate scenarios also run
in this private fixture on an emulator when explicitly requested. The Russian
`метро` expanded-order assertion remains an ordinary-editor test: one private
run did not find the expected item in the expanded row, so that test is
explicitly skipped in the private fixture. The preceding physical ordinary
run remains the evidence for that scenario; the private result is not treated
as a pass for it.

On a disposable API 37 emulator, both private English cases and all three
ordinary cases passed individually or as their respective suite. A separate
real-IME regression enabled both diagnostic streams, opened a private editor,
selected an expanded candidate and checked that both streams and personal
stores stayed unchanged through that operation; it passed. This regression is
now required by identity in the Android CI general-report gate, whose 23 host
checks passed. Two earlier private-suite attempts failed: first on a stale
accessibility node during redundant editor launch, then on a stale expand node
before click. The redundant launch was removed and the expand-node lookup now
reacquires a stale node within a bounded wait. A later private-suite attempt
failed to find the Russian expanded candidate, as described above; no claim of
a general cause is made.

The revised app and test APKs built offline in a temporary clone with the pinned
runtime submodule. The temporary clone, emulator, its ADB server and build
outputs were removed. The revised fixture has not yet been run on Fold; the
private-field test does not prove that closing a pre-existing normal session or
an interrupted test cannot produce diagnostics. A host-side owner backup and
post-run verification remain required. The displaced original Fold journal
remains in the existing private recovery archive. Hosted CI and manual TalkBack
are not established.

## Fold private-fixture retention check

On the physical Fold, source `d31c0cc6` was built as a debug test APK in an
offline temporary clone with the pinned runtime submodule. The test APK SHA-256
was `611452f3a884191d78cfa8585b8b3f8b535c8e1f9fcfc5bc8c205852b6e0adc`.
Using explicit-device ADB with the physical opt-in and failure captures off,
`hiddenCandidateCanBeExplicitlySelectedInRealIme` and
`typingOutsideExpandedRowClosesItWithoutSelectingOldCandidate` each reported
`OK (1 test)` with no assumption skip. The Russian ordinary-field scenario was
not invoked. The installed main app was not updated; its exact source identity
was not independently established in this run. The device reported `OPENED`
and 1968×2184 afterwards, without continuous posture observation.

Before installing the test APK, a private host snapshot captured the original
test APK, four IME system settings, shared preferences and the six named
personal/diagnostic store roots. After both tests, the original test APK was
reinstalled and matched its saved SHA-256, the main APK was unchanged, all four
system settings matched, and the set and contents of files and directories in
those saved preference/store roots matched. This includes the diagnostic files,
not just a comparison of aggregate counts. The per-run backup was removed only
after that verification. The older private recovery archive containing the
previously displaced original diagnostic journal remains intact. The temporary
build clone was removed. The test output itself was not retained beyond the
recorded result. This does not establish source identity of the installed app,
ordinary-field diagnostic retention, cover display, manual TalkBack or hosted CI.

## 2026-11-24 live TalkBack traversal of the expanded row

The `75d06f6f` debug APK ran in an owned API 37 emulator with TalkBack
17.0.0.889642762 and touch exploration on. A passive accessibility
observer tracked focus and click events. The virtual touchscreen typed
the public `addess` fixture and activated Show more suggestions.
Twelve forward swipes went through the keyboard letters, starting with
`q`. Direct touch exploration of the expanded row found the hidden
`Correction: access` button. A double-tap selected it and the remote
editor displayed `access`. Trace SHA-256:
`c887c83a1d7cb8db67b7285c7f75c202dddc657be2e4fa1620f9438b3715372c`.

Three popup approaches were checked. A direct accessibility-focus
action showed a second focus outline while activation still targeted
the underlying expand button. A focusable popup transferred TalkBack
focus to the hidden candidate, but a double-tap over blank editor space
dismissed the popup. An outside-touch interceptor permitted selection
in one diagnostic build. All four ordinary expansion checks passed in
that build. The lint-clean repeat confirmed Back dismissal and transfer
to the hidden candidate, then reproduced dismissal without selection
both after reopening and in a fresh editor. Its two trace digests are
`b35cea27b41224e7eaf1d1becd73110fc87f2fa23b9fd080c6f941ac91f5b337` and
`034d6517c8de4c986e6770855fac0635ad49d8b0e78fed4aa83514ef1b09064c`.

The popup changes were reverted. A single-window solution should
verify forward traversal, double-tap on a neutral area, Back, and a
second expansion, while retaining normal outside-key typing and stale
selection cancellation. API 26's local image has no preinstalled
TalkBack, and physical Fold acceptance remains open. The owned guests,
observer, raw traces, screenshots and temporary APKs were removed.

## Expanded row in the IME window with TalkBack

On an isolated API 37 emulator, TalkBack 17.0.0.889642762 entered the public
fixture `addess` in the composing QA editor. The first forward swipe after
activating **Show more suggestions** focused **Correction: access**, reported as
a clickable button. Back closed the expanded row, and TalkBack could reach the
expand button again without reopening the keyboard. After reopening the row, one
forward swipe and a double-tap outside the row selected the focused correction.
An independent UI hierarchy dump read the exact editor value `access` after the
accessibility observer disconnected.

The row and toggle share the IME window. The first hidden candidate follows the
toggle in accessibility traversal. Android 13+ registers the overlay Back
callback only while the row is open. The older IME key-event route handles Back
on earlier Android versions. The initial same-window prototype passed forward
traversal. API 37 hid the keyboard on Back until the overlay callback was added.

The tested debug APK SHA-256 was
`8ba1ff39d2196eb07ef99e543c3508910d2c11b92d2188b84837afcb303409ef`.
The TalkBack event trace SHA-256 was
`1a586166a1d9aa6a6a65f193594d48ff43966d65f1d3cb0a9d4cc514a369c20e`.

The debug APK, instrumentation APK and debug lint built successfully. API 37
passed all 31 selected instrumentation cases: four real IME scenarios, 16
candidate-strip checks, five physical-touch checks, four dynamic-touch checks
and two version-eligible safe-inset checks. The cases cover Back and reopening,
English and Russian choice, typing with the row open, shared window identity,
unchanged height and key instances, and cancellation of a held stale choice.

API 26 passed all 20 real-IME and candidate-strip cases on the same APKs.
The API 26 image did not include TalkBack. Both frozen product replays matched
their reference projections exactly (2,160 plus 12,000 rows). The projections
were `e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`
and `b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512`.
The updated layout and accessibility flow still need physical Fold acceptance.
