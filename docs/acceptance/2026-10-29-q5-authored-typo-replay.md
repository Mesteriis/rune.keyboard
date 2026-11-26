# Q5 authored dialogue deletion replay

The 19 [pre-registered one-deletion phrases](2026-10-29-q5-authored-typo-inputs.md)
were replayed as complete current-product JVM controller/editor sessions.
Inputs contain no expected labels; the deterministic target is the original
written word. Two runs produced byte-identical observations.

Seven of 19 final words were changed to the original target, 12 stayed as the
mutated input, and none produced another output. Seven automatic edits were
followed by exact handled Undo; no prefix or case-only changes occurred. All
observed input and output stage contexts were already registered before replay.
Examples left unchanged include `молоо` (target `молоко`) and `мето` (target
`метро`). Other mutations, such as `пакт` from `пакет` and `кара` from `карта`,
are valid alternative words, so treating all unchanged forms as errors would be
unjustified. This synthetic, disclosed set is not a natural accuracy estimate.

The [receipt](2026-10-29-q5-authored-typo-replay-evidence.json) binds the
source, inputs, current registries, actual controller sources, model assets and
JVM inputs; no external model was invoked. The evaluator test covers case and
prefix flags, session continuity and a failing Undo. The runner refuses any
future output context that has not been registered. Real-device behavior,
independent natural data and the Q5 labelled baseline remain open.
