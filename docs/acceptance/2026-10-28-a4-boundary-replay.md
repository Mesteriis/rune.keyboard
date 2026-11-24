# A4: boundary selection in current-product replay

The current-product replay now accepts `space`, `period` and `colon`, with
space as the unchanged default. The selected boundary reaches the actual Kotlin
controller; non-space observations identify the boundary and compare the editor
text against its insertion. Other historical modes reject non-space selection.
At this checkpoint the legacy stress analyzer was space-only; its later extension
is described below.

On the five review examples in `2026-10-28-a4-space-discovery.md`, all 15
boundary cases retained the original token and Backspace restored the pre-boundary
text. In a separate positive probe, `смотруть` became `смотреть` at each of the
three boundaries and Backspace restored `смотруть`. Each boundary invocation
ran twice and passed the full non-timing projection comparison. These six named
inputs are discovery probes, not the requested category corpus or fresh holdout.

The final code passed the actual Q7 CI gate locally: 2,160 disclosed inputs and
12,000 historical inputs, each replayed twice with the default space, matched
their respective existing baselines. The focused Python suite ran six tests with
no failures. Raw results are under `build/review-a4-final-{space,period,colon}-20261028`,
`build/review-a4-positive-{space,period,colon}-20261028`, and
`build/review-a4-final-parity-20261028{,-historical}`. Receipts bind the assets,
sources, inputs and toolchain. Replay harness SHA-256:
`db26501da46400ef1337df06b000c54b05d73425a2f94aa511f5df691b2d8006`;
driver SHA-256:
`78c65882357df56e55cff6c2ee7d0bb4b6394cb395abb241ec738ca690ea38b8`.

Still required: a 100–200-item categorized control corpus and reporting gate,
including IDN and case controls,
and protected abbreviation, useful correction and exact Undo on Fold. These
host observations do not establish physical-editor behavior or close A4.

## Analyzer extension

`local_spelling_stress.py report` accepts the same three boundary names and can
consume the host-only current-product identity mapping. It checks mapping order,
opaque IDs and source IDs before associating labels with observations. For
punctuation it verifies the observed boundary, change flag, actual Backspace text
and restoration flag; historical space output remains unchanged. Reports retain
the supplied row, observation and mapping hashes and are descriptive, not
qualification verdicts.

The real observations above were analyzed successfully for all three boundaries:
five controls yielded zero changes per boundary and the positive example yielded
one intended correction with no Undo failure per boundary. Raw labeled inputs
and reports are in `build/review-a4-{discovery,positive}-labeled-20261028.jsonl`
and `build/review-a4-{report,positive-report}-{space,period,colon}-20261028.json`.
The local stress suite passed 18 tests, including corrupted boundary, change and
Undo fields and invalid identity maps; the shared slice suite passed eight.
