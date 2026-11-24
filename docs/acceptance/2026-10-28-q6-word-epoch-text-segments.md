# Q6: archived word and epoch text payloads

In addition to the historical target occurrences, the verified archives retain
630 public text records. Their exact text payloads were segmented with the
historical delimiter and added as normalized hashes to the exclusion ledger:

| Partition | Archived text records | Manifest article identities | Distinct segment hashes |
| --- | ---: | ---: | ---: |
| Additional epoch test | 200 | 230 | 200 |
| Word-ranking train | 253 | 3,717 | 253 |
| Word-ranking dev | 85 | 334 | 85 |
| Word-ranking test | 92 | 869 | 92 |

Each text record's article identity belongs to its original partition; archive
and parent identities are verified. These are the text payloads retained in the
archives, which can be truncated excerpts. They do not cover every article in
the manifests and are not certified full articles or linguistic sentences.
The original article and target-window exclusions remain necessary. The shared
normalized full-sentence namespace detects compatible exact text overlap, but
does not make a source from another namespace or an incomplete segment fresh.

`import_word_epoch_text_segments.py` stores hashes only, never source text, and
retains the incomplete global coverage status. Two independent runs produced
byte-identical output; the receipt is
`build/review-q6-word-epoch-text-segments-20261028/receipt.json`, SHA-256
`549d3b7e21d565d48df97cae9c08283be5a621dc5a477b6a3cb4ad7c5f4c6b70`.
Unit coverage checks normalization, compatible cross-source keys, duplicate and
foreign article refusal, and empty text refusal. No model was run.
The full stdlib inventory passed 755 tests across 149 modules with no skips.
