# Durable public corpus exclusions

`holdout-ledger.json` stores sorted, domain-separated SHA-256 identity keys and
source/corpus bindings. It does not store sentence text, predictions or model
scores. Hashes of public words/contexts are not anonymization of private data.
Only the explicitly pinned public inputs in the snapshot importer are included.
The importer uses Python 3.11+ and the standard library only.

The initial snapshot contains six historical Wikipedia spelling corpora v7–v12,
the current right-context calibration and reserved holdout, and 42 supervised
right-context families. Historical spelling rows provide typo-independent
context/target identity, but lack article IDs and do not certify their family
strings as Pymorph lemmas. Their missing axes are recorded explicitly.

**Coverage is incomplete.** Known overlap is rejected as `LEDGER_OVERLAP`.
An otherwise disjoint freshness check fails as `LEDGER_INCOMPLETE` until historical
article/sentence/family recovery and remaining corpus imports are finished.
`--validate-only` verifies schema and reports coverage; it does not certify fresh
qualification data. Ordinary CI runs this validation and dependency-free tests.

```sh
python3 tools/typing_experiments/holdout_ledger.py --validate-only
python3 -m unittest discover -s tools/typing_experiments -p 'test_*holdout_ledger.py'
python3 -m unittest discover -s tools/typing_experiments -p test_conversation_split_checks.py
```

Future public Wikipedia sentence corpora use the same standardized row fields
as the current right-context corpus: `article` (decimal Wikipedia ID), `families`
(pinned Russian Pymorph lemmas), `contextHash` (existing source-context hash),
`prefix`, `typed`, `expectedSpelling`.

```sh
python3 tools/typing_experiments/holdout_ledger.py --rows new-corpus.jsonl --profile new-sentences
```

The `new-sentences` protocol excludes every recorded article, sentence/context
and supervised family, while allowing previously evaluated families in new
sentences. The `new-families` profile additionally excludes all recorded family
identities. Missing identity fields fail rather than being skipped. This checker
does not replace source/label correctness audits, minimum cohort sizes or quality
qualification. Existing frozen generators and old qualification contracts are
unchanged; do not silently add new checks into hash-bound historical scripts.

The deterministic bootstrap importer reads original frozen corpus manifests,
their row hashes and the current receipt chain. It never overwrites a snapshot:

```sh
python3 tools/typing_experiments/snapshot_public_holdout_ledger.py --output build/rebuilt-ledger.json
```

Rebuilding requires the preserved original corpora. Reading the committed ledger
and rejecting overlaps does not require `build/`, PyArrow, Pymorph, CatBoost,
Java, a model or a phone. A rebuild does not replay models or inspect holdout
predictions. Reserved holdout stays reserved; inclusion in an exclusion ledger
does not mean it has been scored.

Remaining work is listed in the snapshot's `coverage.pending`. Recover historical
article/selection identities from pinned public data and existing receipts;
do not invent missing IDs or relabel legacy word families as canonical lemmas.
Preserve original generator bytes for each recorded SHA before introducing
versioned replacements. Import other joint/context/conversation public histories
with source-specific adapters and verified privacy/provenance, then wire the
complete registry into new preparation entry points. Do not mark Q6 complete
based on this bootstrap or a schema-only CI pass.
