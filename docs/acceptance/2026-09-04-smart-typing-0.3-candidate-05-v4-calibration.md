# Candidate 05 qualification-v4 calibration — 2026-09-04

Exact GGUF SHA-256 `26b6e8db369b2f9e9fa8759c8682532f5bd6f84900499aa74e1733ad5bc1f7bd`
and exact runner SHA-256 `f2f8e9e21a028871da4b9ced6ce0492eb692f742c4de765467a2d44a18535973`
completed all 6,600 calibration requests. The cache has one identity header plus 6,600 numeric
responses. No v4 holdout request preceded either frozen configuration.

The default conservative Wilson-95 selector qualified RU 467/467 and EN 679/679 with zero false
changes, but froze ES to full abstention. That profile therefore failed the three-language volume
gate and was not used for holdout.

The user selected a 95% point-precision product profile. The pre-existing point-estimate selector
was exposed as an explicit CLI choice and bound into the immutable config. It froze margin 1.0 and
confidence feature 0.8 for every language:

| Language | Auto | Correct | Precision | False changes |
| --- | ---: | ---: | ---: | ---: |
| RU | 633 | 628 | 99.21% | 5/1,000 (0.5%) |
| EN | 707 | 706 | 99.86% | 1/1,000 (0.1%) |
| ES | 671 | 668 | 99.55% | 3/1,000 (0.3%) |

The frozen file SHA-256 is `a2b737f8280bc3eadb3fe9523cb82ca9f49482a907161e9b56d4fce7ee9d224f`;
its internal config SHA-256 is `48802ac0f8fb72af501268b7cd7fa5c9d2a00874b0fa0b1f9f91f6c918a464b7`.
The evaluator retains 99% and Wilson-95 as historical defaults, records non-default precision and
selector choices, and recomputes them before allowing holdout scoring. Evaluator tests pass 28/28.

This is a calibration PASS only. The untouched v4 holdout, production candidate pipeline, physical
model behavior, performance/energy and publication remain open.
