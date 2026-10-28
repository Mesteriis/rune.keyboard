# Acceptance evidence

The acceptance reports in this directory record the fixed inputs, commands,
digests, measured outcomes, and release decisions for Rune Smart Typing 0.3.

The working-tree status is recorded in the
[review completion map](../plans/2026-10-27-review-completion.md). Individual
reports bind a particular source commit, artifacts, inputs and measured scope.
A local or narrow device pass does not establish a new release or distribution
acceptance.

Current scoped references include [learning-data consent](2026-10-28-q2-learning-privacy.md),
[source cascade and asset notices](2026-10-28-q2-source-cascade-notices.md), and
[actual Chrome editor checks](2026-10-28-q8-chrome-editor.md).
The [Rune 0.3.2 report](2026-09-12-rune-0.3.2-autocorrection.md) and earlier
qualification/emulator matrices remain historical evidence for their recorded
commits and artifacts.

Generated command output is intentionally not versioned. Directories named
`results/` under `tools/` contain rerunnable logs, score rows, archives, and
device receipts; they are ignored to keep the source reviewable and to avoid
committing transient build evidence. Run the command recorded by the relevant
report to recreate an evidence directory locally. Versioned commands and input manifests are identified by each scoped receipt.
Source availability, successful execution, fresh qualification and distribution
acceptance are separate requirements; outstanding items remain in the review map.
