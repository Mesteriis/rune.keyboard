# Enter and editor actions — 2026-09-03

Baseline `f060da1`. Enter now retains the latest accepted candidate decision
until the action consumes it. It never waits for scoring. Multiline Enter uses
the known `\n` write, commits the corrected or original word, and leaves no
composing span. SEND/GO/SEARCH/NEXT/DONE/custom actions prepare the same word,
then issue the exact action without adding a period or any other punctuation.

If an action explicitly returns false, Rune commits newline as a separate owned
fallback. A correction transaction is extended to include that newline, so the
first Backspace restores the original word and removes the fallback. An exception
or missing connection is an unknown action outcome: Rune does not replay a
fallback, discards ephemeral session ownership and waits for an actual selection
callback. Rejected/ambiguous text preparation also drops the action without a
second mutation. Sensitive, raw and unsupported editors keep their established
legacy path.

Six new JVM tests cover corrected and original newline, closing composition,
SEND without punctuation, fallback Undo, rejected preparation, and accepted /
refused / unknown exact-action results. Fresh JVM641/641 PASS, zero failures,
errors or skips. The final-source lint, all variants, privacy/dependency/IME and
native-symbol gates plus Android test assembly pass (277 tasks). API26 and API37
real `InputConnection` editor-action suites pass2/2 each (348.546s /264.047s),
including multiline newline and the six editor actions.

Production spelling qualification remains closed, so automatic correction on
Enter is proven with injected admission in the real controller/executor JVM
fixture, while Android proves the production routing with Original. Full
automatic IME Binder qualification remains part of the final gated pipeline.
No editor readback, network path, new model work, punctuation before SEND, push,
publication or version change was added. Contextual punctuation, final holdout,
Fold typing/energy and release qualification remain open.

Evidence: `tools/qa/smart-typing-0.3/results/2026-09-03-enter-actions/`.
