# U15 mode-key entry: current behavior and acceptance conflict

The review predates U8's editing panel. On the current source, the ordinary
`?123` key has one long-press alternate, `OpenEditing`, across the three
languages. The layout test asserts this. In password fields its alternates are
empty; the Android editing-panel test asserts there is no accessibility long
click on the mode key. The symbol/emoji `ABC` key has no alternate.

`KeyboardKeyView.performLongClick()` dispatches the **first** alternate, and
its accessibility node labels that action as editing only when the first action
is `OpenEditing`. U8 Android tests invoke this action to reach the editor panel.
The alternate popup is non-touchable: the held key owns touch and selection.
Therefore putting the keyboard switch first, as the older U15 proposal says,
would silently replace the existing accessibility route to editing; merely
adding later visual cells would not prove those actions reachable by TalkBack.

The existing `NextInputMethod` reducer command already invokes a service helper
that attempts switching on API 28+ and falls back to the system picker, but the
mode key does not expose it. The manifest's `android.view.InputMethod` action is
in Rune's own service intent filter; it is not a package-visibility `<queries>`
declaration. This inspection does not establish whether one is required for
voice IME discovery on any Android version.

U15 remains unimplemented. Its implementation needs an explicit accessibility
route for each available command while preserving U8 editing and sensitive-field
behavior, followed by actual popup, picker and voice/no-voice tests and Fold
acceptance. This source review does not count as a TalkBack or device test.
