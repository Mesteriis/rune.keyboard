# Q5: natural-error source screen

The [dataset card at revision `5d488562e6d5f6cc165b3178184a8fdea9dd8b5e`](https://huggingface.co/datasets/inkoziev/spellchecker/blob/5d488562e6d5f6cc165b3178184a8fdea9dd8b5e/README.md)
declares MIT licensing and says its hand-selected test split contains errors made
by people; it distinguishes that split from synthetic training data. It also
says samples may contain multiple errors and sensitive or offensive material.
The card does not provide per-entry author identities, source permissions or
proof that its corrections are sufficient for this keyboard's labels.

The revision's `test.json` was fetched twice into memory, without executing a
source loader. Both HTTP requests returned 200 and the same 2,198,952 bytes,
SHA-256 `de379e36e40ea8e3c2525ce081a7cbcddeabe0de6641fe6286436d451ca59478`.
The JSON array contains 6,244 rows and 6,244 distinct IDs. Its documented
fields are `id`, `sentence`, `fixed_sentence`, `label`, `error_type` and
`domain`. All 6,244 rows have label 0; 5,323 have a string correction. Thus
this test file did not provide labelled acceptable-original controls for Q5.

A purely mechanical screen NFC-normalized and trimmed each text, removed only
terminal `. ! ? …`, case-folded tokens and required 2–6 whitespace-separated
Cyrillic-only words in both original and correction. Of 1,449 rows meeting that
shape, 460 had equal token counts and exactly one differing token: 330 labelled
spelling, 125 grammar, two tokenization, one punctuation and two unknown. They
contain 457 distinct original/correction pairs and 456 distinct targets. These
are source-level counts, not validated keyboard corrections or independent
cases. No row text, fingerprint, source file or model output was retained; no
model was run. The dataset-card examples themselves were visible during this
inspection and are disclosed; they must not be treated as independent holdout
material. No general source-identity registration for this corpus was added.

The source may be useful for a separate human-error diagnostic, but its target
sentences are edited material, not verified unchanged natural-chat controls.
Individual author clustering, consent, underlying text rights, annotation
quality, source overlap with all existing Rune data and calibration/holdout
independence remain unverified. Do not treat this screen or the publisher's MIT
tag alone as clearance to redistribute the underlying texts or as Q5/Q6
qualification. Nothing was imported into training, controls or registries.
