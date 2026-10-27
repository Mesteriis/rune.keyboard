# Review Q6, first migration: durable exclusion keys

Historical bootstrap receipt. The subsequent [source recovery](2026-10-27-legacy-holdout-recovery.md)
adds article/window identities and discloses historical overlap in current v6
corpora. Counts and missing axes below describe the original bootstrap only.

The first ledger snapshot and its dependency-free checker are now tracked.
This is a verified bootstrap, **not completion of Q6** or fresh-data qualification.
Historical coverage remains explicitly incomplete and blocks freshness approval.
No model, runtime behavior, thresholds, APK or device state changes.

## Persisted facts

`holdout-ledger.json` contains nine entries:

- Six public Wikipedia spelling corpora v7–v12: 1,700 typo-independent
  context/target keys each. Original rows/manifests match both their own frozen
  hashes and the existing right-context exclusion plan. Public-source revision,
  license, generator/runtime and hash metadata are retained, including the
  distinct historical generator SHA values.
- Current disclosed calibration: 1,651 article, 1,661 source-context, 588 family
  and 4,583 left-context/target keys.
- Current reserved, unscored holdout: 1,614 article, 1,630 source-context, 523
  family and 4,481 left-context/target keys.
- The 42 current supervised right-context families, bound to existing preparation
  metadata and its tracked evidence receipt.

The current corpus chain is verified through the tracked source-v6 evidence,
scoring-plan input hashes, corpus/identity-audit receipts and original source
plan. Source parquet hashes are preserved from that historical plan; this step
does not re-download data or claim a new source-parquet audit. No holdout model
predictions, scores or threshold choices are read during migration.

The snapshot has 26,973 sorted identity digests and is 2,119,798 bytes. Rebuilding
from preserved inputs is byte-identical on both Python 3.11 and Python 3.14:
`cead20d51939a948d0a1f3d85b80e4de0fd1562a43097312e34a823be514ea49`.
The importer refuses to overwrite an existing snapshot.

The existing `conversation_split_checks.py` normalizer and its four tests are
tracked without changing their bytes or historical semantics. Context identity
continues to normalize NFC/case/whitespace, preserve punctuation and exclude
the typo surface from left-context/target identity. Hash kinds/namespaces are
separate. The first implementation supports the current Russian/Wikipedia
identity schema; other source formats need explicit adapters, not silent guesses.

## Known missing coverage and failure behavior

Historical spelling rows lack article IDs and carry legacy family strings that
are not certified as canonical Pymorph lemmas. Their article, canonical-family
and source-sentence axes remain marked missing. Other public joint/context/
conversation histories and required historical generator versions also remain
pending. Private or owner-derived corpora are not silently imported into this
public ledger.

Known intersection raises `LEDGER_OVERLAP:<axis>` even while the ledger is
incomplete. Otherwise a freshness check raises `LEDGER_INCOMPLETE`. Missing row
identities, malformed digests, duplicate records/keys and inconsistent coverage
claims fail explicitly. An empty corpus cannot pass by vacuity. Changing only
the root `complete` flag cannot hide pending imports or missing axes.

The `new-sentences` profile preserves the existing protocol: supervised families
are forbidden, previously evaluated families may recur only in new source
articles/contexts. `new-families` additionally excludes all recorded family
keys. This does not alter frozen generators, existing qualification requirements
or the independent source/label/cohort/quality audits.

The CLI freshness gate exists, but old hash-bound builders are not rewritten to
invoke it. Wiring it into versioned future preparation entry points is still
required after coverage recovery. A schema-only green CI step is not approval
to qualify new data or promote any rejected right-context model.

## Checks and CI

Eleven ledger tests and four existing normalization/separation tests pass. The
same commands pass in a temporary source-only directory without `build/`, models,
Java, Pymorph or the phone. A known public article remains blocked there, while
otherwise unseen rows fail `LEDGER_INCOMPLETE`. Current calibration/holdout keys
are disjoint on all four recorded axes, and the current 42 supervised families
intersect neither part.

The actual CI step is added before Java/native setup: schema validation plus
these 15 dependency-free tests. Its commands were reproduced locally in an
isolated directory; no remote GitHub run is claimed. Python bytecode directories
are ignored, without deleting any user files. Existing unrelated working changes
and old generator files remain untouched.

Raw check evidence is under `build/holdout-ledger-bootstrap-20261027/`, bound by
the accompanying receipt. No full JVM suite, lint, APK, Fold or release acceptance
is claimed for this tools/CI-only migration.

Next: recover historical article/selection identities and canonical family keys,
import the remaining source-bound histories, archive exact generator versions,
then require the complete ledger in the new builder/replay workflow. Packaged
training/provenance inventory and Q7 replay integration remain open. See
`tools/typing_experiments/HOLDOUT_LEDGER.md` for commands and current boundaries.
