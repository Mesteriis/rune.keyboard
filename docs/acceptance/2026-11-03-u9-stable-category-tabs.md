# U9: retain emoji category views across panel updates

Selecting an emoji category previously removed all category views and created
new ones, losing the selected tab's view identity and any focus owned by it.
The API 26 test reproduced this on the original implementation: after the
`People & Body` click, the original and current tab were different objects.
The panel now retains category views, updates labels and selected state, and
inserts or removes only the recent tab when the privacy policy changes. Click
handlers use the panel's current language and privacy state.

The targeted test checks category view identity and synthetic keyboard-focus
retention, language relabeling, selection and recent-tab removal. Two initial
post-fix test setups could not request focus while the emulator was in touch
mode. The final test explicitly enables touch-mode focus for that view before
requesting it; it is not a manual TalkBack or accessibility-focus traversal.
The final API 26 suite passed seven tests, including this case, full catalog/font
and recycling checks, four actual IME panel scenarios and a measurement. API 37
passed the six corresponding non-measurement cases. No tests were skipped.
Both task-created emulators were stopped and deleted.

Four API 26 preview samples measured handler times of 7.31, 6.63, 6.53 and
11.17 ms and draw-start times of 17.49, 16.34, 17.04 and 18.48 ms. They are
warm, same-emulator samples after other tests, not a causal speedup, reliable
cold tail, presented-frame latency or Fold measurement. All four were under
50 ms for these recorded stages. The full JVM suite passed 1,391 tests with no
failures, errors or skips; debug lint and the IME/scoring dependency boundary
passed. Debug APK SHA-256:
`5825f354316496c839f9f0e4c94b313c63bc373c06ef5b37f9f41647a2922bd5`.
Instrumentation APK SHA-256:
`eaff74f4faf6643860541b7c9611d629fe75cb5f1db1a4e9f639d884473b8238`.

The initial release privacy command stopped at `RELEASE_SOURCE_DIRTY` because
these changes were uncommitted; its source-check tests and IME boundary did
pass. It is not a release-gate pass. Logs are under
`build/u9-focus-*-20261103.log`. Fold layout/performance, presented-frame,
manual TalkBack and remaining U9 acceptance remain open. No physical device was
used for this change.

Follow-up: an isolated clean checkout at commit `0e9cc6b4` with the pinned
submodule initialized passed `:app:privacyGateRelease --offline`. The source
check reported zero dirty entries and one verified submodule; release packaging,
release lint-vital and the diagnostics packaging gate completed successfully.
The checkout remained clean. The first dirty-worktree refusal above remains a
failed run, not the source of this result.
