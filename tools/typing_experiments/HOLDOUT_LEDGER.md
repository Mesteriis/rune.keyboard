# Durable public corpus exclusions

`holdout-ledger.json` stores sorted, domain-separated SHA-256 identity keys and
source/corpus bindings. It does not store sentence text, predictions or model
scores. Hashes of public words/contexts are not anonymization of private data.
Only the explicitly pinned public inputs in the snapshot importer are included.
The importer uses Python 3.11+ and the standard library only.

The initial snapshot contains six historical Wikipedia spelling corpora v7–v12,
the current right-context calibration and reserved holdout, and 42 supervised
right-context families. Historical spelling rows provide typo-independent
context/target identity. A separate verified recovery now adds all matching
article IDs and current source-window hashes; legacy family strings still do
not certify Pymorph lemmas. Their missing family axis is recorded explicitly.

The v7-v12 recovery found 9,505 historical articles. The subsequent v6 import
adds 1,583 articles, for 11,088 across v6-v12. Together they overlap 122 articles
in the current v6 calibration and 131 in its reserved holdout. These corpora
cannot certify independence from historical spelling articles. The earlier
97/115 counts describe v7-v12 only. Existing rows and scores are unchanged;
reserved means unscored, not independently fresh. The ledger records this
finding and its exact corpus scope in `historicalArticleOverlap`.

**Coverage is incomplete.** Known overlap is rejected as `LEDGER_OVERLAP`.
An otherwise disjoint freshness check fails as `LEDGER_INCOMPLETE` until historical
canonical-family recovery and remaining corpus imports are finished.
`--validate-only` verifies schema and reports coverage; it does not certify fresh
qualification data. Ordinary CI runs this validation and dependency-free tests.

```sh
python3 tools/typing_experiments/holdout_ledger.py --validate-only
python3 -m unittest discover -s tools/typing_experiments -p 'test_*holdout_ledger.py'
python3 -m unittest discover -s tools/typing_experiments -p test_conversation_split_checks.py
python3 -m unittest discover -s tools/typing_experiments -p 'test_legacy_holdout_*.py'
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

That command rebuilds the **bootstrap**, not the enriched current ledger. Then
recover v7 through v12 from their pinned public Parquet files, always supplying
the bootstrap explicitly (rather than requiring earlier recovery receipts):

```sh
python3 tools/typing_experiments/recover_legacy_holdout.py --version 7 \
  --parquet build/typing-ranker-v2/ru-0012.parquet \
  --ledger build/rebuilt-ledger.json --output build/recovery/v7
# Repeat for versions 8..12: shard number is version + 5, output v8..v12.
python3 tools/typing_experiments/merge_legacy_holdout_recovery.py \
  --base build/rebuilt-ledger.json --recovery-root build/recovery \
  --output build/enriched-ledger.json
```

Scanning requires PyArrow and the original public source files; unit tests do
not. The archived selector bytes are hash-checked before loading. The old
selection hash omits article ID, so every matching article and occurrence is
retained. Recovery verifies selector parity, all row identities and exact input
hashes without calling models. Source-window keys use the current 256-character
prefix input / 128-character suffix projection, not a full-sentence identity.
Article exclusions cover the entire source article. The merge only adds keys
and preserves previous source bindings; it cannot certify complete coverage.

Remaining work is listed in the snapshot's `coverage.pending`. Recover historical
canonical family identities from pinned public data and existing receipts;
do not invent missing IDs or relabel legacy word families as canonical lemmas.
Preserve remaining original generator bytes before introducing
versioned replacements. Import other joint/context/conversation public histories
with source-specific adapters and verified privacy/provenance, then wire the
complete registry into new preparation entry points. Do not mark Q6 complete
based on this bootstrap or a schema-only CI pass.

Dictionary-only legacy family recovery is a separate append-only addendum with
usage `historical-family-exclusion`. It stores the union of all dictionary
analyses, including ambiguous words, without guessing unknown lemmas. The six
parent entries retain their missing family axis. The current addendum covers
9,563 of 10,200 rows (6,975 distinct lemmas); 637 unresolved row IDs remain in its
receipt. This usage is family-only, is included by `new-families`, and does not
turn historical evaluation into supervised training for `new-sentences`.

```sh
python3 tools/typing_experiments/recover_legacy_families.py \
  --base build/enriched-ledger.json --output build/legacy-family-recovery
python3 -m unittest discover -s tools/typing_experiments -p test_legacy_family_recovery.py
```

Extraction requires the pinned dictionary packages from `tools/morphology/ranker.py`;
its receipt hashes installed package code/data. Reading the resulting exclusion
keys and running the unit tests requires only the standard library. The importer
rejects changed corpus bindings, missing targets, duplicate row IDs and repeated
addendum import; it does not update old rows or clear pending coverage.

The pinned `typing-ranker-v2/data` history is imported with
`import_ranker_history.py --base LEDGER --output NEW_DIRECTORY`. It verifies its
fixed manifest hash, every row/text file and the original public Parquet hash.
All 1,158 declared text-partition articles are excluded, including articles with
no selected typo row. The 7,500 target rows are checked against partition/article
metadata. Dictionary-supported training target families are `supervised`;
dev/test families remain historical. The single unknown training target keeps
its parent family axis pending. Source-window/context recovery remains pending;
full-article exclusions already block new sentences from these sources.

`import_joint_history.py --base LEDGER --output NEW_DIRECTORY` imports the
original public joint corpus and both preserved follow-up corpora. It pins all
three manifests and four public Parquet hashes, verifies every row-file hash,
and checks article membership against the source Parquet ID column. Source locks
must identify the pinned Wikipedia revision. Native numeric family IDs are
never used as Pymorph lemmas. All typo variants contribute the same normalized
target/context exclusion; all dictionary target analyses are retained separately.
The training family addendum is supervised; calibration/holdout addenda are
historical because those sets have already been used. No scoring is performed.
The importer requires PyArrow plus pinned morphology; its unit tests do not.

`import_spelling_v6.py --base LEDGER --output build/NEW_DIRECTORY` recovers the
older public spelling-v6 corpus from its pinned manifest/source and archived
original selector. It retains all matching source articles/occurrences, projected
windows, contexts and dictionary-supported families. The separate v6 prepare
builder is also archived at its original hash. Existing entries remain unchanged;
the historical spelling overlap summary is expanded to v6-v12. The 110 unknown
v6 lexical targets remain pending. Use `audit_family_coverage.py --ledger LEDGER
--output NEW_RECEIPT` to distinguish lexical dictionary gaps from exact protected
control construction; this audit never guesses lemmas or changes the ledger.

`import_early_ru_history.py --base LEDGER --output NEW_DIRECTORY` imports only
RU spelling components of qualification-v2 and compact-v3/v4. Each contributes
3,400 persisted target/context identities plus partial dictionary family addenda.
Pinned manifests, RU row files and public Parquet hashes are verified. Exact
original qualification generators v2/v3/v4 are archived and checked, not executed.
The v3/v4 sources were recovered from local Git at their original manifest hashes.
Article/window recovery, punctuation/protected-token components and other languages
remain pending. EN/ES cannot be silently imported into the current RU namespaces.

Early RU source recovery is now a separate append-only migration:

```sh
python3 tools/typing_experiments/recover_early_ru_sources.py --corpus qualification-v2 \
  --base LEDGER --output build/recovery/qualification-v2
# Repeat for compact-v3 and compact-v4 into build/recovery/<corpus>.
python3 tools/typing_experiments/merge_early_ru_sources.py --base LEDGER \
  --recovery-root build/recovery --output build/enriched-early-ledger.json
```

Exact source locks v2-v4 were restored from Git and archived. Recovery checks the
original seed and article hash/modulus filter, normalizes only the split-template
wrapper in copied rows, and verifies original selector parity. V2 uses the literal
3042026 in its archived builder; v3/v4 use their source locks' corpusSeed. All
matching eligible articles/occurrences are retained. The merge preserves previous
keys/bindings and family gaps. It adds 6,875 articles, expanding registered spelling
history to 17,963 articles across ten component entries; current 122/131 overlap
counts are unchanged. Window hashes are projections, not full-sentence identities.
Punctuation/protected components and EN/ES remain pending. CLI scans need PyArrow;
reading keys and running the unit tests do not.

New versioned proposal finalizers now enforce lexical and control exclusions
together, including language-qualified punctuation articles. See
[PUBLIC_CORPUS_PREPARATION_V1.md](PUBLIC_CORPUS_PREPARATION_V1.md). The old hash-bound
builders remain unchanged. Current incomplete coverage rejects final publication;
source/label/model qualification is separate.

`import_natural_context_history.py` adds the seven pinned historical public
Wikipedia availability pools (1,204 contexts). Every prefix/target/right-context
capture is checked against its original Parquet article, and source-window
hashes are recomputed. Both target and rival dictionary analyses are excluded;
all are dictionary-supported in these pools, so their four lexical axes are
complete. This does not complete global history coverage. The exact original
collectors are archived without executing their model/file-writing top levels.
Their remaining runtime/dependent inputs are not claimed reproducible here.
