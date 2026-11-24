# Historical public neighbor-recovery corpus

These three files reproduce the original September 2026 disclosed neighbor
corpus and match its original manifest hashes. The rows derive from the pinned
2023-11-01 Russian Wikipedia shards listed in `manifest.json`, distributed
under CC BY-SA 3.0 and GFDL. `articles.jsonl` supplies each source article's title
and a link to its edit history for attribution to the Wikipedia contributors.
The [Wikimedia notice](../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md) links the
license terms and documents the source. The corpus includes synthetic typo variants and protected controls; it is not
user typing data, a fresh holdout, or evidence of current model quality.

The earlier generator identified by the manifest is not recovered; row identity
was independently reproduced with the retained later generator. Native numeric
family IDs are not canonical lemma identities. The original receipt is retained
separately in `historical_provenance_sources/joint-neighbor-receipts/`.
