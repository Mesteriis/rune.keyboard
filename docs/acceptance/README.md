# Acceptance evidence

The acceptance reports in this directory record the fixed inputs, commands,
digests, measured outcomes, and release decisions for Rune Smart Typing 0.3.

The current consolidated report is [Rune 0.3.2](2026-09-12-rune-0.3.2-autocorrection.md).
Earlier source-bound qualification and emulator matrices apply only to their
recorded commits and artifacts; they are historical evidence, not a fresh 0.3.2 pass.

Generated command output is intentionally not versioned. Directories named
`results/` under `tools/` contain rerunnable logs, score rows, archives, and
device receipts; they are ignored to keep the source reviewable and to avoid
committing transient build evidence. Run the command recorded by the relevant
report to recreate an evidence directory locally. The shipped source includes
the evaluator, fixed corpora, model identity, lexicon provenance, tests, and
the summarized acceptance results.
