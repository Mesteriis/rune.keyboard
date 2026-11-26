# Corpus acceptance record

Copy this template to a dated report. Every field below requires actual evidence;
this template does not establish a passing result.

## Scope and frozen inputs

- Reviewed source commit and any uncommitted source hashes:
- Public source revision, license, attribution and extraction/filter commands:
- Exact corpus/manifest/config/model/runtime SHA-256:
- Declared split, cohorts, article/family separation and threshold-selection plan:
- Disclosed regression data versus genuinely unseen qualification data:

## Durable exclusion binding (Q6)

Keep the complete JSON report from the versioned public corpus preparation
command, including blocked reports. Record its SHA-256 here:

- Preparation report path and SHA-256:
- Actual command, exit code and `status`:
- `registryBindings.schema`: `rune-acceptance-registry-bindings-v2`
- Exact lexical ledger SHA-256 from
  `registryBindings.registries["lexical-ledger.json"].sha256`:
- Exact control ledger SHA-256 from
  `registryBindings.registries["control-ledger.json"].sha256`:
- Relevant registry name, entry ID and full canonical entry SHA-256 from
  the corresponding `entrySha256` map; include the newly consumed entry when
  registering the evaluated corpus, and bind the resulting updated ledger:
- Both registry coverage flags, unresolved history and overlap counts:
- `registryBindings.englishSurfaceBindings`: exact helper, fixture, importer
  and source-lock SHA-256 values:

The report binds **all** entries present during preparation, including their
origin bindings and metadata. Entry hashes use UTF-8 JSON with sorted object
keys, `ensure_ascii=False`, separators `(',', ':')` and `allow_nan=False`.
The ledger SHA binds the original file bytes, including formatting. Public
record hashes do not anonymize private messages; never add private messages or
their dictionary-enumerable fingerprints to public exclusions.
The v2 binding also covers the mandatory English source-surface exclusions.

To check an existing report against the current versioned registries:

```sh
PYTHONPATH=tools/typing_experiments python3 - PREPARATION_REPORT.json <<'PY'
import json
from pathlib import Path
import sys
from public_corpus_preparation_v1 import verify_registry_bindings
report = json.loads(Path(sys.argv[1]).read_text())
verify_registry_bindings(report,
    Path('tools/typing_experiments/holdout-ledger.json'),
    Path('tools/typing_experiments/control-ledger.json'))
print('Registry snapshots and entry hashes match; inspect acceptance gates separately.')
PY
```

Run from the repository root and replace `PREPARATION_REPORT.json` with the
actual report. A missing binding, added/changed/removed entry, or byte change
fails verification. If the registry legitimately advances, retain the old
receipt and create a new preparation/acceptance record; do not rewrite old proof.
Older v1 reports do not bind these exclusions. They cannot pass the current
verifier; `verify_historical_registry_bindings_v1` is available solely to
recheck their two historical ledger snapshots without a surface-coverage claim.
Matching hashes prove identity only. Incomplete coverage, overlap, missing
identities or failed quality gates cannot be promoted to a passing acceptance.

## Executed acceptance

- Exact commands and actual exit codes; explicit skipped/unrun checks:
- Per-language/cohort replacements, correct replacements and false changes:
- Point precision, descriptive intervals, control coverage and exact Undo:
- Baseline comparison and original-candidate retention:
- JVM versus real editor/device evidence and measured latency/memory:
- Outcome, failed gates, remaining limitations and promotion decision:
