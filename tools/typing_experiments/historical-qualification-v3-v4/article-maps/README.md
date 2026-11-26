# English and Spanish spelling source articles

The scanner replayed the frozen v2, v3 and v4 spelling candidate generators on
six pinned public Parquet shards. Each shard matched its recorded size
and SHA-256. The scan also reproduced the historical number of scanned and
eligible articles. A match requires the original selection hash, target word,
prefix and family. The output retains all distinct matching article IDs per
row and no source text.

| Archive | Language | Rows matched | Multiple article matches | Distinct articles |
| --- | --- | ---: | ---: | ---: |
| v2 | EN | 3,400 | 14 | 2,657 |
| v2 | ES | 3,400 | 20 | 2,463 |
| v3 | EN | 3,400 | 14 | 2,666 |
| v3 | ES | 3,400 | 24 | 2,537 |
| v4 | EN | 3,400 | 16 | 2,712 |
| v4 | ES | 3,400 | 12 | 2,617 |

Use an article ID with the row's language, for example
`https://en.wikipedia.org/?curid=<id>` for an EN row. These links identify
candidate source articles. The scanner did not recover revision IDs or
establish which article supplied a row when multiple articles match.

To regenerate a map, supply the corresponding shard from the
[v2 source lock](../../frozen_sources/qualification_v2_source_lock_e3ad381de42a6ac0.json)
or [v3/v4 source locks](../NOTICE.md), and run from the repository root with PyArrow
25.0.1. The output path must be fresh.

```sh
python3 tools/typing_experiments/recover_historical_spelling_articles.py \
  --version v3 --language en --shard /path/to/en-0030.parquet \
  --output build/v3-en.json
```

All six scans exited zero. The original JSON reports are preserved with their SHA-256 values listed below.

| Map | SHA-256 |
| --- | --- |
| v2-en | `010e73b16cef526a35ae7c5fac85cdef1333f339ead676ffa8e4de1403696ce1` |
| v2-es | `791567744f7f5f7d08afc7afa041f94941c8552e24af9a71653634109ac9ffdf` |
| v3-en | `a6e1c372ac9aaa57c0ff6a32d33d165892ddfeb92f4400ad036ac82f2e63c288` |
| v3-es | `d27aebca87ef795dc4f74c966a3a912d0baea37e6375d84655f2ca5ea83ae0da` |
| v4-en | `4c7d6cefa2f945a69e599830791a20673ecb818d069e0ca01d9cf03c895d696d` |
| v4-es | `52829200603faad738dfac521037e3a91c1f82ec88112b4e4eee0fe4c2d33c3f` |

The six maps contribute 15,652 language-qualified article keys to the Q6
control registry. The v3/v4 registration added 10,141 keys and the v2
registration added another 4,894. The
registrar validates the frozen map hashes, source locks, generator identities,
archived row coverage and all six resulting entries. The corpus preparation
gate rejects a new context from any of these articles, including secondary
matches for ambiguous rows. The lexical registry's Wikipedia article keys
use an unqualified numeric ID, so these EN/ES entries use the control
registry's language-qualified namespace. Publication review remains open.

The [attribution index](attribution/README.md) records the snapshot titles
and URLs for each of these spelling maps.
