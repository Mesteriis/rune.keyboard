# Q6: reproduce the early ranker corpus and recover target windows

Re-ran the original tracked prepare_refinement.py, whose bytes still match the
historical preparationScriptSha256. It read the pinned public RU Wikipedia shard
0007 and frequency vocabulary. The regenerated manifest and all six JSONL files
(train/dev/test target rows and text exposures) match the originals byte for byte.
This establishes reproducibility of these corpus files; it does not reproduce
training, binary assets or model outcomes.

Recovered the source captures for all 7,500 target rows: 5,000 train, 1,000 dev,
1,500 test. Recovery preserves the original sentence-local selection identity,
prefix truncation, Cyrillic regex and whitespace requirement. All matching
occurrences are retained. Capture hashes use the established projected
prefix/word/128-character suffix identity; they are windows, not full sentences.
Repeated or short captures can share a hash. The three partitions have
5,010/998/1,498 window keys and 4,999/999/1,500 normalized context keys.

Added three durable window entries. Existing 82 entries remain unchanged,
including exclusions for all text-exposure articles, even those without target
rows, and their supervised/historical dictionary-family addenda. New window
entries deliberately keep the family axis incomplete: this step proves source
capture, not canonical families for previously unresolved targets. No additional
article overlap with the current v6 calibration/holdout is introduced.

The new recovery command requires a manifest and all six reproduced files to
match their pinned originals before emitting an updated ledger. Source and
producer hashes and parent ledger bindings must also match. Output must be a
fresh directory. Original preparation and historical corpus files are unchanged.

All 151 tests pass in a fresh source-only directory without build corpora,
models, PyArrow or morphology packages; both ledger schemas validate and retain
incomplete coverage. Five new recovery tests cover repeated captures, original
mixed-script token boundaries, changed/missing source identity, cross-source
context reuse and reproduction tampering; the durable snapshot test also checks
a real recovered context. Two initial fixture assumptions were corrected after
the first five-test run failed: short captures can have the same full-window
hash, and a hyphen-ended prefix violates the producer whitespace requirement.
Final checks and original exit codes are recorded in the adjacent evidence JSON.
CI includes the new tests; no remote CI execution is claimed.

This closes the missing target-window/context exclusions for this early ranker
corpus. Global Q6 coverage remains incomplete: unresolved families, other
historical source/generator chains and owner-authored provenance still require
work. No fitting, scoring, APK update or device operation was performed.
