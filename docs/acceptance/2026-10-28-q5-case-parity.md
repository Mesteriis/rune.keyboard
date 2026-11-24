# Q5 case ambiguity overlay: additional disclosed parity

The same isolated ten-key canonical-case overlay was compared with a newly
captured current-product baseline over 4,728 Russian inputs: 720 FrequencyWords
parity rows, 4,000 historical spelling-parity rows and eight previously reviewed
chat controls. Both observers completed all rows. After normalizing the opaque
controller ID and excluding timing fields, **all non-timing observation fields
matched**, including candidates, editor commands, boundary output and Undo.

The 4,720 parity rows are previously disclosed and unlabeled; expected spelling
in their transport is a placeholder, not ground truth. This is a behavior-parity
check, not an independent holdout, estimate of accuracy or evidence that the ten
keys are safe in name contexts. The eight extra controls concern an earlier
rare-word experiment; they are not the five capitalization failures. The
separate [chat replay](2026-10-28-q5-case-evidence-overlay.md) measured those
five on the corpus used to choose the overlay.

The candidate remains an in-memory modification of the host observer, not a
packaged asset or production policy. The parity runner version is recorded at commit `1cc3181`; it was later
extended for the separate name-contrast experiment. The [receipt](2026-10-28-q5-case-parity.json)
binds the input rows, review screen, runner, comparison tool, harness and both
outputs. Full logs and source bindings are retained in ignored `build/q5-case-parity-*`.
Three candidate-runner tests and 16 existing comparison/fixture tests passed.
An initial command selected a nonexistent test filename and returned “no tests”;
the correct existing test module was then run. The owner phone was not used.
