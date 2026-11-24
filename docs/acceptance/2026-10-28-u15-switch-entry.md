# U15 next-keyboard entry (partial)

The non-sensitive `?123` popup now includes the existing next-input-method
command after Edit, preserving U8's default accessibility long-click. The `ABC`
mode key offers the same switch. A separately labeled accessibility action
exposes the command without replacing the tap or editing action; popup cells can
carry a spoken label distinct from their glyph. Password fields retain no mode
key alternates. The existing command attempts the platform next-IME switch on
API 28+ when offered and otherwise opens the system picker.

Validation: all 1,360 JVM tests passed, with zero failures/errors/skips;
`lintDebug` and `imeIntelligenceBoundary` passed. Layout tests cover all three
languages, both symbol pages and password controls. API 26 passed seven focused
key-view methods; API 37 passed 15 key-view and real editing-panel methods.
The new node test checks the named action, dispatch, editing long-click, tap and
disabled-key refusal. Raw logs are in ignored `build/u15-*`.

The initial API 26 combined run failed five of 15 methods: the new test lacked a
parent View (fixed for the final runs), while four editing tests used the newer
`ClipboardManager.clearPrimaryClip` in teardown. It is not counted as a pass;
the existing full editing suite was run successfully on API 37 instead.

Debug APK SHA-256: `600b0d7c9fd2d5e1c8a36f74d02e9139e7cc5c497bed3eb89e7b6d55262fde56`.
Test APK SHA-256: `1ef89f662d6b2d24e5acbaf4ab9a5349d5424d5df57c4776b52fd23198a940f7`.
No actual system picker/IME switch, popup gesture, TalkBack session or Fold test
is claimed. Voice discovery, voice switching and the rest of U15 are not yet
implemented. Neither APK was installed on the user's phone.
