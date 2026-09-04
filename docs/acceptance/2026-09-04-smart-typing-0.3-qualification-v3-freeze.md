# Smart Typing 0.3 qualification-v3 freeze — 2026-09-04

The third prepared-candidate qualification corpus is frozen before scoring at manifest SHA-256
`56a5b994bc2048c4cf434a123ebbe2e2f7a746102b936a83d535fc582ceecee3`. It contains 13,200 rows:
for every EN/RU/ES split, 1,000 typos, 1,000 correct/protected negatives and 200 punctuation rows.
Original is present in every candidate set. Calibration and holdout have 5,790 distinct families each
and no family/template overlap.

Inputs are previously unused Wikipedia 20231101 shards `en-0030`, `es-0005` and `ru-0010` at pinned
parquet revision `a634f78b…`; exact sizes and SHA-256 values are in `source-lock.json`. Their repository
paths do not overlap the model-training shards or qualification-v2. The generator additionally excludes
every family from train/validation, the original evaluation corpus and the revealed v2 corpus before
selection. The manifest records actual scanned/selected article counts and the hashes of all generator,
evaluator, training and prior-corpus inputs.

The evaluator now accepts one internally consistent corpus version 2 or 3 and rejects mixed versions.
The default calibration rule remains the already committed conservative Wilson-95 rule. Tests pass:
common evaluator 28/28 and v3 generator/lock 5/5. No v3 scoring occurred before this freeze; both v3
calibration and holdout are untouched at this checkpoint.
