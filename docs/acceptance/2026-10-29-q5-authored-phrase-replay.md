# Q5 authored dialogue phrase replay

The 20 [pre-registered author-written phrase inputs](2026-10-29-q5-authored-phrase-inputs.md)
were typed word by word in separate current-product JVM controller/editor
sessions. The source is human-written but scripted and small. Punctuation was
removed for this harness; this does not simulate real Android input or establish
natural-message accuracy.

Two runs were byte-identical. Across 20 phrases and 80 words the observer
reported zero boundary changes, prefix changes, case-only changes and automatic
edits. Thus there was no automatic edit on which to exercise Undo: zero checks
is not an Undo pass. The zero changes are observations on this disclosed set,
not a false-change estimate or a qualification. Each observed stage input and
output context is already in both registries; future undisclosed output is
refused by the replay gate until registered.

The [receipt](2026-10-29-q5-authored-phrase-replay-evidence.json) binds the
source, inputs, current registries, controller sources, model assets and JVM
inputs; external model calls were disabled. The evaluator's unit test exercises
case changes, session consistency and Undo failure handling. This remains a
regression diagnostic; the required labelled baseline and independent corpus,
real-device validation and correction/Undo coverage remain open.
