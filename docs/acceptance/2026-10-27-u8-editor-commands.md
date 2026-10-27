# U8 — editor-command execution foundation (partial)

This slice implements the command executor following the selection prototype at
7934bb6. It does not expose an editing layer or claim complete U8 acceptance.

EditorCommand now has NavigateCursor with six closed directions (Left, Right,
Up, Down, Home, End) and an explicit extendSelection flag, plus ContextMenu with
Select All, Copy, Cut and Paste. Existing space-drag MoveCursor and text commands
are unchanged. Home/End use MOVE_HOME/MOVE_END, with line geometry owned by the
editor. Vertical single-line restrictions belong in the forthcoming reducer/UI;
the low-level executor has no EditorContext and is not a public keyboard entry.

Extending navigation brackets the arrow’s Down/Up with SHIFT_LEFT Down/Up and
META_SHIFT_ON, following the successful real-EditText prototype. Releases are
attempted in finally after refusal or exception, including an uncertain arrow
Down. A refused Shift Down stops before the arrow; there is no movement retry or
fallback protocol. Failed releases report failure; this is not a guarantee that
an uncooperative editor released a modifier. No held synthetic Shift state is
retained between commands. The small dispatch callback seam permits meaningful
JVM cleanup tests without constructing mock Android KeyEvent objects.

Context menu commands call only InputConnection.performContextMenuAction with
the named framework ID. They reject raw-key and sensitive contexts before touching
the connection. Runtime exceptions return failure, with no retry or clipboard
fallback. Normal and incognito contexts are supported. Both new command types
leave cached selection metadata unclaimed: handled means dispatch acceptance,
not completed movement, copying or insertion. No success message was added.

Validation:

- All 1,208 JVM tests pass (zero failures/errors/skips). Six new tests cover all
  six direction/key/meta combinations, all four refusal/exception points, ordinary
  arrow release, exact menu IDs and return values under normal/incognito policy,
  raw/sensitive refusal before calls, and menu exception without retry or fabricated
  selection reset. Existing typing/reducer/executor tests remain green.
- IME/scoring boundary, release privacy, debug lint and debug/test APK builds pass.
- Six final Android 36 arm64 emulator tests pass, without skips: three actual
  executor cases plus the unchanged three prototype controls. The executor uses
  the real Rune-to-:qa_editor Binder connection. Actual KeyEvent action/code/meta
  sequences are asserted, emoji selection avoids the surrogate middle, Shift is
  released before the next ordinary arrow, and Home/End reach real editor carets.
- Native Select All, Copy, Cut and Paste are exercised. The test process overwrites
  its disposable clipboard with a public sentinel before observing Copy, verifies
  the copied public seed, reselects before Cut (Copy may end selection), explicitly
  supplies the public paste text, checks the resulting real field and then clears
  the fixture clipboard. Clipboard reads here are test-observer code, never product
  code. The executor imports no ClipboardManager and never acquires selection text.
- All six InputConnection payload counters stay zero before and after execution.
  This is an input-connection read assertion; the test observer intentionally reads
  only its fixed public fixture output/clipboard. No personal data or Fold is used.
- The isolated emulator is stopped/deleted. All 88 sources and 18 assets bound to
  the prior ordinary product replay still match. Those sources do not include the
  editor-command executor/types, so that identity cannot prove these new commands;
  the JVM and native checks above provide their evidence. No new replay or general
  accuracy/performance claim is made.

Remaining U8: reducer actions, editing layer/entry popup and labels, arrow repeat,
single-line/TYPE_NULL presentation restrictions, owned-context invalidation and
awaitEditorSelection for Cut/Paste, post-paste foreign-boundary regression,
EditText/WebView/Compose integration, physical/manual TalkBack acceptance and the
public clipboard/privacy/user copy. Current user-facing layouts are unchanged.
Commands must not be connected to the UI before those ownership guards are added.
The adjacent receipt binds sources, built APKs, commands, logs and actual outcomes.
