# Punctuation and Russian spelling attribution

The nine reports list matching source articles for all 3,600 punctuation
rows in v2–v4 and all 10,200 Russian spelling rows. Each report contains a
row-to-article map and the ID, title and URL of every matching article in
that source shard. Multiple candidates for the same row are retained.
The records contain no article text.

The scans reopened the pinned Wikimedia Wikipedia `20231101` Parquet
shards and checked their size and SHA-256. The original punctuation selector
recovered 3,617 occurrences. Its article keys and occurrence counts match
the existing control ledger. For Russian spelling the article keys agree
with the three existing lexical entries. The reports bind the frozen rows,
shards, generator and source lock by SHA-256.

The control registry also carries language-qualified keys for all 6,875
Russian spelling articles. Of these, 6,502 were absent from the previous
control registry. CI checks the three entries against the frozen maps and
the lexical article keys. A preparation test exercises article rejection
when the supplied lexical registry lacks the same article.

Together with the [English and Spanish spelling attribution](../article-maps/attribution/README.md),
the reports locate candidate articles for the 34,200 Wikipedia-derived
spelling and punctuation rows in v2–v4. The 5,400 protected-token rows
come from authored matrices. The pinned shard schemas lack Wikipedia
revision IDs. Any publication review requiring exact article revisions
still needs separate verification.

To reproduce a report, supply the corresponding locked shard and run from
the repository root with PyArrow 25.0.1.

```sh
python3 tools/typing_experiments/recover_historical_punctuation_attribution.py \
  --version v2 --language ru --shard /path/to/ru-0009.parquet \
  --output build/v2-ru-attribution.json
```
