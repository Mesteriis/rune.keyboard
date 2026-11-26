# Q5: disclosed Tatoeba full-session controller replay

The 9,543 previously disclosed, unproofread CC0 Tatoeba controls registered in
[the input preparation](2026-11-09-q5-tatoeba-phrase-inputs.md) were replayed
as complete two-to-six-word sessions. The JVM observer types each word into one
controller/editor session, runs local candidate/recovery generation and commits
a space before continuing. It checks exact Undo after an automatic edit on the
last word only. This does not exercise a real Android IME, timing, external
model, or intermediate-word Undo.

Two runs produced byte-identical results. Across 42,153 word stages, 166 phrases
had at least one change: 169 boundary changes, including 148 case-only changes;
169 were reported as automatic edits. The observer found no prefix changes and
checked 33 final-word Undos, all exact. These are descriptive counts, not a
false-change rate: the public source is not independently proofread and contains
known spelling, colloquial and capitalization ambiguities. The source has
previously been exposed and is not a qualification holdout.

Both the typed context and the resulting context of each stage were examined:
84,306 observed variants. After subtracting existing registrations, the two
persistent registries received 431 additional control and 56 additional lexical
context keys. Two independent extractions and registrations produced identical
outputs, preserving every prior entry and the incomplete-coverage status. The
[retained numeric receipt](../../tools/typing_experiments/chat_regression/tatoeba-full-phrase-replay-v1.json)
binds the old registry snapshots, source, selection, product sources, assets,
toolchain and result SHA-256. The separate observed-key fixture binds that
receipt; these unsalted hashes do not anonymize public source text. A check and
negative tests are routed into CI. The original generated observations and
temporary builds were removed after registration.

Input registries were at commit `d6883782`; the replay harness added in this
change is bound by its hash in the receipt. The full historical snapshot must
be used when reproducing the original receipt: the current registries now also
contain the observed exclusions. Broader manually verified controls, independent
qualification, physical-device replay and hosted CI remain open.
