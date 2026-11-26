# English and Spanish spelling attribution index

The six JSONL files list the article ID, title and URL for all 15,652 candidate
source articles in the [spelling maps](../README.md). Each file corresponds to
one map. An ambiguous row can link to several articles. The metadata comes
from the pinned Wikimedia Wikipedia Parquet snapshot `20231101`. The
[manifest](manifest.json) binds each map, source shard and metadata file by
SHA-256, with the upstream path and Parquet revision.

The six source schemas contain `id`, `url`, `title` and `text`. They do not
contain Wikipedia revision IDs. The links identify articles, while the
Parquet hash identifies the historical snapshot inputs. The output excludes
article text. This index covers the EN/ES spelling maps. Publication review
still needs to assess the original article revisions and the other archived
components.

To regenerate one index, supply the matching shard from the source lock and
run from the repository root with PyArrow 25.0.1 and a new output path.

```sh
python3 tools/typing_experiments/recover_historical_spelling_attribution.py \
  --version v2 --language en --shard /path/to/en-0019.parquet \
  --output build/v2-en-attribution.jsonl
```
