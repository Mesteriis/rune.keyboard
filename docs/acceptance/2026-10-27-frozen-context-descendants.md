# Q6: frozen natural/side descendants and remaining public families

Audited four historical corpora whose own manifests were not yet bound to the
durable registry. Their preparation scripts are now archived byte-for-byte by
hash. The scripts' top-level model/path/write operations were not executed.

| Corpus | Calibration rows / source contexts | Holdout rows / source contexts |
| --- | ---: | ---: |
| Natural frozen | 1,600 / 400 | 1,600 / 400 |
| Side | 6,050 / 1,290 | 5,810 / 1,242 |
| Fresh side v4 | 5,800 / 1,240 | 5,780 / 1,236 |
| Fresh side v5 | 5,800 / 1,240 | 5,776 / 1,235 |

The 38,216 row exposures represent 8,283 repeated context exposures and 5,808
unique source-window hashes, not independent examples. Every source word,
prefix and complete suffix was verified against the actual article in seven
previously pinned public Wikipedia assets. Natural captures additionally match
all inherited fields of their previously verified source-pool records. Manifest,
plan, payload, source-asset and preparation identities are bound in the receipt.

Verified every typo/correct/rival/protected variant and the side unfinished-word
control against its source-context parent. A changed suffix, control target or
article cannot silently retain the parent's identity. Side v5 is exactly the
order-preserving, whole-context filter of v4 using the historical authored-v5
training families and original filter helper: calibration is identical; holdout
removes one context with all four variants. No scoring result participates.
This verifies data lineage, not independent quality, selection-algorithm parity,
semantic labels or historical model-training execution.

Canonical families were rebuilt from dictionary analyses of source words and
rivals. Numeric/declared family labels, corrupted inputs and `@` controls do not
supply canonical lemmas. All candidates in these four corpora have supported
analyses. Eight entries add 640 previously unblocked family keys, 4,779 article
keys, 5,008 source-window keys and 15,000 target-context keys. Historical evaluated
families are excluded by the **new-families** profile; the existing new-sentences
profile still permits evaluated families while excluding used articles and
contexts. These data are not relabelled as supervised training.

The previous 113 entries and incomplete coverage state are unchanged; the ledger
now has 121 entries. All 19 currently present `right-context*/corpus/manifest.json`
files are bound, which is only a scoped inventory, not a claim that all historical
inputs or missing feature sources have been recovered. The separate 120-example
origin gap, unsupported surfaces, missing historical feature hashes, disclosed
old article overlap and fresh independent qualification remain open.

Validation: 202 tests and both registry schema checks pass in a fresh isolated
source-only directory without build data, models or morphology packages. The
new durable-entry test first failed against the old ledger. The real preparation
CLI rejects the recovered family under new-families with exit 2 and creates no
output. An initial CLI test incorrectly used new-sentences; correcting the test
profile preserved the intended existing policy. Eight new audit tests cover
variant mutation/order/count, exact parent filtering, pool ancestry, dictionary
recovery and all four archives. CI now runs these tests and the source-window
and training-filter helper tests; no remote CI result is claimed.

The dictionary-backed audit exits 0 with no model calls. Exact commands, hashes,
counts and outcomes are in the adjacent evidence JSON. This Q6 step changes no
runtime policy, model, frozen certificate or device installation.
