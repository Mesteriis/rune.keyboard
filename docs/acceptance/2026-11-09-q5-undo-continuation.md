# Q5: continue a phrase after Undo

The full disclosed 9,543-phrase controller replay was repeated twice after
adding an opt-in test-harness mode; its unmodified results matched the earlier
product replay byte for byte. The new mode is absent from normal operation and
from Rune's production APK. It reproduces a chosen automatic correction,
backspaces to Undo, presses Space again, then continues typing the rest of the
same phrase with the same controller and editor session.

There were 123 observed corrections with at least one following word. Each
was replayed twice: the chosen before/after states had to match the original
full phrase, Undo had to restore the exact text, and Space had to preserve that
restored word. All 123 cases passed and continued through 381 subsequent words;
no later stage changed text before its current word. These are controller/JVM
simulations on disclosed, unproofread public data, not real IME, timing, user
intent, natural-quality or independent qualification evidence.

The [numeric receipt](2026-11-09-q5-undo-continuation-evidence.json) binds the
baseline, source, assets, toolchain and per-index results. Ten previously
unregistered control keys arose during continuation; two independent registry
writes agreed byte for byte and preserved all earlier entries and the existing
incomplete-coverage status. All observed lexical contexts were already
registered. The new registry check and two runner and two registration tests
are included in CI; one test demonstrates that an actual resulting context is
rejected as a fresh control. Hashes of public text are unsalted and reversible.

The existing six-phrase replay also passed with its prior results and exact
Undo checks. Temporary inputs, raw observations and build artifacts were
removed. Fold, hosted execution, a fresh independent corpus and broader Q5
acceptance remain open.

## Real IME continuation

A separate mandatory Android test types the public sequence `зочу`, waits for
the `хочу` correction candidate, commits the correction, uses backspace Undo,
presses Space again, and types and commits `домой`. The remote composing editor
must contain exactly `зочу домой ` and report zero payload readbacks throughout.
The individually invoked test passed with exact instrumentation events and no
skips on isolated ARM64 API 26 and API 37 emulators. The Android required-case
report gate includes the identity, and its 15 host tests passed. The temporary
checkout, APKs and emulators were removed. This one real-IME scenario does not
extend the JVM sample's coverage to all 123 cases or establish Fold behavior.
