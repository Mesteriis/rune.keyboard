# Candidate 03 qualification-v3 calibration

Result: **FAIL before holdout**. The exact candidate completed all 6,600 calibration rows and froze
the conservative Wilson-95 configuration. RU and ES found eligible buckets, while EN found no bucket
that simultaneously provided at least 300 automatic replacements, a precision lower bound of 99%,
and a false-change upper bound of 0.5%. EN therefore froze to full abstention.

The untouched v3 holdout was not scored because the frozen EN configuration makes the
three-language release gate impossible. `report.json` and `report.md` were emitted with the expected
exit code 2; their holdout sections explicitly show 2,200 missing rows per language. No threshold was
changed and no product model-dependent evaluation was started.

The GGUF and native runner are not included. `scores.jsonl.gz` uses deterministic gzip metadata and
expands to the cache digest recorded in `provenance.json`.
