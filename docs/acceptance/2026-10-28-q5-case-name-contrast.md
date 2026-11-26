# Q5 canonical-case overlay: name and place contrasts

The blanket lowercase-evidence overlay is **rejected as a production candidate**.
For 21 title-case occurrences extracted from 13 already-excluded Russian
Wikipedia articles, the current-product host replay reproduced the source
capitalization in 21 cases after receiving a lowercased target. The overlay
reproduced it in **zero**; all 21 boundary outputs changed. These contexts
include personal names and place names, with target forms `ника`, `моника`,
`майн` and `марсе`. The 21 rows are clustered by 13 articles, not independent
samples. They show a concrete tradeoff that the earlier unlabeled parity data
and five common-word cases did not expose.

The original source spelling is a useful contrast, not proof of what a user
would want Rune to do after deliberately typing lowercase. The prefix is a
short, lowercased fragment of a public article; it may omit wider context. This
post-hoc and previously exposed sample is not a fresh qualification set or a
population estimate. Some names or terms can themselves be ambiguous.

The [reproducible extractor](../../tools/typing_experiments/build_case_name_contrasts.py)
uses the hash-pinned Wikipedia snapshot, previously generated lowercase-evidence
screen and permanent ledger. It reads only articles whose identities are already
excluded, excludes hyphen/apostrophe fragments and sentence-initial words, and
emits opaque replay IDs. Two extractions matched byte for byte. The small
[public derived corpus](../../tools/typing_experiments/chat_regression/case-name-contrast-v1/rows.jsonl),
manifest and attribution notice are tracked; article IDs provide attribution and
provenance. Two extractor tests and four candidate-runner tests pass.

The runner version used for this experiment is retained at commit `97cf293`.
Both baseline and overlay replays used current source identities and the same
21 inputs. The [receipt](2026-10-28-q5-case-name-contrast.json) binds the rows,
source manifest, generator, runner, harness and outputs. Full logs and source
bindings remain locally in ignored `build/q5-case-name-*`. An initial exploratory
scan was manually interrupted because it needlessly scanned large prefixes for
all words; the bounded extractor was used for both final runs. No production
asset, policy, APK or phone changed. A future approach needs context-sensitive
contrast controls, wider regressions and independent qualification.
