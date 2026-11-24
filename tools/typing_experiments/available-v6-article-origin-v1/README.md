# Available v6 public article identity recovery

This mapping resolves the article keys already registered for historical v6
calibration and holdout to public Wikipedia page IDs and pinned shard names.
It contains no article text, typo rows, candidates, scores or natural typing
observations. It does not qualify a corpus or reproduce the missing rows.

The source is [Wikimedia Wikipedia, 20231101 Russian snapshot, pinned
revision](https://huggingface.co/datasets/wikimedia/wikipedia/tree/a634f78b1c435397c07001e175fa74cc4ad5e775/20231101.ru/train).
The source metadata declares CC-BY-SA-3.0 and GFDL-1.3; see the project's
[attribution and provenance](../../../app/src/main/assets/smarttyping/experiments/NOTICE.md).
The retained mapping consists only of article IDs, shard names, partition labels
and registered keys; it is not a redistribution of article text. Individual
article revisions and contributors were not reconstructed for publication.

To validate the retained mapping and current registry without source downloads:

```sh
python3 -B tools/typing_experiments/check_available_v6_articles.py
```

To reproduce from public source shards, install the pinned host scientific
requirements, then run into a new output directory:

```sh
python3 -B tools/typing_experiments/recover_available_v6_articles.py \
  --download-temporary --output /tmp/rune-v6-article-recovery
```

The download path verifies each source hash before and after decoding, processes
one shard at a time, and removes each temporary shard. Alternatively use
`--source-dir PATH` with all ten predownloaded files named `0011.parquet` through
`0020.parquet`. Existing output is not overwritten. The source lock and current
historical ledger bindings are required; PyArrow and its native dependencies
are not authenticated by this script. Delete any user-created output directory
when it is no longer needed. Historical raw text and selection plans remain
missing; see the adjacent acceptance receipt for the exact limits.

## Historical context anchors

`context-recovery/anchors.jsonl` contains source offsets and registered context
hashes, not text, typo rows, candidates or scores. The source offsets are
zero-based Unicode code-point positions after NFC normalization. The report
keeps every candidate, including cross-partition matches and ambiguous locations;
no candidate is silently chosen. Check the retained artifact without downloads:

```sh
python3 -B tools/typing_experiments/check_available_v6_contexts.py
```

To repeat the public-source scan into a new directory, use the same pinned host
scientific requirements and run:

```sh
python3 -B tools/typing_experiments/recover_available_v6_contexts.py \
  --download-temporary --output /tmp/rune-v6-context-recovery
```

Alternatively use `--source-dir PATH` with all ten pinned files. Source shards
are verified before and after decoding; a temporary download is removed after
each shard. This scan does not reproduce historical selection, error variants,
labels, model execution or a qualified holdout. The decoder's provenance and
the original complete selection plan remain unverified.

## Registered target-key candidates

`target-recovery/matches.jsonl` maps registered prefix/target hashes to source
anchors, retaining offsets and hashes only. Check the frozen receipt locally:

```sh
python3 -B tools/typing_experiments/check_available_v6_targets.py
```

To repeat the source scan with the pinned scientific requirements:

```sh
python3 -B tools/typing_experiments/recover_available_v6_targets.py \
  --download-temporary --output /tmp/rune-v6-target-recovery
```

Alternatively pass `--source-dir PATH` with the ten pinned files. Temporary
shards are deleted after each scan. These matches do not recover historical
rows, typed errors, labels or selection. Unmatched keys cannot be classified
from this evidence alone. The offline checker binds the retained scan output; it
cannot independently recompute target hashes without the source text.

## Recovered rival associations and exact calibration input

`rival-recovery/matches.jsonl.bz2` completes candidate coverage of the
previously unmatched registered target keys. Its records are hashes and
source offsets. `calibration-recovery/calibration.tsv.bz2` expands to the
exact historical calibration input verified against the original manifest.
It contains encoded prefixes and generated variants from the pinned
Wikipedia snapshot. Its upstream source terms and pending publication-rights
review are described in the [recovery report](../../../docs/acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#all-remaining-target-keys-and-byte-exact-calibration-tsv).
The historical holdout and selection plan remain incomplete.

The following command verifies both archives locally.

```sh
python3 -B -m unittest discover -s tools/typing_experiments -p test_available_v6_recovery.py
```

`calibration-recovery/source-index.jsonl` binds each ordered context group in
the exact TSV to its article and registry keys. It excludes the original
prior-family exposure flag, which remains unverified. Run
`python3 -B tools/typing_experiments/check_available_v6_calibration_index.py`
to verify the index offline.

`calibration-attribution/articles.jsonl` supplies the exact pinned snapshot
titles and URLs for all calibration articles. The adjacent receipt binds the
source lock and the already verified calibration input. The map supplies links for the
source notice. Publication approval remains pending.

`holdout-attribution/articles.jsonl` supplies the pinned snapshot titles and
URLs for all 1,614 holdout articles. Its receipt binds the holdout source
index and decoded TSV digest. Source revision IDs and distribution rights
remain open for both partitions.

`calibration-attribution/translation-sources.json` records source references
from historical discussion-page translation notices. It identifies candidates
for attribution and stores checks of the numeric revision references that were
available. The [publication screen](../../../docs/acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#translation-notices-in-historical-discussion-revisions)
describes its coverage and the remaining passage-level review.

`revision-witnesses-0011/` contains the full-text matches for the first shard.
Each page record keeps every matching revision in the sampled API window.
Matching the cleaned text provides an attribution witness. The XML dump's
original revision identity still requires source evidence.

The revision check uses Python 3.12, PyArrow `25.0.1`, and
`mwparserfromhell` `0.6.5`. It verifies the indexed pages, Parquet digest and
pinned cleaner before comparing public revisions through the MediaWiki API.
It writes revision metadata and digests, with no article text in the output.
Specify `--source` with a local pinned Parquet file to skip the shard download.

```sh
python3 -B tools/typing_experiments/recover_v6_revision_witnesses.py \
  --shard 0013.parquet --download-temporary --output build/v6-revision-witnesses-0013
```

Check the captured reports against the historical page index offline. Add
`--local-root build` to include newly captured directories and `--require-all`
to make missing shards fail the check. The report keeps missing reports,
missing pages, exact-text witnesses and ambiguous matches distinct.

```sh
python3 -B tools/typing_experiments/check_v6_revision_witnesses.py --local-root build
```

With `--corpus`, the checker also verifies both restored v6 JSONL digests
and projects the page outcomes onto corpus rows and contexts. The numeric
result distinguishes matches by the dump date, later matches, missing pages,
and pages still awaiting checks. It also lists each checked exception with
its public article ID and the number of affected rows and contexts.

The following command repeats the metadata-only scan with the pinned
scientific requirements.

```sh
python3 -B tools/typing_experiments/recover_available_v6_calibration_attribution.py \
  --download-temporary --output /tmp/rune-v6-calibration-attribution
```
