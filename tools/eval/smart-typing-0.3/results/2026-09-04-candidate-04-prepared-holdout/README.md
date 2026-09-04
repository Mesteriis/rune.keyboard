# Candidate 04 prepared-candidate holdout

Result: **PASS** for prepared-candidate suitability. All 13,200 corpus rows have one identity-bound score record. Calibration completed first and froze config `b7e07c54e76e961efd9e33e28c6b9be066167b1dace4e2e815b2fc472682ed69` before the first holdout request. The model, runner, corpus and thresholds did not change during holdout.

RU, EN and ES each satisfy the required replacement volume, observed precision and false-change row gates. This permits the exact candidate digest to enter production-candidate calibration and holdout; it does not qualify production AutoReplace, Android performance, Fold behavior, energy use, publication or release.

The GGUF and native runner are not included. `scores.jsonl.gz` uses deterministic gzip metadata and expands to the cache digest recorded in `provenance.json`.
