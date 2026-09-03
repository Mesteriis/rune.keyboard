# Production candidate calibration export

This host-only tool runs the current production `CandidateGenerator` and
`PackedCandidateLexicon`, including membership, protection, language routing,
weighted edit features and the shared 8192-state/64-terminal limits. It uses
the existing frozen packed lexicons, whose complete bytes/structure are checked
by the production loader before execution. No model or Android editor is used.

The exact existing corpus files are hash-checked and validated. Only the 6,000
calibration spelling rows reach the generator; its input contains a numeric
row index, language and typed token. Prepared candidate sets, expected answers,
labels and context never reach generation. It exports original plus up to seven
actual alternatives and features. `--maximum-alternatives` fixes the requested
limit (1–7, default7) before execution using the production constructor. The
receipt records that limit; it cannot be lowered after a search exhausts its budget. Missing expected words stay missing. Partial
search results keep their AutoReplace veto. Results are not confidence estimates
or an AutoReplace policy.

Run from the repository with Python 3.11+, JDK17 and the existing hash-pinned Kotlin compiler
cache. Index/rank arguments identify pre-existing caches with the frozen bytes;
replace the example paths if the cache layout differs. No download occurs.

```sh
python3 tools/eval/smart-typing-0.3/pipeline/export_calibration.py \
  --output build/smart-typing-0.3/pipeline-calibration-01 \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
python3 -m unittest discover -s tools/eval/smart-typing-0.3/pipeline -p 'test_*.py'
```

The output must be a fresh directory under repository `build/`. It contains
public synthetic inputs and candidate text, compiled harness, raw protocol,
JSONL candidates, summary and provenance. Source and asset hashes are rechecked
after execution. Failed stages preserve evidence and do not produce successful
provenance. Compilation uses two host processors/768 MiB and a 120-second timeout;
generation uses the same process limits and a 600-second timeout. Neither time
nor memory setting is an Android performance measurement.

`summary.json` describes candidate recall and retrieval completion only. It
reports row and unique-token counts because the original prepared corpus has
candidate-set-sensitivity repeats that become identical generator inputs. Those
rows must not be described as independent typing observations. No confidence
threshold, quality PASS, Wilson precision interval or AutoReplace count follows
from this export. The calibrated decision layer and final holdout report remain
separate work. This tool has no holdout execution option; adding that phase must
require a frozen calibration configuration and preserve the earlier model report.

The output text is permitted only because these are checked-in public authored
fixtures. This developer harness is not packaged in the APK and is never an IME
logging/export path.
