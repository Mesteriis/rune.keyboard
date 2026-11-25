# Chrome editor compatibility fixture

This opt-in Fold test uses real Rune touches in Chrome, a separate loopback-only
public page, and a numeric DOM oracle. It never opens an existing user document,
sends a message, exports page text or changes production networking permissions.
The two HTML pages differ in `autocomplete=on/off`; Chrome's actual EditorInfo
flags and session availability are measured rather than assumed.

Build `:app:assembleDebugAndroidTest` and install that APK with `adb -s` on the
explicitly authorized Fold. Preserve owner state and coordinate its exclusive
window before driving it. The app APK must match the source under test. Start:

```sh
python3 tools/qa/chrome-editor/serve.py --port-file /tmp/rune-chrome.port --receipt-file /tmp/rune-chrome-dom.jsonl
```

The handoff files must not already exist. Read the allocated port, create only
that port's `adb -s "$RUNE_FOLD_SERIAL" reverse tcp:PORT tcp:PORT` mapping, and run:

```sh
adb -s "$RUNE_FOLD_SERIAL" shell am instrument --user 0 -w -r \
  -e class io.github.mesteriis.rune.keyboard.qa.ChromeEditorCompatibilityInstrumentedTest \
  -e runeLoopbackPort PORT -e allowPhysicalDevice true -e runeFailureArtifacts false \
  io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner
```

Save the actual output as the native log, then require the independent gate:

```sh
python3 tools/qa/chrome-editor/verify.py --receipt /tmp/rune-chrome-dom.jsonl --native-log /tmp/rune-chrome-native.log
```

**The native test alone cannot establish correction or Undo correctness.** Chrome
can remove the focused DOM editor from its accessibility tree while its IME
connection remains active. Exact known-string comparisons occur inside the page;
only bounded integers and boolean flags reach the host, with no input text.
The gate requires five corrected words, exact Undo, correction of the sixth word,
and five literal words plus Backspace when suggestions are forbidden. It rejects
missing/out-of-order stages, unexpected fields, strings and incomplete native runs.
The server accepts only three fixed GET routes and three numeric POST routes. It
never serves a directory and retains at most 512 metric records.

Each test closes its own tab, identified by the exact loopback address in the
browser toolbar, and restores the owner's full keyboard settings and IME state.
After success or interruption, verify the test is terminal, close only remaining
owned fixture tabs, remove only the created reverse mapping, stop the server,
and verify owner state. Neither background processes nor global ADB state should
be reset. This fixture measures the current display configuration; it does not
prove cover/inner/rotation, omnibox GO, other applications or full Q8 acceptance.

## Disposable emulator

The same test can run on an explicitly owned emulator with Chrome installed.
Use an isolated ADB server and replace `-e allowPhysicalDevice true` with
`-e runeOwnedEmulator q8-chrome`; the test also requires emulator hardware and
`ro.kernel.qemu=1`. Complete first-run Chrome setup without an account. Start a
fresh fixture on a port not already open in another Chrome tab, then apply the
same native and DOM verification above. This supplements, but does not replace,
the physical Fold matrix. Remove the owned reverse mapping and stop the fixture,
emulator and isolated ADB server after the run.

## Android emulator CI

### Separate landscape omnibox test

On the owned API 37 emulator, use a fresh fixture port and Chrome tab. The
omnibox test rotates the display and types the last two characters of a fixed
loopback URL using Rune. Backspace removes the extra character. Go loads the
second fixture page. The test checks that the keyboard's Delete control and
the input service's shown state both clear after navigation.

```sh
adb -s "$RUNE_QA_EMULATOR" shell am instrument --user 0 -w -r \
  -e class 'io.github.mesteriis.rune.keyboard.qa.ChromeOmniboxInstrumentedTest#landscapeGoLoadsOwnedPageAndDismissesKeyboard' \
  -e runeOwnedEmulator q8-omnibox -e runeLoopbackPort PORT -e runeFailureArtifacts false \
  io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner

python3 tools/qa/chrome-editor/verify.py --navigation \
  --receipt /tmp/rune-chrome-dom.jsonl --native-log /tmp/rune-chrome-native.log
```

The navigation gate requires the exact native case and independent numeric
reports from both empty pages, with the original page observed first. Both
scenarios use the existing loopback routes. The textarea oracle still checks
its original word and Undo stages.

The API 37 smoke job runs the omnibox case separately using the same owned-AVD
runner. The command allocates a fresh loopback port and saves a separate native
log, numeric stream and verdict.

```sh
python3 tools/ci/android_chrome_editor.py --avd-name rune-ci-boundary \
  --output build/ci-chrome-omnibox --navigation
```

### Textarea route

The API 37 smoke job runs the Chrome textarea class and its numeric oracle
with `tools/ci/android_chrome_editor.py`. The command requires an owned
`rune-ci-*` API 37 userdebug emulator, installed ordinary debug and test APKs,
and the image's Chrome package. It temporarily supplies Chrome's first-run
flags, allocates one loopback reverse port, and removes the port mapping and
temporary Chrome configuration on exit. The route refuses an existing Chrome
flags file or debug app configuration. It requires both exact instrumentation
cases and the ordered DOM outcomes. The matrix collects the native log,
numeric event stream and result.
[Chromium Android command-line flag documentation](https://new.chromium.org/developers/how-tos/run-chromium-with-flags/#android)

### Foldable emulator textarea route

Use a disposable API 37 foldable profile with a cover display, such as the
Pixel Fold. Boot and unlock it on the inner display. Install the matching Rune
debug and test APKs and select Rune before starting the run.

```sh
python3 tools/ci/android_chrome_editor.py --avd-name rune-ci-q8-fold \
  --output build/ci-chrome-fold-transitions --fold-transitions
```

The same Chrome tab holds three corrected words and a literal fourth word
before the fold. The test dismisses the emulator keyguard if it appears and
uses Ctrl+End to resume at the end of the same field. Rune completes the
fourth word with Space on the cover display, corrects the fifth word, and
undoes that correction. After unfolding, the test returns to the end again,
enters the separator, and requires correction of the sixth word. The independent
DOM oracle checks exact text at all three word boundaries and the existing
literal no-suggestions control. The native fixture separately requires the
display width to change in both directions and the closed and reopened
editor to remain on the owned loopback tab.

### Password route

The separate API 37 case compares preview visibility for ordinary and password
inputs on one loopback page with preview enabled. It then types a synthetic
value in the password field and presses Backspace. Exact string comparisons
run in Chrome. The host verifier requires the empty, full and one-character
shorter stages in order, and the native test closes the owned tab. Preview
images stay in emulator memory.

```sh
python3 tools/ci/android_chrome_editor.py --avd-name rune-ci-boundary \
  --output build/ci-chrome-password --password
```
