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
The server accepts only two fixed GET routes and two numeric POST routes; it
never serves a directory and retains at most 512 metric records.

Each test closes its own tab, identified by the exact loopback address in the
browser toolbar, and restores the owner's full keyboard settings and IME state.
After success or interruption, verify the test is terminal, close only remaining
owned fixture tabs, remove only the created reverse mapping, stop the server,
and verify owner state. Neither background processes nor global ADB state should
be reset. This fixture measures the current display configuration; it does not
prove cover/inner/rotation, omnibox GO, other applications or full Q8 acceptance.
