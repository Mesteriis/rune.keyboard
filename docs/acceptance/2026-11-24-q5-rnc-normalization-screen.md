# Q5 RNC social-media normalization screen

The publishers selected examples likely to contain nonstandard spellings
from public Telegram and VK material and removed punctuation. Their
annotation also expands abbreviations, normalizes some informal spellings
and preserves some ambiguous spellings. They report inconsistencies in
capitalization after punctuation removal. An unchanged annotation cannot
establish that a phrase is an independently proofread control, and the
distribution declares CC BY-NC-SA 4.0.
[Original paper](https://www.injoit.org/index.php/j1/article/download/2355/2027)
[Dataset card and license](https://huggingface.co/datasets/ruscorpora/normalization)

Two runs of [the aggregate-only screen](../../tools/typing_experiments/screen_rnc_normalization.py)
read the pinned release and produced byte-identical output. The source is
764,416 bytes and has SHA-256
`fe2d977dfc95a0dbaf1b4015c02d2c6d4726b68400a00e5b4b8357cca2264461`.
A short phrase contains 2–6 words of Russian Cyrillic. Case folding is
applied for the character filter and comparisons that explicitly require it.
[Pinned JSON release](https://huggingface.co/datasets/ruscorpora/normalization/resolve/8fc9c1665e17a8d6e0267000055aba43f19f8a48/data.json)

| Measure | Count |
| --- | ---: |
| Parallel source and annotation rows | 1,930 |
| Identical source and annotation, all lengths | 967 |
| Short Cyrillic inputs | 1,018 |
| Short Cyrillic inputs unchanged with original case | 586 |
| Short unchanged inputs already in lowercase | 6 |
| Short inputs unchanged after case folding | 713 |
| Distinct short inputs unchanged after case folding | 712 |
| Short pairs with one changed token after case folding | 159 |
| Of those, pairs with only the final token changed | 59 |
| Exact matches from the existing orthographic generator | 15 |
| Exact matches from that generator for final-token edits | 5 |

The generator matches eight `о/а` cases, three reflexive-suffix cases, two
sign deletions and two `е/и` cases among the 159 pairs. Thirty of those
159 pairs change only `е/ё`. These counts measure coverage of the
deterministic corpus generator on this selection. The study also labels
stylistic normalizations, so the counts do not estimate typo frequency or
Rune's correction accuracy. The screen retained zero messages, fingerprints
and identifiers, and made zero model calls.

The corpus falls below Q5's 3,840 controls even before author clustering.
For illustration, with 712 independent controls and zero changes, the
95% Wilson upper bound would be 5.37 per 1,000. This is a hypothetical
limit. The release exposes token pairs without author or conversation IDs.
The forum dataset `ruforum` declares CC0 but lists message ID, timestamp
and text as its only fields. Its card supplies no spelling labels or
author clusters and does not establish rights from the original posters.
This check used the forum dataset card and downloaded no dataset payload.
[Forum dataset card](https://huggingface.co/datasets/nyuuzyou/ruforum)
