# U9 — modifier CommitText over the real editor Binder

The review requires instrumented insertion/deletion of modified sequences, while
explicitly treating a skin-tone selector as a separate stage. This step adds
coverage of the existing CommitText entrance; it adds no production selector,
catalog variants or other runtime changes.

With the actual IME emoji layer open and an uncorrected `teh` prefix in the
separate-process QA editor, the test dispatches fixed synthetic `👍🏽` and
`🧑🏽‍💻` at RuneInputMethodService.handleAction. Reflection is test-local and
uses the root IME window's Context; it does not bypass the reducer, typing
session, editor-command executor or real InputConnection/Binder. This is action
contract coverage, not a claim that a modified entry is selectable from the grid.

For each sequence, the editor must contain the unchanged prefix plus the exact
sequence. All six editor payload-read counters must remain unchanged during
insertion. One actual keyboard Delete must then restore the prefix with no
remaining modifier/ZWJ fragments. Existing UI-driven ZWJ/flag insertion,
incognito recents policy and post-emoji correction tests run alongside this case.
EditorBoundaryInstrumentedTest also covers complex-grapheme deletion, real touch
injection, editor transitions, field restrictions and selection/cursor commands.

The adjacent evidence binds the final debug/test build, exact APK/test-source
identities, native nine-case result and emulator cleanup. The first attempt had
one test-setup failure before dispatch: the themed keyboard Context did not expose
the service. That failed nine-case result (eight passed) is retained separately.
After changing the lookup to rootView.context, the entire suite was rebuilt and
run on a new clean API 26 arm64 AVD. Production APK bytes are identical between
attempts. Both AVDs were stopped/deleted. No phone was used or updated.

This step does not close U9. The four failed 50 ms draw-start observations in the
u9-emoji-deferred receipt remain failed. Cold IME/PSS, release/presented-frame,
category/recent-lookup latency, Fold displays and manual TalkBack remain open.
