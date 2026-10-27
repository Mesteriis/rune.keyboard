# Versioned public corpus preparation behind both registries

The new spelling and control entry points finalize **source-extracted proposal
files**. They do not rewrite historical generators or perform extraction,
morphological labeling, source-publication verification, model training or quality
qualification. Upstream source/label audits remain required. Their independent
sourceLabelsQualified/modelQualityQualified flags are false even after exclusion
checks. Input manifests' public/frozen flags are declarations bound by hash, not
proof of public origin or correct labels.

```sh
python3 tools/typing_experiments/prepare_public_spelling_v1.py \
  --rows build/proposals/rows.jsonl --source-manifest build/proposals/manifest.json \
  --output build/new-spelling
python3 tools/typing_experiments/prepare_public_controls_v1.py --kind punctuation \
  --rows build/proposals/rows.jsonl --source-manifest build/proposals/manifest.json \
  --output build/new-punctuation
# --kind protected uses the same mandatory gates.
```

Both load `holdout-ledger.json` and `control-ledger.json` by default; explicit
registry paths are supported for reproducible pinned inputs. There is no ignore,
allow-incomplete or skip-registry option. A proposal manifest must declare
containsPersonalMessages=false and frozenBeforeScoring=true and bind the actual
JSONL file hash under files[filename]. Row IDs must be unique and nonempty.
Existing output paths are rejected. Input bytes and registry bytes are captured
before output, avoiding mutable-input receipt drift.

Canonical RU spelling proposals need language, article, families (pinned canonical
target analyses from upstream), contextHash, prefix, typed and expectedSpelling.
Punctuation proposals need language, article, prefix, currentWord, expectedBoundary,
task=punctuation and noAuto=true; RU proposals also need canonical families and
contextHash. Protected authored proposals need language, prefix, typed,
cohort=protected, noAuto=true, expectedCandidate=0 and unchanged first candidate.
They do not receive invented article IDs or canonical lemmas. Source-backed
foreign control proposals remain blocked by incomplete foreign lexical history.

The shared preflight checks every applicable lexical article/window/context key,
canonical family profile, both control context kinds and language-qualified
punctuation article keys. Both actual typed and expected target controls are
checked, so changing the requested builder task cannot hide protected exposure.
Punctuation boundary relabeling cannot hide a disclosed context. Canonical
metadata is assumed source-extracted; this layer does not certify its correctness.
new-sentences excludes supervised families; new-families excludes all historical
families. These retain the original lexical protocol semantics.

Reports aggregate overlap counts from both registries and schema errors before
making a decision. BLOCKED_OVERLAP, BLOCKED_IDENTITIES and BLOCKED_COVERAGE exit
with code 2 and create no output corpus. If the original manifest/hash is invalid,
the command fails before preflight. A future validated complete registry protocol
would be required for READY_TO_FREEZE; current control schema deliberately
certifies no completeness. Current incomplete real registries therefore prevent
all final publication. No successful fresh corpus build is claimed or tested.

The finalizer code preserves source/input registries, manifest and rows as immutable
snapshots if a future approved protocol permits freezing, and binds builder source
hashes. This is still separate from label/cohort/model acceptance. Current checks
prove blocked publication and both-registry enforcement, including a real
punctuation article missing from lexical history, real supervised family exposure,
a protected fixture, and an explicitly artificial unseen-identity coverage probe.
