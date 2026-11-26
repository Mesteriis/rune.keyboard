# Sources for the historical qualification archives

The spelling and punctuation rows in both archives use the Wikimedia
Wikipedia snapshot `20231101`, in English, Spanish and Russian. The
historical generators selected and transformed Wikipedia text into contexts,
spelling variants and punctuation examples. A separate authored matrix
produced the protected-token rows. The archives are retained for reproducible
historical checks.

The manifests name CC BY-SA 3.0 and GFDL 1.3 for the Wikipedia source. The
original [Wikimedia source notice](../../model/rune-text-0.2/WIKIMEDIA_NOTICE.md)
links the license terms and describes the upstream snapshot. The exact shard
locations, expected byte sizes and SHA-256 digests are recorded in the
[v3 source lock](../frozen_sources/qualification_v3_source_lock_14ceb1c0cbe8b20e.json)
and [v4 source lock](../frozen_sources/qualification_v4_source_lock_3f86e8b384c094e7.json).
Both locks point to Parquet revision `a634f78b1c435397c07001e175fa74cc4ad5e775`.

Historical corpus rows retain a shared source label and derived template
identities. The generators use article IDs to select articles. Candidate
generation retains text-derived keys, so each attribution map can contain
more than one article for the same row.

Candidate source articles for EN/ES spelling are now available in
[the retained maps](article-maps/README.md). The earlier
[RU spelling recovery](../../../docs/acceptance/2026-10-27-early-ru-source-recovery.md)
and [punctuation recovery](../../../docs/acceptance/2026-10-27-punctuation-source-articles.md)
cover their respective archived components. A row can match several articles.

The [punctuation and Russian spelling attribution reports](punctuation-ru-attribution/README.md)
include candidate article titles and URLs for the remaining Wikipedia-derived
rows across v2–v4.

## Attribution and distribution scope

The [pinned dataset card](https://huggingface.co/datasets/wikimedia/wikipedia/blob/b04c8d1ceb2f5cd4588862100d08de323dccfbaa/README.md)
records CC BY-SA 3.0 and GFDL for the source collection and describes text
extraction from Wikimedia dumps. The corpus generators further extract
contexts and construct spelling variations or punctuation examples. Rune's
root MIT license applies to its original code and documentation. The archived
Wikipedia-derived text follows the applicable source license.

Section 7 of the [Wikimedia Terms of Use](https://foundation.wikimedia.org/w/index.php?title=Policy:Terms_of_Use&oldid=598588#7._Licensing_of_Content)
lists article URLs as one way to attribute contributors. The recovered
indexes provide these URLs for all archived Wikipedia-derived rows, including
every candidate when a row is ambiguous. The snapshot schemas do not provide
article revision IDs. Exact revision IDs would improve traceability. The
linked terms do not list them as a condition of attribution by article URL.

Section 7 also calls for indicating modifications, preserving applicable
additional attribution for imported material, and including the distribution
license and its text or link. It identifies CC BY-SA 4.0 or later for modified
Wikimedia text under the terms, subject to applicable exceptions. The
[CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)
describes the license conditions in Section 3. The source collection's
license labels document provenance. Checking article-specific notices and
settling the license for a public archive are separate release checks.
