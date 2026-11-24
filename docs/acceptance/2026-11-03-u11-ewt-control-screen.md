# U11: unannotated EWT controls for the English edit prototype

The [previous edit-channel experiment](2026-11-03-u11-ewt-annotated-edit-model.md)
was screened against EWT test tokens with no `CorrectForm` annotation. The
prototype and development-selected weight are reproduced exactly before this
screen; source hashes and both existing exclusion registries are checked before
the text is read. Exact words used in annotated training or development are
excluded. A token lacking `CorrectForm` is not a verified correct-word label:
it may still contain a source error, a name, or another unusual form. EWT was
already disclosed, so this is not an independent holdout.

Among 19,669 alphabetic tokens of length 2–32, the frequency vocabulary
protected 19,053. Seven unknown tokens matched annotated train/development words
and were excluded. Of the remaining 609 unknown-token occurrences, the offline
one-edit vocabulary search found at least one alternative for 306; 303 had none.
There were 440 distinct unknown forms. UD labels 385 occurrences as proper
nouns; 198 of them had at least one alternative. These are source-change
opportunities under the experimental search, not measured product changes or
an estimate of false-change probability. Individual occurrences need separate
human review to establish whether the original is correct and should be kept.

Of the 306 occurrences with alternatives, 104 had a single candidate. A
relative-score margin alone assigns those cases an unbounded margin; even a
fixed log-score gap of at least 3 would retain 112 occurrences in total.
These are arbitrary diagnostic score units, not calibrated probabilities.
The finding rules out treating a lone dictionary match or this margin alone as
sufficient evidence for automatic correction.

Two pinned-source runs produced byte-identical [aggregate receipts](2026-11-03-u11-ewt-control-screen.json).
No source tokens, document IDs, sentences or per-token observations were
written. The receipt binds the historical registry snapshots but does not claim
English family completeness. Six host tests cover annotation filtering, known
word protection, prior-word exclusions, candidate counts, the single-candidate
margin, missing exclusions and retained receipt bindings. CI runs these tests
without requiring the EWT source; rerunning the actual source screen requires
the exact pinned public files. The current Rune candidate engine, thresholds,
APK and phone were not changed. Natural labelled controls, product replay,
calibration and independent qualification remain necessary for U11/Q6.
