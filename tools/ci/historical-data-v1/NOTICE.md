# Original public historical test data

Host-side regression fixtures only; not packaged in the Android application.
The two original manifests and every file they advertise are preserved byte for
byte. No new training, qualification or model selection is performed.

Source: Wikimedia contributors, Russian Wikipedia snapshot 20231101, distributed
as wikimedia/wikipedia, parquet conversion revision
`a634f78b1c435397c07001e175fa74cc4ad5e775`, `20231101.ru/train/0007.parquet`.
Dataset: https://huggingface.co/datasets/wikimedia/wikipedia
Each consumed article is credited by title and a contributor-history link in
`articles.jsonl`; the retained article IDs also appear in the original manifests.
Source texts were normalized/tokenized, truncated and combined with synthetic
spelling errors by the two hash-bound preparation scripts. These changes are
covered by the original source terms, not by the repository code license.

The pinned dataset notice records CC-BY-SA-3.0 and GFDL-1.3, with some text
available only under Creative Commons. Use this text collection under
Creative Commons Attribution-ShareAlike 3.0:
https://creativecommons.org/licenses/by-sa/3.0/
Legal terms: https://creativecommons.org/licenses/by-sa/3.0/legalcode
See also `tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md` and `source-lock.json`.
Historical generators and vocabulary provenance remain bound in each manifest.
The archive includes derived examples, not the source frequency list.

These articles are permanently excluded from fresh qualification by the durable
holdout ledger. Missing canonical-family/full-sentence provenance remains open.
