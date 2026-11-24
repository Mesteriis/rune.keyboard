# U18: independent keyboard palette, partial acceptance

Keyboard shape remains independent of a new persisted dark/light/system
palette and of the settings application's theme. Existing and malformed values
fall back to dark without rewriting storage. The home preview and live IME use
the selected palette; system mode follows the system configuration even when
the settings application is forced dark. Changing palette rebuilds the input
view. The five existing shapes use immutable palette colors; dark Outline's
normal border is made brighter so it meets the review's 3:1 outline threshold.
Dark remains the default, but this border is a deliberate appearance change.

The IME requests matching navigation icon appearance and a dark navigation
background on API 26, where light-navigation icons are unavailable. Android 15+
may enforce a transparent system navigation bar; [Android's edge-to-edge
guidance](https://developer.android.com/develop/ui/views/layout/edge-to-edge)
describes this platform behavior. Tests check the actual sampled navigation
backdrop and icon appearance on the current emulator configuration, not just
the requested window color. A subsequent API 37 emulator run covered both gesture and three-button modes;
see [navigation evidence](2026-10-28-u18-navigation-modes.md).

The final app passes all 1,360 JVM tests, `lintDebug`, and the scoring boundary
check. A later clean-source run passed `privacyGateRelease`, the IME boundary
and forbidden-runtime-dependencies gates; see [release evidence](2026-10-28-u18-release-boundary.md).
Palette tests check all five shapes and both palettes across text,
secondary text, selected text, common surfaces and Outline borders. API 26 and
37 each passed four final-build instrumented methods covering settings persistence,
live color and navigation state, system dark/light changes with text preservation,
and home preview independence from the app theme. After the preview integration, the complete current nine-method theme suite
passed on both API 26 and API 37, including all ten shape/palette combinations,
fixed-viewport rendering, and the later navigation capture method. See
[full-suite evidence](2026-10-28-u18-final-theme-suite.md). Local synthetic
preview captures are in ignored `build/u18-palette-preview/`.

Earlier test attempts are retained as evidence: an overbroad unit assertion
incorrectly required Outline borders on other shapes; a corrected scope passed.
The first device inspection incorrectly searched the keyboard's themed context
for the IME service, and both emulator runs failed that test; using the window
root resolved the inspection. A later API 37 test expecting an opaque
`navigationBarColor` failed because the platform returned transparent; the
updated test checks rendered backdrop and icon appearance instead.

This is not complete U18 acceptance: Fold cover/inner screens, manual TalkBack,
popup and expanded-row manual checks, navigation on Fold and other Android
versions, API 29 and additional Android 35+ variants, and distribution screenshots remain open.
No Fold installation or external release was performed. The adjacent evidence
binds the current app, tests and APKs; earlier seven-test runs used the build
before the preview integration.

## Fold inner-screen palette check — 2026-11-10

On the unfolded Fold, `paletteChangesRebuildImeAndKeepItsText` passed on the
installed debug app and test APK built from `b48d73c2`. This automated check
exercised palette changes and preservation of its synthetic editor text. The
device reported `OPENED` before and after the run; its state was not sampled
continuously. Keyboard and diagnostic preferences and the selected IME matched
before and after. Rotation displaced one original diagnostic file, whose exact
bytes were preserved in a private, Git-ignored recovery directory. That directory
contains owner diagnostics and must not be treated as a build artifact.

This single check does not establish the remaining U18 manual accessibility,
popup, navigation, display-transition, or broader device acceptance.

## Light Monolith with real TalkBack on API 37

On an isolated API 37 emulator, candidate `687361c8` ran with the Monolith
shape, Light palette and TalkBack 17.0.0.889642762. Touch exploration and
double-tap typed the public fixture `addess`. A forward swipe from the
expanded-suggestions toggle reached **Correction: access**. A double-tap
selected it. Activating **Shift** exposed **Shift on** and uppercase **Z**.
An independent hierarchy dump verified the exact editor value `accessZ`.

The captured screen contained the Monolith bottom strip at `#e0e0e0`.
The base, expanded row, Shift state and ordinary touch long-press popup
also contained the expected palette colors. The ratios below use the
foreground and background colors identified in the captured regions.

| Element | Foreground | Background | Contrast |
| --- | --- | --- | ---: |
| Key labels | `#1a1a1a` | `#e8e8e8` | 14.20:1 |
| Expanded candidate labels | `#484848` | `#f2f2f2` | 8.17:1 |
| Selected Shift | `#0a0a0a` | `#d2d2d2` | 13.09:1 |
| Key popup | `#1a1a1a` | `#f2f2f2` | 15.55:1 |
| Selected key popup cell | `#1a1a1a` | `#d0d0d0` | 11.28:1 |

The debug APK SHA-256 was
`6b31bee517d2a99427a417e1fd22894abb01876e759d387dd643add23b0bf28d`.
The event trace SHA-256 was
`597d1573d15ad594cf64e85c194ca97f3f0896c5d74a82199942982077ab1c73`.
The [English store screenshot](2026-10-28-u18-light-store-screenshot.md)
matched its recorded hash. The README, Russian user guide and all three
Fastlane descriptions already cover the palette choice. The emulator and
its temporary files were removed. Physical TalkBack, visual checks on both
Fold displays, the remaining navigation configurations and distribution
acceptance remain open.
