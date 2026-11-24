# Q6: recovered v6 availability and corpus manifest

Two missing historical metadata files were reconstructed from captured output of
the original local preparation session. The recovered bytes match the original
SHA-256 values in `2026-10-27-right-context-numeric-bridge-evidence.json`:

- `sentence_pairs_v2_v6_availability.json`: 927 bytes, SHA-256
  `ea94b32ee61b828de62e7e4a4666a2b699031614e34fe77906d6fc3da1e92d83`.
- `available_clean_v6_manifest.json`: 1,521 bytes, SHA-256
  `63a96729330de3d36024ab6d062542bfeed0461d3b3d4202f820c74a30b90691`.

The availability object reports 926,220 scanned articles, 1,661 calibration
and 1,632 holdout candidate contexts. Its matched-copula counts, 75 and 72,
are below the historical required 400 per partition. The later clean manifest
reports 7,905 calibration and 7,750 holdout rows, explicitly marks the full
cohort gate as failed and disallows holdout scoring. These are historical
aggregate observations, not proof of new independent qualification.

The clean manifest supplies four original file hashes. A read-only SHA-256 scan
of all 8,587 Git blob objects available locally, including unreachable objects,
found none of those four exact files. The scan covered 8,438 blobs at or below
4 MiB (314,992,129 bytes) and 149 larger blobs (6,123,607,385 bytes). This is a
boundary on the local Git object store, not a search of every backup, external
storage location, or source service. The historical plan, context rows, corpus
files, model lineage and independent holdout therefore remain incomplete.

Three source-only tests verify both recovered files against their original
receipt, the reported cohort failure and all four corpus hash formats; a
mutation is rejected. No original selector or model was executed. The test is
assigned to the stdlib CI inventory. No private conversation text or corpus
rows were copied into these metadata files.

The same three tests also passed from a staged source archive without `build/`;
that temporary archive was removed. Inventory validation passed with 199
stdlib and 26 scientific modules. Full profiles and hosted CI were not repeated.

## Identity audit and model link

A further captured JSON object reconstructed the original clean-v6 identity
audit byte for byte: 922 bytes, SHA-256
`bdcdc6d6954771036608ba64cc6daea3fce956dbfdf0e07f210ddaaa23e10662`.
Its hash matches `identityAuditSha256` in the recovered manifest and the
original numeric-bridge receipt. The audit reports its own identity checks
passed, but also says the prior family metadata was not exhaustive, earlier
evaluation families were allowed, and quality qualification was not performed.
That historical result does not override later overlap findings or establish a
fresh independent holdout.

The manifest's `modelSha256` matches the existing tracked 39,444-byte
`app/src/test/resources/right-context-model-parity/model.bin`. This identifies
the retained model bytes; it does not restore the original frozen-model JSON,
training inputs, corpus rows or establish a new model run. A read-only scan of
8,445 Git blobs at or below 4 MiB matched the model but did not match the clean
plan, parent plan, identity audit, prior-exclusion receipt or calibration
receipt. The exact audit was recovered from captured output, not that Git scan.
Larger Git blobs were not checked for those additional metadata targets.

The expanded four-test recovery suite passed both locally and from a temporary
source archive without `build/`; the archive was removed. Full profiles and
hosted CI were not repeated for this metadata recovery.

## One logged calibration observation

One complete calibration object was recovered from an earlier successful local
command's output; that command read the old available-clean-v6 calibration
JSONL. The stored JSON is a normalized serialization of that observed object,
with SHA-256 `5061b2449adfe6b306b354432de6a3d2dbfe1823e86a489d64e914ea659d9490`
as a new fixture-integrity marker. There is no original per-row signature, and
one logged example cannot prove the recovered bytes match the missing complete
corpus file or its manifest hash. The recorded source label points to the
Wikipedia-derived `0018.parquet` shard; the individual article's attribution
and rights were not reverified for publication.

The example's source context digest reproduces from its recorded fields. Its
one article key, both family keys, one source-context key and one target-context
key are already present in the historical calibration ledger entry. This is a
previously disclosed example and must not be used as an independent holdout.
Five recovery tests passed locally and from a temporary source archive without
`build/`; that archive was removed. The remaining 7,904 calibration and 7,750
holdout rows are not recovered by this observation. No model was scored.

## Source-article verification for the logged observation

The logged example identifies article 8825104 in the Russian Wikipedia 20231101
snapshot shard `0018.parquet`. Hugging Face's metadata for pinned revision
`a634f78b1c435397c07001e175fa74cc4ad5e775` reports 209,795,982 bytes and the
same SHA-256 `588e30523cfed480151b4bd5c1a7d7211dc03971fee399a3db6af3ad04e42c87`
recorded in the historical joint-corpus source bindings. A downloaded shard
matched both values. Of 92,622 records, exactly one had the recorded article
ID and exactly one source-text occurrence matched the logged prefix, original
word and right context. Its snapshot title and URL identify the public article
[«Депортации из Латвийской ССР»](https://ru.wikipedia.org/wiki/Депортации_из_Латвийской_ССР).
No full article text or downloaded shard was retained.

The new `verify_available_v6_observation.py --source PATH` repeats the
source/observation hash checks before and after reading, rejects absent or
duplicate articles and contexts, and reports only bounded metadata. The initial
manual check and the new verifier both passed against independently downloaded
copies of the pinned shard. Four synthetic-Parquet tests pass, including wrong
hash, missing/duplicate article or context, and source drift; they also passed
from a temporary source archive without `build/`. The tests are assigned to the
scientific profile; inventory validation passes. PyArrow 25.0.1 was used, but
its wheel and transitive decoder dependencies were not independently attested.
Both downloaded shards, archives and temporary Python environments were removed.

The source match establishes correspondence for the observed public excerpt,
not its inclusion in the missing complete corpus file. The snapshot's exact
Wikipedia revision and individual contributor attribution remain unverified;
the article link and general snapshot licensing notice alone do not complete a
publication-rights audit. No model was evaluated and no fresh holdout is
claimed.

## All registered v6 source article identities

The archived v6 selector identifies ten Russian Wikipedia 20231101 shards,
`0011` through `0020`. Pinned Hugging Face revision
`a634f78b1c435397c07001e175fa74cc4ad5e775` supplied the ten files; their
published LFS hashes match the corresponding historical ledger bindings. A
single sequential run downloaded 2,055,492,010 bytes, one shard at a time,
verified each shard's exact size and SHA-256 before and after decoding, and read
only the ID column. All ten shards contained 92,622 rows, for 926,220 total,
matching the recovered historical availability count.

All 3,265 distinct v6 article keys in the current historical registry resolved
to unique public page IDs: 1,651 calibration and 1,614 holdout. The retained
`available-v6-article-origin-v1/recovered/articles.jsonl` contains IDs, source
shard names, partitions and their existing ledger keys, not source text. Its
SHA-256 is `0f55e171539de0b476041a960f2a8f212ff6b4bfac23625aed8eecd84d8b2d88`.
The recovered logged example maps to its previously checked shard and partition.
The receipt binds the ledger snapshot, pinned source lock and examined helper
versions. PyArrow 25.0.1 was used; its wheel and complete native decoder chain
were not independently attested.

At this earlier registry snapshot, the recovered mapping resolved intersections
with all other then-registered historical entries: 140 calibration and 144
holdout articles. By shard `0011`–`0020`, calibration counts are
`29,25,18,16,19,12,21,0,0,0`; holdout counts are
`17,20,18,23,26,19,21,0,0,0`. These count distinct articles, not v6 rows or
errors. The registry remains incomplete, so absence from these intersections is
not evidence of independence.

A source-only checker validates every ID against the original registered key,
partition, duplicate detection, source counts, frozen mapping hash and helper
bindings. Eight focused tests cover real retained data, rehashed mutation,
false qualification claims, historical intersections and synthetic Parquet
source failures; all passed in a temporary source archive without `build/`.
The CI inventory check passed. All downloaded shards and temporary source and
Python environments were removed. Neither original corpus rows, the historical
plan, per-article Wikipedia revisions nor independent qualification were
recovered; the original v6 cohort gate remains failed. Full profiles and hosted
CI were not repeated.

## Source-context anchors for registered v6 keys

The exact pinned shards were scanned again, one temporary file at a time. For
the 3,265 mapped articles, the scan applied the recorded neighboring-word
selector and bounded-prefix logic, then compared each derived source-context
hash with the two v6 sentence-key sets. The selector source matches its original
receipt hash; the bounded-prefix function's syntax matches both retained
historical v2 sources. The original complete selection plan and selection
outcomes were not reconstructed.

Every one of the 3,291 registered sentence keys has at least one candidate in
an article assigned to the same partition. Within that restricted set, 3,277
keys have one candidate location and 14 have multiple candidate locations. The
scan also found one additional candidate in an article assigned to the opposite
partition; it remains in the artifact but is excluded from the unique-location
count. There are 3,307 candidate anchors in total. Multiple locations are not
silently resolved, and matching source context is not proof of historical
selection or a distinct corpus row.

The retained `context-recovery/anchors.jsonl` contains only article IDs, shard
names, context and ledger hashes, partition labels and zero-based NFC Unicode
code-point offsets. It contains no source text, synthetic errors, labels or
model scores. Its SHA-256 is
`2fc6aecbc3616ffdb80c124b16e2d5bd7c6c74d0eb7be3731ab9034845bfb472`.
The previously recovered logged observation has one matching same-partition
anchor. The source-only checker validates all keys, mapped articles, offsets,
counts, ambiguity, helper bindings and the frozen artifact hash.

The full scan checked all ten shards before and after decoding, with 926,220
source rows and no lowercasing-length refusals for the mapped articles. Python
3.12.14, Unicode 15.0.0 and PyArrow 25.0.1 were used; the decoder wheel and
native chain were not independently attested. Eleven focused tests passed from
a temporary source archive without `build/`, including fake Parquet, source
drift, duplicate and missing articles, all ambiguity classes, a rehashed
mutation and helper drift. The public source shards and temporary Python/source
environments were removed. The CI inventory includes both test modules; full
profiles and hosted CI were not rerun. Historical corpus rows, labels and
model qualification remain open.

## Target-key candidates from source anchors

A subsequent scan checked 3,306 same-partition anchors across the ten pinned
shards, verifying each shard's size and SHA-256 before and after decoding. The
single opposite-partition anchor was excluded. Against 9,064 distinct registered
prefix/target keys, it retained 6,584 candidate mappings: 3,292 source-word and
3,292 protected-source-word candidates. These cover 6,576 distinct keys: 6,570
with one candidate and six with multiple candidates. Another 2,488 keys remain
unmatched; none of the retained mappings crosses partitions. Candidate mappings
are not counts of original rows, and unmatched keys cannot be classified from
this evidence alone.

A matching hash connects a registered prefix/target combination to a candidate
source position. It does not establish the original selected row, its typed
error or label: several generated variants can share an expected spelling, and
the reconstructed generator lacks independent historical source attestation.
The retained artifact contains offsets, IDs and hashes, not source text or
words. Its SHA-256 is
`2be072e1019f844f5455626a9443a9f3481b2e633c015c9e3f4519ec4d1537d4`.
The offline checker verifies its frozen hash, receipt, ledger, anchor and helper
bindings and structural consistency; recomputing target hashes requires the
public source scan. Python 3.12.14, Unicode 15.0.0 and PyArrow 25.0.1 were used;
the decoder and native dependencies were not independently attested. This is
not a recovered corpus or independent model qualification.

Nine focused tests passed from a temporary source archive without `build/`:
five scanner tests and four retained-receipt checks, including rehashed output,
false label claims and ledger drift. The CI inventory check passed. Full CI
profiles and hosted CI were not rerun for this slice; temporary shards and
Python/source environments were removed.

## Later A4 shard exposure

The later A4 frequency screen read the entire pinned `0011.parquet` shard.
After its 92,622 articles were added as exposure exclusions in both ledgers,
193 calibration and 162 holdout v6 articles match that shard. The union against
all other currently registered lexical entries is now 304 calibration and
289 holdout articles. These newly registered intersections describe later
source exposure, not newly discovered historical training or v6 row counts.
The original per-shard counts above remain the earlier snapshot's result.
The exclusion manifest and checks are documented in the
[A4 frequency receipt](2026-11-10-a4-abbreviation-frequency.md#whole-shard-exposure-quarantine).

The retained target-candidate receipt binds the full lexical-ledger SHA-256 at
the original scan. The two later A4 entries changed that file and initially
caused the target checker to fail closed. The checker now accepts the new ledger
only after independently validating both specific A4 entries in both registries,
removing exactly those two lexical entries in memory, and reproducing the
original serialized ledger's exact receipt hash. Any other old-ledger change or
altered A4 entry still fails. A regression mutates the earlier coverage record
and confirms refusal. The historical receipt and target mapping were not
rewritten; source data and model outputs remain unrecovered.

## Local indexed-file and snapshot check

On 2026-11-10, `tmutil listlocalsnapshots` exited 0 for both the system and
Data volumes and listed no Time Machine snapshots. A read-only Spotlight
`mdfind` search for the four original corpus filenames, scoped separately to the
canonical checkout and its one other current worktree, returned two accessible
candidates in the canonical checkout. Both were hashed; neither matched the
corresponding historical manifest hash. The other worktree returned no indexed
candidates. No candidate was modified or copied.

This only covers names present in Spotlight's index and Time Machine local
snapshots at that time. It does not search unindexed files, differently named
files, archives, external backups or other locations, and does not recover v6.

A subsequent `rg --files --hidden --no-ignore` inventory of the same two
worktrees, excluding Git internals and owner Fold recovery directories, found
four accessible files with these names: two calibration JSONL and two holdout
JSONL, with no TSV candidates. All four were SHA-256 checked, and none matched
the corresponding historical manifest hash. The command exited 0 in both
worktrees and no candidate read errors were recorded. This supplements the
indexed search but does not traverse archive contents or follow directory
symlinks, and does not cover differently named files or external locations.

The two worktrees were also inventoried by extension rather than by filename:
147 accessible `.jsonl` and `.tsv` files (69,647,178 bytes) were read solely to
compute SHA-256 and compared with all four original file hashes; none matched.
Four paths containing protective terms for logs, diagnostics, owner or private
data were excluded, as were Git internals and Fold recovery directories. Both
inventories exited 0 and no candidate read errors occurred. Renamed files with
other extensions, compressed data, excluded paths, symlinked directories and
external locations were not searched.

A bounded follow-up inventoried ZIP, TAR, compressed TAR, BZip2 and XZ-named
archives in the same worktrees with the same protective path exclusions. Both
inventories exited 0. Twelve archives were opened without extracting to disk;
56 regular `.jsonl` or `.tsv` contents, including eligible standalone BZip2
streams, were hashed (114,696,406 decompressed bytes). None matched any of the
four historical hashes; no read error or 100 MB per-member limit was reported.
The check did not recurse into nested archives, inspect other member extensions,
follow directory symlinks, or cover excluded or external paths. It does not
establish that no copy exists elsewhere.

## Expanded worktree and compressed-file search

At `3f4f7d80`, the six worktrees listed by Git were searched for the four
original corpus SHA-256 values and the original plan SHA-256. The first pass
hashed 3,306 raw JSON, JSONL or TSV files (1,045,663,936 bytes) and 15
standalone gzip streams with those extensions before compression (241,359,907
decoded bytes). Nine streams exceeded that pass's size limit. No hash matched.

A second pass checked 421 archive files across the same worktrees, streaming
741 regular contents or standalone compressed streams (1,921,244,351 decoded
bytes). It included TAR variants and ZIP members with JSON, JSONL or TSV
extensions and standalone gzip, BZip2 and XZ streams. The second pass also
selected unusually large raw JSON, JSONL or TSV files and found none.
Both passes deduplicated by filesystem identity within each run and excluded
Git internals, common dependency directories, symlinks and paths indicative of
logs, diagnostics, private material or owner backups. Neither pass extracted
files or found a match. The second pass did not recurse into nested archives.
The searches provide no evidence about external backups or excluded paths.

The four focused recovery and retained-evidence modules passed all 18 tests.
This verifies the checks over retained evidence. The original plan, corpus
files and historical holdout result remain unavailable.

## All remaining target keys and byte-exact calibration TSV

At `93488d52`, two public-source scans checked all ten pinned Wikipedia
shards against the source lock before and after decoding. Each scan checked
926,220 source records and applied the archived selector's dictionary
contrasts to the previously registered same-partition anchors. It used the
shipped grammar asset with the original selector's SHA-256, and Pymorphy3
2.0.6 with the Russian dictionary 2.4.417150.4580142. The original selector
is hash-attested. The installed dictionary and Parquet native dependencies
were identified by version.

Both scans produced the same **2,492 associations for all 2,488 previously
unmatched keys**, with three keys having multiple
possible locations and zero cross-partition matches. Calibration accounts for
1,261 associations with unique keys. Holdout accounts for 1,231 associations
covering 1,227 keys. The compressed artifact contains only existing registry
keys, page IDs, offsets and partitions. Together with the prior source and
protected-word candidate map it accounts for every one of the 9,064 registered
target keys. This is coverage of registered keys, with candidate ambiguity
preserved.

A separate pass over the calibration candidates restored the v6 TSV. It
used the archived cohort priority and selection digest, exact neighboring-word
boundaries, and the original 50k frequency file by SHA-256. It produced the
typo, unfinished, correct, protected and dictionary-rival variants in the
historical order. The first attempt split the following word on whitespace
and did not match. Using the selector's punctuation-aware boundary, the
third cohort-compatible choice across the ambiguous calibration payloads
produced **7,905 rows and 3,266,373 decoded bytes**, with SHA-256
`b19e91877a9dc4ec200a4982b191d7c9348efdf8196ddb84047521a4c04b3abb`.
This exactly matches `calibration.tsv` in the recovered historical manifest.

The archived TSV is historical diagnostic input. It contains Base64-encoded
source prefixes and generated variants. The source snapshots declared
CC-BY-SA-3.0 and GFDL-1.3. This local recovery does not establish article
revision attribution or publication rights. At this stage the exact historical
`calibration.jsonl`, both original holdout files and the plan were missing.
No model was evaluated and the original cohort gate remains failed.

The source-only tests check the recovered TSV against the historical
manifest, verify the full rival-key coverage against the bound anchors and
registry, and reject modified archive content. Both archives are recorded in
the F-Droid data inventory without a scanner exception. A fresh full
F-Droid scanner run and hosted CI remain open.

## Calibration TSV source index and JSONL reconstruction probe

At `f2a730e3`, the verified calibration TSV was decoded into its 1,661
ordered context groups. A fresh pass over the same ten hash-pinned Parquet
shards recomputed candidate metadata for the calibration anchors. The
reconstruction kept only candidates with the exact TSV prefix, typed forms,
dictionary rival where present, and historical cohort position. Each TSV
context group had one distinct compatible metadata record. The ordered
result also matched the 1,651 registered article identities, 1,661 sentence
keys and 588 registered family keys. Its first reconstructed JSON object
matched the previously logged original in every field.

The retained `calibration-recovery/source-index.jsonl` maps ranges of
historical TSV rows to their article, existing sentence key and family keys.
It stores no extra text. Its SHA-256 is
`feed2e451dbe91d7afb5eac8fc946b92b2dbda2b414e7cb3f91469df559c44d8`.
The offline checker verifies the exact TSV digest, contiguous group ranges,
and source/protected/rival target-key associations against the existing
anchored maps. It also checks complete article, sentence and family coverage.

The original `familyExposure` flag depends on the set of prior bound records
at selection time. The retained natural and side registries and eleven earlier
Tatoeba cohort registers gave 276 distinct exposure assignments to test.
None produced the expected historical `calibration.jsonl` SHA-256. The
non-matching candidate JSONL was not retained, and the index omits
`familyExposure`. Earlier source binding contents and any other byte-level
differences still need confirmation. The original JSONL files and selection
plan remain open.

The captured preparation commands identify the earlier binding chain.
The v6 selector added the natural-frozen and side corpora to the bindings
in the first Wikipedia plan. That plan inherited from focused-v2. The
focused preparation inherited the noun-case-v3 manifest's exclusions and
added the noun-case-v3, broad-v2 and instrumental corpora and the Tatoeba
sentence-split file. The noun-case preparation in turn inherited from
grammar-focused. This identifies the earlier inputs to check for original
family values. The present registry includes dictionary-derived expansions,
so its family key sets alone cannot substitute for the historical row fields.

## Calibration article URLs and plan input gaps

The archived selector and captured preparation commands identify the parent
selection plan's source and exclusion bindings. The current recovery matches
the original plan SHA-256 and records the recovered binding digests. The
three additional cohort payloads still require reconstruction.
[Exact v6 parent selection plan](#2026-11-24-byte-exact-v6-parent-selection-plan)

At `d319fa57`, a separate calibration-attribution scan read only the article
ID, title and URL columns of all ten pinned Parquet shards. Each shard matched
its locked size and SHA-256 both before and after decoding. The scan accounted
for 926,220 source records and located all 1,651 articles in the calibration
source index. The 1,651 URLs are distinct and every decoded URL path matches
the accompanying snapshot title. The retained
`calibration-attribution/articles.jsonl` has SHA-256
`52879ff76c1362c617d5910c4e75455c884e4a720034322a1a9593afe9e06fec`.
The receipt binds the source lock, exact TSV, context index, article registry
and recovery helpers. The scan decoded and retained only those three metadata fields.

Wikimedia's terms list an article hyperlink as one mechanism for attribution
and address imported material separately. This map supplies article links.
It leaves current article notices, article-specific imported content terms
and distribution-license review outstanding.
[Wikimedia Terms of Use, section 7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)

## 2026-11-23 v6 calibration publication screen

The exact TSV contains Wikipedia-derived prefixes and source words along with
generated typo, protected and dictionary-rival variants. The grouping and
encodings preserve the historical experiment. The [pinned Parquet revision](https://huggingface.co/api/datasets/wikimedia/wikipedia/revision/a634f78b1c435397c07001e175fa74cc4ad5e775)
contains no dataset card. The later [dataset card at `b04c8d1`](https://huggingface.co/datasets/wikimedia/wikipedia/raw/b04c8d1ceb2f5cd4588862100d08de323dccfbaa/README.md)
labels original text CC BY-SA 3.0 and GFDL. Wikimedia's terms effective June 7,
2023, its dump guidance and the current Russian Wikipedia rights endpoint use
CC BY-SA 4.0 for ordinary text. Wikimedia expressly calls for checking the
page footer, history and discussion for imported text. The current site-wide
default and the mirror's metadata give different versions and cannot certify
individual archived excerpts.
[Wikimedia terms, section 7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)
[Wikimedia dump licensing](https://dumps.wikimedia.org/legal.html)
[Russian Wikipedia rights endpoint](https://ru.wikipedia.org/w/api.php?action=query&meta=siteinfo&siprop=rightsinfo&format=json&formatversion=2)

An unauthenticated read-only API screen queried all 1,651 numeric article IDs
in batches of up to 50 and accounted for each ID. It used the pinned article
map (`52879ff7…`) and matched exceptions to the exact TSV through the bound
source index. The current results were:

| Current result | Articles | Historical context groups | Historical TSV rows |
| --- | ---: | ---: | ---: |
| Article absent by ID and snapshot title | 14 | 14 | 68 |
| Current article has a different title | 34 | 34 | 163 |
| Current article has a copyright-violation template | 1 | 1 | 5 |

All 1,637 returned articles were in the main namespace; none was a redirect.
Of these, 1,603 retained their snapshot title. The absence cases returned no
redirect or available destination when queried by snapshot title. All 14 had
public deletion-log records. One copyright-related comment was attached to a
2012 deletion under the title mapped to archive ID `8848451`. The latest
deletion under that title was in July 2026. The 2012 comment precedes the
snapshot and does not identify the affected text in the TSV.

Missing snapshot IDs: `5883205`, `5935145`, `6139095`, `7171152`, `7778924`,
`7795183`, `8402514`, `8732109`, `8848451`, `9089473`, `9222833`, `9623169`,
`10084417`, `10164587`.

For article `7013362`, the archive's normalized prefix and source word occur
literally in both the revision last available on the snapshot date and the
current tagged revision. The historical revision lacks the inline copyvio
template; the current revision includes it. The check does not establish that
the markup refers to the extracted passage. These five rows require examination
before redistribution.
[Historical revision `132949401`](https://ru.wikipedia.org/w/index.php?oldid=132949401)
[Tagged revision `156340832`](https://ru.wikipedia.org/w/index.php?oldid=156340832)

The API also returned associated discussion titles for all 1,637 available
articles. Of those, 677 discussion pages were absent. The 960 available pages
had 240 transclusions of the translated-article template, covering 242 context
groups and 1,151 TSV rows. None returned either of the other two queried
templates, copyright violation and VRTS permission. This screen checks the
current transclusions. Historical notices, template arguments, unstructured
discussion text, imported authorship and article footer notices still need
verification.

The recovered TSV remains an unpublished exact historical artifact.
`publicationRightsReviewed` in the archive catalog remains false. A future
distribution notice must bind the actual archive, carry the author attribution
and applicable licenses, describe the selection and generated changes, and
preserve source-specific notices. The exact archive is reachable from
`f2a730e3`; deleting its path in a later commit alone would still transfer the
blob if that history were pushed. An independently reviewed distribution
history must exclude any unresolved blobs from the objects it sends.
[CC BY-SA 4.0, section 3](https://creativecommons.org/licenses/by-sa/4.0/legalcode#s3)

All 11 focused archive tests passed after the screen. The temporary API probe
and response metadata were removed. No article text or deletion-log comments
were persisted by the probe.

### Scope of the copyright warning

The source-aligned calibration prefix and source word for page `7013362` are
unique literal matches in the inspected revisions after NFC, case folding
and whitespace normalization. The match is in `Критика` in revision
`132949401`, and in `Реакция` in revisions `156312943` and `156340832`.
Both later revisions place the copyright-warning template directly below the
heading `Вооружённое противостояние моджахедов рохинджа и правительства Мьянмы`.
Its comment scopes the allegation to that section and names an International
Crisis Group report. The indexed calibration context is outside that section.
This narrows the specific flag and leaves the general attribution and
publication review open. The report URL and copyright notice both returned
HTTP 403 during this check, so the alleged source was not independently
compared.
[Snapshot-date revision](https://ru.wikipedia.org/w/index.php?oldid=132949401)
[Current tagged revision](https://ru.wikipedia.org/w/index.php?oldid=156340832)

The Internet Archive Availability API also returned zero captures in 14
successful requests for the missing articles' exact pinned snapshot URLs,
requesting the nearest capture to November 1, 2023. This covers those URL
forms and that endpoint. It leaves the 68 rows from those pages without
an independently verified historical attribution copy.
[Availability API documentation](https://archive.org/help/wayback_api.php)

### Translation notices in historical discussion revisions

Selected the 240 current talk pages with the translated-article template and
requested each talk page's latest public revision through November 1, 2023,
23:59:59 UTC. Of these, 237 had retrievable wikitext; every returned revision
predated November 1. A structured parse with `mwparserfromhell` 0.7.2 found 221
translation notices on 217 pages. These account for 218 context groups and
1,035 TSV rows. The projected source titles cover 11 language editions.
Fields for free-form comments and contributors were omitted from the receipt.
Two source-version values and one receiving-version value did not have a
plain numeric form and were omitted. The sample covers present-day template
candidates and can miss archived notices removed from current discussions.
[Template field documentation](https://ru.wikipedia.org/wiki/Шаблон:Переведённая_статья)

Of the 18 numeric source-version references, 15 resolve to the reported title,
two resolve to different current titles and one is unavailable. The two
different titles also failed page-ID equivalence after resolving redirects of
the reported title. All six numeric receiving-version references resolve to
their expected Russian article IDs. These are page-level metadata checks.
They do not locate the translation inside the article or certify rights to
the calibration excerpt. These cases still require passage-level review.

The [translation-source receipt](../../tools/typing_experiments/available-v6-article-origin-v1/calibration-attribution/translation-sources.json)
binds the restored TSV, source index and article map. It records the historical
discussion revision, reported source and available reference checks for each
projected notice. Its SHA-256 is
`1461b88dc8faac62280255cc347cbd03594b62b63054b109a34de182e97c02a4`.

## 2026-11-23 byte-exact holdout TSV recovery

Two scans each verified and decoded all ten locked Parquet shards, covering
926,220 source records per scan. The reconstruction used the original
punctuation-aware following-word boundary, frequency input, grammar asset,
Russian dictionary and selection digest. The control reproduced all 7,905
calibration rows byte for byte against the existing archive in both scans.
The runs used Python 3.12.14, PyArrow 25.0.1 and the repository's hash-locked
Pymorphy dependencies. All 11 focused recovery tests passed afterward.

For holdout, the first scan found 1,630 context groups. Two groups had two
compatible payloads each. One of the four layouts matched the original group
counts and 7,750 rows. The first TSV encoded contiguous source IDs and failed
the manifest digest check. The archived exclusion log records that the original
generator assigned source IDs before removing two five-row matched-copula
contexts. The retained TSV indices are still contiguous, while the IDs in
column two preserve the gaps.

The second scan tested the 2,556 possible placements of the two gaps within
the matched-copula group. The matching layout omits source IDs `3965`–`3969`
and `4005`–`4009`, at zero-based retained row indices `3965` and `4000`.
The resulting 7,750 rows and 3,116,900 decoded bytes match the original
`holdout.tsv` digest exactly:
`36a769b5b2e1ed0f76667bd4336d4792502195c83233ff34fd29e85d2ca0ca6b`.
An independent parser checked every line and decoded source ID. The compressed
local archive was reopened and compared byte for byte against the reconstruction.

The exact TSV and the executed reconstruction script are retained locally in
the Git-ignored `build/retained-historical-v6/` directory. The
[versioned receipt](../../tools/typing_experiments/available-v6-article-origin-v1/holdout-recovery/receipt.json)
binds the manifest, archived exclusion report, source lock, source anchors and
recovered byte hashes. The archive contains source text and remains subject to
publication-rights review. Both original JSONL files and the parent selection
plan remain outstanding. The original cohort gate remains failed, holdout
scoring remains disallowed, and the reconstruction made zero model calls.

## 2026-11-23 holdout source index and JSONL field check

The original 402-byte prior-context exclusion report was recovered from the
numeric-bridge evidence. Its SHA-256 is
`76e48ec2bca6d1e4dd180e83630ea080ae50e07510dbd29b324fede7e9f146c0`.
It binds the two historical removed context hashes and the ten removed holdout
rows. The clean diagnostic plan also requires the SHA-256 of the complete
parent `contexts.unqualified.jsonl`, including the excluded contexts. The
partial corpus manifest and retained TSVs do not supply that digest.

A further scan verified all ten shard hashes and evaluated the known context
anchors against both exact TSVs. The exact row order and payloads left one
compatible metadata record for each of the 1,661 calibration and 1,630 holdout
groups. An independent check compared every reconstructed variant's encoded
source ID, prefix and typed column against the TSV. It checked all protected,
printed-source and rival target associations against the previously recovered
registry maps. All four registry axes were matched in each partition.

| Partition | TSV rows | Article IDs | Sentence keys | Family keys | Target keys |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | 7,905 | 1,651 | 1,661 | 588 | 4,583 |
| Holdout | 7,750 | 1,614 | 1,630 | 523 | 4,481 |

The new [holdout source index](../../tools/typing_experiments/available-v6-article-origin-v1/holdout-recovery/source-index.jsonl)
contains row ranges, article IDs and existing sentence and family keys. Its
SHA-256 is `d56fb9d7fa167f599e8414dac7190a057a2a7667ad3cad07694dbe3c850e03eb`.
The same computation reproduced every entry of the existing calibration index
and the first logged calibration object when provided its observed exposure
flag. The locally retained compressed metadata candidates use `null` for the
unverified `familyExposure` field so the source scan can be reused. They
contain source text and remain under the Git-ignored retention directory.

For holdout, the retained natural and side registry entries and 13 historical
Tatoeba source groups produced 240 distinct exposure assignments. None
reproduced the whole original JSONL hash. Recovering the actual prior bindings
and verifying both original JSONL digests remain necessary. Publication rights
and independent qualification remain open.

## 2026-11-23 source anchors for the two excluded contexts

The archived exclusion report gives two source-context hashes. The verified
holdout TSV gaps place them in the matched-copula group, between the retained
selection hashes at row boundaries 3,965 and 4,000. The source scan checked
all 926,220 records from the ten locked shards, verifying the shard digests
before and after decoding. It applied the original word boundary, morphology
and candidate rules, then checked both archived context hashes within their
selection windows. Each expected hash had one compatible source occurrence.

| Retained row boundary | Wikipedia article ID | Source shard | NFC word offsets |
| ---: | ---: | --- | --- |
| 3,965 | 8345020 | `0017.parquet` | `[1357, 1364)` |
| 4,000 | 4719133 | `0011.parquet` | `[23104, 23110)` |

Reinserting these two groups in selection order reproduced all pre-exclusion
availability counts, including 1,661 calibration contexts, 1,632 holdout
contexts and 7,760 pre-exclusion holdout variants. Both partitions also matched
the historical per-group, family and cue-type totals. All 3,293 reconstructed
parent-context candidates are now available locally across the existing
retained groups and the two omitted records. The omitted candidates are in
the Git-ignored `build/retained-historical-v6/excluded-context-candidates.json.bz2`.

The [source-anchor receipt](../../tools/typing_experiments/available-v6-article-origin-v1/holdout-recovery/excluded-contexts.json)
binds the archived counts, exclusion hashes, source lock, holdout TSV receipt
and both source indexes. It stores no excerpt text. The original exposure
flags and whole-file parent context digest remain unverified. The cohort gate
and the original holdout scoring restriction are unchanged.

## 2026-11-23 earlier v6 preparation chain

The original logged shell heredocs and literal source edits yielded seven
preparation scripts. They were recovered as text without running the recorded
commands. The [noun-case-v3 preparer](../../tools/typing_experiments/frozen_sources/prepare_d22734e202939a42.py)
matches the original `cohortManifest.preparerSha256` in the
[noun-case evidence](2026-10-26-noun-case-training-evidence.json).

The six remaining source captures are in
[`historical_provenance_sources`](../../tools/typing_experiments/historical_provenance_sources).
They cover grammar-focused, noun-case-v2, broad-v2, instrumental,
right-context-focused-v2 and fresh-matched-v5. Each capture has a stable digest
and parses as Python. Independent historical source hashes for these six
captures have yet to be found.

Focused-v2 brought forward the noun-case-v3 exclusion map and added the
noun-case-v3, broad-v2 and instrumental row files plus the Tatoeba split.
Broad-v2 wrote decimal packed-morphology family IDs. Instrumental and
noun-case-v3 wrote dictionary lemmas. The v6 selection tested exact strings in
the prior `family` and `families` fields, so replacing broad-v2's numeric IDs
with dictionary-derived exclusion keys would change the historical input to
that test. Fresh-matched-v5 belongs to the additional article bindings. It
supplies an article exclusion for selection and contributes to the later
identity audit, outside the earlier family-flag calculation.

The original row files remain outstanding. No corpus or model was run for
this source recovery. The parent plan was recovered in the later pass below.

The [Natural Frozen v2 model binding](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/natural-frozen-model-v2-binding.json)
matches the original `modelBindingSha256` in the
[training receipt](2026-10-27-right-context-training-evidence.json).
It links the previous model from the byte-exact Natural Frozen manifest
to the new training-only model. The receipt confirms that all four
corpus file digests and the training family set carried forward. It also
records that independent scores had yet to be read.

The original role-training v5 and v6 plans and frozen model bindings have
also been recovered. All four SHA-256 values match the independently recorded
receipts for [v5](2026-10-27-right-context-other-part-training-evidence.json)
and [v6](2026-10-27-right-context-role-kotlin-evidence.json). The archived
trainers define serialization and key order. The verified v4/v5 authored
generators reproduce 9,572 v5 rows and supply the 38 declared family keys
whose selection is confirmed by the original binding digests. The plan
recovery also used the historical Git assets and the noun-case count bindings.
No model was fitted or scored.

The [lineage receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/role-training-v5-v6-lineage.json)
records the original digests and uses a repository-relative key for the one
machine-local path in each original document. The exact documents are retained
in the ignored recovery directory. The v6 plan reuses the v5 corpus and
candidate pools. The frozen bindings share 9,094 groups, 134,459 training
candidates and identical group, vector and selection digests.

The original v6 binary is present as the tracked
[JVM model fixture](../../app/src/test/resources/right-context-model-parity/model.bin).
Its 39,444 bytes match the SHA-256 in the recovered v6 frozen binding
and the October Kotlin receipt. A fresh checkout of `2c8a2af925ba`
passed all seven `RightContextRevisionFeaturesTest` cases. The suite
compared 36 composed vectors, 36 runtime vectors and scores, and 284
split-boundary probes, and verified malformed-model and layout refusals.
The JUnit report SHA-256 was
`50d9540f7156075057ffbc94f7f6b6961cf0e86aaa3ae8f98de083ae43d60427`.
All 38 declared families in each frozen binding also match the existing
supervised ledger entry. The temporary checkout was removed.

### 2026-11-24 historical v5/v6 candidate-pool replay

The archived v4 and v5 preparers regenerated 8,688 and 9,572 authored rows
respectively. Both `train.jsonl` digests matched the
[original authored receipts](2026-10-27-late-authored-history-evidence.json).
The preparers also emitted 802 v4 queries and 1,007 v5 queries. A separate
manifest recovery restored the original generator path key and dictionary
installation receipt. That dictionary receipt is shared with the verified
[grammar-focused manifest](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/grammar-focused-manifest.json).
The reconstructed v4 and v5 manifests matched their respective original
SHA-256 values and are retained under the ignored recovery directory.

The v5 queries ran through the production spelling replay harness rebuilt from
`3bd893ca` with the five compiler JARs verified against the historical toolchain
manifest. The `noun-case-production` replay and historical `select_groups`
reproduced 9,094 groups, 134,459 candidates and 478 incomplete-pool skips.
The SHA-256 of the serialized `groups.jsonl` was
`f7d8b3c0d777108372fb16b3783cfbf99161a9f59043c0ce3c504274c1638888`, matching
the original shared v5/v6 digest in the lineage receipt. The recovered groups
are retained under the ignored recovery directory. The isolated compiler cache
and checkout were removed. The harness includes host nanosecond timings in
its observations, and the selection receipt binds the entire observations
file. Both original files remain unverified.

The [recovery command](../../tools/typing_experiments/recover_role_training_groups.py)
reproduces the shared groups from a clean checkout with the historical Git
revision available. Run it with Python 3.12 and the locked morphology
dependencies, Java 17, and the Android SDK with platform `37.0`. Prepare the
pinned Kotlin JARs using the same Gradle target as hosted CI.

```sh
./gradlew --no-daemon -p tools/ci/replay-toolchain prepareReplayToolchain
python tools/typing_experiments/recover_role_training_groups.py \
  --java "$JAVA_HOME/bin/java" --output build/recovered-role-training
```

The command writes `groups.jsonl` and a numeric `receipt.json` to the fresh
output directory after verifying the original SHA-256 and counts. A clean
checkout run verified the digest and confirmed that reusing the output path
is refused. The temporary checkout, replay observations, and compiler output
were removed.

The CI workflow fetches the exact historical commit into its existing
depth-one checkout and runs this replay after setting up the pinned compiler
and Python environment. Recovery exports the fetched tree directly with
`git archive`. A nested clone was shown to omit the detached fetched tree
in this configuration. Running the workflow's shell step from a local
depth-one checkout reproduced the original groups digest. The upload path
includes only the numeric receipt. Hosted execution remains open.

### 2026-11-24 byte-exact v5/v6 refits

The archived v5 trainer's feature extraction and fitting stages ran on the
verified group file and both recovered count tables. The feature source files,
archived trainer and 25 historical model assets were checked against the frozen
lineage. The isolated environment used NumPy 2.2.6, CatBoost 1.2.8 and the
hash-pinned morphology dependencies. The exported v5 weights and the shared
178-feature vector archive both matched their original SHA-256 values.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Shared `train-vectors.npz` | 2,152,992 | `da1e56dcc5966c8bf2ff11d6ee20ea8d10612dc2e63dc659f4fac780171c1895` |
| v5 `experimental-ranker.bin` | 22,036 | `44327fbfc294b7568292702ab8b43f8d3a0c951458f5c5bc1fc89ca065e1b16b` |
| v6 `experimental-ranker.bin` | 39,444 | `dfdc98954e702b3787118cb88ecd3268b25b4b1f498b45777872dc4c4c977594` |

The v6 fit used the original depth-six plan, the verified v5 parent and the
recovered vectors. Its export also matched the tracked JVM fixture byte for
byte. Across the first 32 training groups, maximum scalar-versus-CatBoost score
differences were `3.75e-8` for v5 and `3.05e-8` for v6. Both temporary checkouts
were removed. The shared vectors and v5 export are retained under the ignored
recovery directory.

The reruns verified computational inputs directly against the frozen lineage
and ran the archived fitting code without the historical receipt preamble.
The original observations and selection receipt were outside this validation.
Neither training fit establishes independent qualification.

The [refit command](../../tools/typing_experiments/refit_historical_role_models.py)
runs both fits from a clean checkout. Use the Python environment from the group
replay with NumPy `2.2.6` and CatBoost `1.2.8`. Supply the verified 500,000-row
Wikipedia `model-counts.jsonl` and the CC0 Tatoeba `tatoeba-train-counts.jsonl`.
Their original digests are recorded in the shared v5/v6 lineage. The example
assumes the count tables are in the local historical recovery directory.

```sh
python tools/typing_experiments/refit_historical_role_models.py \
  --groups build/recovered-role-training/groups.jsonl \
  --wiki-counts build/retained-historical-v6/word-context-v3/model-counts.jsonl \
  --tatoeba-counts build/retained-historical-v6/tatoeba-cc0-verified/tatoeba-train-counts.jsonl \
  --output build/refitted-role-models
```

The command writes both ranker binaries, the shared vector archive, and a
numeric receipt after all three output digests match. A clean checkout run
compared each output byte for byte against the recovered originals and the
tracked v6 fixture. It rejected an altered count table before training and
removed the temporary checkout and fit files.

## 2026-11-23 byte-exact early Wikipedia context pools

The seven `sourceContextBindings` in the v6 parent selector now have
byte-exact row files. The recovery read the locked Wikipedia Parquet shards
0012–0017 and 0020, verified each shard before and after decoding, and selected
only articles present in the original pool registry. Within those articles,
the historical copula pattern, source-window and target-context keys determined
one compatible capture per article. Rebuilding the original variant,
selection key, and partition order reproduced all 1,204 rows across all seven
files. Every output SHA-256 matched both the October receipt and the existing
registry. The recovery also reproduced each pool's article, context, and
dictionary family counts.

The
[recovery command](../../tools/typing_experiments/recover_natural_context_history.py)
takes `--source-dir` with the seven numbered `.parquet` files from the pinned
v6 source lock, and `--output` with a new directory under `build/`. It runs
with the pinned morphology dependencies and PyArrow 25.0.1. The seven exact
JSONL files are retained under the Git-ignored
`build/retained-historical-v6/natural-context-pools/`. The
[receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/natural-context-pools-recovery.json)
contains hashes and counts. Republishing the recovered text requires a
separate rights decision.

The original aggregate availability reports for fresh-matched-v5 (25/20),
reliable-side-v5 (844/846), and sentence-corpus-v6 (1,043/1,025) were also
recovered from the historical output. Their byte hashes match the original
acceptance receipts, and the counts are calibration/holdout contexts. Their
three `additionalArticleBindings` row files and both final v6 JSONL files
remain open. No model was run.

## 2026-11-24 byte-exact v6 parent selection plan

The original session output listed all 64 exclusion bindings, seven source
context bindings and five additional article bindings in serialization order.
The frozen selector defines the rest of the plan. Its reconstruction uses
the ten pinned Parquet hashes and the original v6 model and training-plan
digests. The result matches the recorded parent-plan SHA-256
`b54efac3d50e8f5d59ec9796118c55a370dd97b0f2111c37fb23c0c3561d6346`.
[Recovered plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/sentence-pairs-v2-v6-plan.json)
[Original selection receipt](2026-10-27-right-context-source-parity-and-selection-evidence.json)

The plan supplies exact target digests for the two noun-case inputs, broad-v2
and instrumental, and for the reliable-side-v5, fresh-matched-v5 and
sentence-corpus-v6 context files. The five original payloads, the final
available-clean v6 plan and its two JSONL files still require verification.

Four earlier plans also match their original file hashes: the first Wikipedia
collection, fresh-side-v4, reliable-side-v5 and sentence-corpus-v6. The first
Wikipedia plan binds the SHA-256 of the focused Tatoeba plan. Rebuilding that
plan with the 60 inherited exclusions and the 24 declared families from the
original authored training generator matches the parent binding. The plans
provide the original selection settings and confirm the exclusion chain.
[Historical plan files](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/)

## 2026-11-23 byte-exact Natural Frozen input

The seven recovered Wikipedia pools reproduce all 800 Natural Frozen contexts
and 3,200 variants. Both JSONL and both TSV payloads match their original
SHA-256 values. The original [plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/natural-frozen-plan.json)
and [manifest](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/natural-frozen-manifest.json)
also match the October receipt. Their reconstruction used the original
collector and feature digests and the 24 declared families from the
hash-verified authored training corpus. The two Natural Frozen JSONL files
are original inputs to v6's `exclusionBindings`. They supply the historical
declared `family` values for those inputs to `familyExposure`.

The [recovery command](../../tools/typing_experiments/recover_natural_frozen_corpus.py)
takes `--pool-dir` with the seven previously recovered pool files and
`--output` with a new directory under `build/`. It verifies the plan,
manifest, seven input digests, and four output digests. The exact original
corpus is retained locally under
`build/retained-historical-v6/natural-frozen/`. The command runs without a
model, a morphology environment, or a network connection once the exact pool
files are present. The derived texts remain local pending rights review.

The original `sentence-corpus-v6` preparation log was also recovered. Its
2,546 bytes match the [October evidence](2026-10-27-right-context-source-parity-and-selection-evidence.json).
The ten per-shard checkpoints give cumulative eligible article counts of
78,658, 156,877, 234,048, 314,125, 396,598, 479,729, 561,325, 643,023,
725,819 and 806,470 in the original order (0020, 0012–0019 and 0011).
The original process exited 1 with `INSUFFICIENT_SIDE_COHORT`. The raw log
is retained locally because the traceback contains a machine-local path.
These checkpoints can verify progress during a rerun of this additional
input, whose row file and plan remain outstanding.

## 2026-11-23 byte-exact Side and Fresh Side inputs

Side and Fresh Side v4 were reconstructed from the same seven locked
Wikipedia shards. The reconstruction matched each registered article,
source-window key and target-context key, then rebuilt the historical
variants and order. All six JSONL files and all six TSV files for Side,
Fresh Side v4, and Fresh Side v5 matched the original SHA-256 values in
the October receipt and the exclusion registry.

| Historical corpus | Calibration rows | Holdout rows |
| --- | ---: | ---: |
| Side | 6,050 | 5,810 |
| Fresh Side v4 | 5,800 | 5,780 |
| Fresh Side v5 | 5,800 | 5,776 |

The 35,016 row exposures include the repeated Fresh Side v5 contexts.
The exact Fresh Side v5 [plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/fresh-side-v5-plan.json)
was reconstructed with the 38 declared families from the hash-verified
authored training corpus. Running the original family filter preserved all
calibration rows and removed one whole holdout context with four variants.
The [manifest](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/fresh-side-v5-manifest.json)
then matched the original SHA-256, including the exclusion audit.

The [recovery command](../../tools/typing_experiments/recover_side_context_corpora.py)
takes `--source-dir` with the seven numbered Parquet files and `--output` with
a new directory under `build/`. It used PyArrow 25.0.1 and the pinned morphology
dependencies. A second reconstruction matched every payload byte. A corrupted
shard was rejected with exit 1 before output was created. Corpus text is
retained locally under `build/retained-historical-v6/side-context-verified/`.
The [receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/side-context-recovery.json)
records the counts and hashes without excerpts. The Side and Fresh Side v5
row files supply four original v6 inputs. The missing additional failed
cohorts, other historical bindings, and the final v6 JSONL remain open. No
model was run.

The original Side plan and manifest now also match their October SHA-256
values. The restored manifest preserves 92 excluded families, the original
partition counts, and the hashes of both JSONL and both TSV payloads. The
plan also records the candidate-policy digest and the 60 inherited exclusion
bindings. The fresh-matched-v5 plan still requires the complete Fresh Side v4
family exclusion list. The logged Fresh Side v4 list ends partway through the
packed numeric family IDs. Its context payload was recovered separately below.
[Side plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/side-plan.json)
[Side manifest](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/side-manifest.json)

## 2026-11-24 byte-exact Fresh Matched v5 context input

The scan matched all ten Parquet hashes before and after decoding and
accounted for 926,220 articles. It collected 41,214 short-adjective and
copula candidates using the original morphology and source guards. Restored
Side and Natural Frozen rows and the first seven Wikipedia pools supplied
known article and family exclusions. Those exclusions and the Fresh Side v5
inputs yielded 51 provisional contexts.

The original availability report fixes the calibration and holdout context
counts at 25 and 20, with 24 and 19 distinct families. Testing 1,877,200
subsets compatible with those counts yielded the original context JSONL SHA-256
`c14d15a2517cc4f8b80d509f5fcac395e3fe828bf92c0d331b14cb291b7bf5c5`.
All 45 rows are retained locally under `build/retained-historical-v6/`.
The receipt retains their public article IDs and row keys. The cohort failed
its original minimum-volume requirement. The recovered rows supply one v6
article-exclusion input. The article IDs and context hashes are disjoint
from all 3,291 reconstructed calibration and holdout anchors and from the
two separately recovered excluded anchors.
[Fresh Matched v5 recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/fresh-matched-v5-context-recovery.json)

## 2026-11-24 Diagnostic Rare Ranking provenance

The recorded manifest header and selection output reconstruct the original
manifest fields for `diagnostic-rare-ranking/fresh-corpus`. The preserved
follow-up generator matches the recorded builder SHA-256, and the reliable
Side v5 plan independently records both payload hashes and the same 0020
Wikipedia shard. The original run recorded 4,760 calibration rows and 4,788
holdout rows. Each partition contains 500 declared families. The original
command combined the three earlier Joint corpora with both first-letter
admission holdouts to build the exclusion input. The manifest records 6,480
excluded families and 7,521 excluded articles for that selection.
[Reconstructed Diagnostic Rare Ranking manifest](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/diagnostic-rare-ranking-manifest.json)

For reliable Side v5, the four recovered Wikipedia and Side input groups
account for 6,211 unique blocked article keys. The bound legacy-context and
Joint registry entries supply 3,804 and 5,173 more, with no overlap across
these groups. The original reliable Side v5 log reports 16,152 blocked
articles, leaving 964 article identities outside that verified union.
The two Diagnostic Rare Ranking payloads carry numeric `article` fields.
The older ranker rows use `articleId`, which the historical Reliable Side
selector did not read. The reconstructed manifest supplied the original
validation targets for both rare-ranking payloads.

The first-letter admission and confirmatory protocol files were recovered
from the original output. Both match the protocol digests in the October
acceptance receipt, which separately binds the 4,672- and 18,696-row
holdouts. The initial capture and its recorded text transformations restore
the two preparation sources. They parse as Python and their source-file
digests have no independent historical reference. Replaying the selection
against the pinned 0020 shard, historical morphology and word frequencies
produced the same surface pools of 4,389 and 3,879 word forms. Both complete
JSONL files match their original SHA-256 digests and are retained locally.

The two holdouts contribute 491 and 1,857 distinct article IDs, disjoint
from each other and from the 5,173 verified Joint article keys. Their union
reproduces all 7,521 article exclusions in the Diagnostic Rare Ranking
manifest.
[First-letter recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/first-letter-admission-recovery.json)
[First-letter admission receipt](2026-10-25-ambiguous-winner-evidence.json)

## 2026-11-24 exact Joint and Diagnostic Rare Ranking payloads

The archived native-morphology selectors reproduced the initial Joint
corpus, both follow-ups and Diagnostic Rare Ranking from four pinned
Wikipedia shards. All nine JSONL files match the original digests. The
initial Joint and two follow-up manifests also match their October SHA-256
values. The generated rare-ranking manifest equals the earlier reconstruction.
The replay used the original frequency data and morphology bytes and made
zero model calls. The 54,364 text rows and original manifests are retained
locally.

The regenerated rare-ranking rows contain 964 previously unaccounted article
keys. Their union with the earlier verified bindings reproduces the 16,152
article exclusions recorded by Reliable Side v5. Every regenerated Joint
and Rare Ranking row declares a packed numeric family ID. The later exposure
flags compare dictionary lemma strings. The Reliable Side v5 payload and
final v6 payloads remain open.
[Joint and Diagnostic Rare Ranking recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/joint-diagnostic-recovery.json)

### Joint and Diagnostic Rare Ranking control coverage

The original digests verified all nine row files again. The lexical ledger
already covered their article and typo-independent context keys. The
[control registration](../../tools/typing_experiments/register_recovered_corpus_controls.py)
now also covers the actual inputs and their protected examples. It added
12 entries and preserved all earlier entries.

| Historical corpus | Rows | Exact context keys added | Surface keys added | Source article keys added |
| --- | ---: | ---: | ---: | ---: |
| Original Joint | 25,647 | 25,647 | 20,360 | 2,164 |
| Joint follow-up | 9,584 | 9,584 | 9,039 | 957 |
| Joint follow-up v3 | 9,585 | 9,585 | 9,034 | 962 |
| Diagnostic Rare Ranking | 9,548 | 9,548 | 9,016 | 964 |

A second pass found zero missing control keys across the four corpora.
The canonical digest of the 12 entries is
`b3c34f184961271baa43f712580629c3e9c00f88bc2083c05723e7792f46547d`.
The source-only check validates this digest alongside both earlier batches.
Only hashes were registered. Full-source sentence provenance and independent
qualification remain separate.

The clean Python run caught a source-binding regression from adding the
shared projection to `control_ledger.py`. That module has its original
SHA-256 again. The [projection](../../tools/typing_experiments/historical_control_projection.py)
now lives separately, preserving existing A4 frequency, article review,
Spanish UniMorph and v6 receipt bindings.

## 2026-11-23 confirmed historical family exposure

Reprojecting the two reconstructed candidate partitions reproduced both
historical TSV hashes before testing any `familyExposure` assignment. The
original Natural Frozen and Side JSONL files supply exact declared families.
For noun-case-v3, the original selector uses the single dictionary lemma
of the source accusative noun. The existing derived registry contains that
lemma for each row, and its family counts match the archived declared totals
of 157 calibration and 168 holdout families. The registry and the receipt
both bind the original noun-case-v3 row hashes.

| v6 partition | Contexts | Confirmed `previously_bound` | Additional possible instrumental families | Distinct complete flag assignments tested |
| --- | ---: | ---: | ---: | ---: |
| Calibration | 1,661 | 1,325 | 10 | 512 |
| Holdout | 1,630 | 1,278 | 13 | 4,096 |

The [audit command](../../tools/typing_experiments/audit_available_v6_family_exposure.py)
enumerates possible additional instrumental families from the original
frequency list and the historical dictionary contrast rule. This is a
superset before the original prior-exclusion and sentence filters.
Each hypothesis preserves the confirmed flags. None matched the original
JSONL digest. The result rules out recovering the files by changing only
these possible instrumental flags on the current candidates. Other
historical declared families and any remaining differences in JSONL-only
fields still need checking. The command reads the local retained v6 inputs
via `--input-dir` and emits an aggregate report. It runs no model.

### Refinement archive families

The original, verified historical fixture archive retains the three refinement
row partitions. Their exact bytes and the train/dev/test concatenation match
eight paths in each of the Reliable Side v5, sentence-corpus-v6 and sentence
pairs v2-v6 exclusion plans. Four candidate-export paths and the all-rows
input share the concatenation digest. The 7,500 rows declare 3,668 distinct
family strings. The audit uses these original values directly, as the
sentence-pairs selector did.

| v6 partition | Additional confirmed contexts | Total confirmed `previously_bound` | Remaining instrumental flag assignments checked |
| --- | ---: | ---: | ---: |
| Calibration | 67 | 1,392 | 512 |
| Holdout | 62 | 1,340 | 1,024 |

Both TSV digests still match. None of the tested assignments produces the
original JSONL digest. Other historical family exclusions and JSONL-only
fields remain open. The test covers all three plans and rejects a missing
binding for a candidate-export path.

### Exact legacy spelling v6–v12 rows

The [recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/legacy-spelling-rows-recovery.json)
binds seven original spelling payloads to the historical ledger and all three
selection plans. The pinned public shards were verified before and after
scanning. The scan intersected the archived selector's candidates with the
registered article and typo-independent target-context keys. The archived row
builders restored each original 1,000-typo and 700-correct split. One v6 context
had two candidate prefixes under the same normalized key. Only one of the two
complete payloads matched its historical SHA-256. Each of v7 through v12 had
a single candidate assignment and matched its historical digest.

The seven files total 11,900 rows and 11,900 distinct original declared family
strings. The family-exposure auditor now includes their exact original values.

| v6 partition | Additional confirmed contexts | Total confirmed `previously_bound` | Remaining instrumental flag assignments checked |
| --- | ---: | ---: | ---: |
| Calibration | 33 | 1,425 | 128 |
| Holdout | 32 | 1,372 | 64 |

Both original TSV digests still match. None of the assignments reproduced the
complete JSONL digests. The original spelling row data are retained locally.
The repository records the metadata, and no model was called.

Reliable Side v5 was also rerun over the full 648,354-article source using
the complete 16,152 article exclusions and the verified refinement families.
Those inputs reduced eligible articles from 415,725 in the first replay to
344,572 in the second. The original reports 313,977. Both candidate context
payloads differed from the original digest and were removed. The recovered
spelling families provide another original input for the next replay.

### Exact Reliable Side v5 contexts

With the original declared spelling families included, the third selection
replay reproduced the complete 1,690-row Reliable Side v5 context payload
and the availability report byte for byte. The two successor plans bind the
context digest. The original role-training receipt independently binds the
availability digest. The replay scanned seven pinned public shards and
found the original 313,977 eligible articles out of 648,354 scanned.

The 844 calibration and 846 holdout rows identify 1,690 distinct articles.
Their union with the earlier article exclusions and the exact Fresh Matched
v5 articles produces the **17,886** blocked identities reported by the
historical sentence-corpus-v6 selection. The
[recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/reliable-side-v5-recovery.json)
binds both recovered payloads and the next article index. The row data are
retained locally. The original insufficient-cohort result still applies.

The separate clean-v6 identity audit counts previously bound families from
all three input maps. With 11 of the 12 context and additional-article
payloads verified, the recovered rows and noun-case family projection
account for at least 482 of its 498 calibration families and 451 of its
456 holdout families. The missing payload in those two maps is
`sentence-corpus-v6/contexts.unqualified.jsonl`. Other outstanding family
sources are in the original exclusion map. This comparison uses both exact
TSV context projections and the original identity-audit denominators
of 588 and 523 families respectively.

### Exact sentence-corpus-v6 contexts

Replaying the original selector with the recovered 17,886-article index
reproduced all ten historical shard checkpoints and both original payloads.
The successor plan binds the SHA-256 of the **2,068** contexts, and the
original source-parity receipt binds the availability report. The replay
scanned 926,220 articles and selected from the original 806,470 eligible
articles. The surviving calibration and holdout candidate counts match
1,043 and 1,025, respectively.

Each context came from a distinct article absent from the earlier exclusion
index. Their union accounts for all **19,954** blocked article identities
reported by the sentence-pairs v2-v6 selector. The
[recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/sentence-corpus-v6-recovery.json)
binds both payloads and this next index. The selected corpus still falls
short of the original positive-cohort requirements.

Adding the exact rows also closes the aggregate family proof from the clean
identity audit. With all twelve additional payloads and the verified earlier
families, the reconstructed candidates reproduce 498 previously bound
calibration families and 456 previously bound holdout families. The selector's
per-context `familyExposure` field uses only the exclusion map. Its final
JSONL digests still require the separate exact comparison.

Re-running the original identity auditor over the 7,905 calibration and
7,750 holdout rows reconstructed from both TSVs reproduced the original
identity-audit JSON byte for byte. The 19,954-key prior article index had
no intersection with the retained article identities. Separately, adding
the two source-verified omitted contexts and applying the original context
exclusion rule restored the exact exclusion-report bytes. Its two holdout
context removals account for ten variants. These checks use fields other
than `familyExposure`; the final corpus digests still require a separate
comparison.

The [final restoration command](../../tools/typing_experiments/restore_final_available_v6.py)
takes a replay directory containing the parent availability and context
records. It checks the historical input digests, allocates the original
variant IDs before applying the two holdout exclusions, and reports
separate digest matches for the plan and the four payloads. It emits
files only when all five original digests match. It does no model calls.

A test using all 3,293 recovered context candidates and the confirmed
subset of family-exposure flags reproduced both TSV files. The two JSONL
files and the plan still differed. The command returned exit code one
and created no output. Unit tests cover the original ID gaps, missing
excluded contexts, duplicate context identities and unknown family flags.

## 2026-11-23 exact noun-case ancestry

The three original noun-case selection plans, the first availability report,
and the v3 separation audit were recovered byte for byte and checked against
the [original receipt](2026-10-26-noun-case-training-evidence.json).
The first capped run found 863 calibration and 967 holdout contexts against
a target of 1,000 each. V2 raised the per-family cap from 24 to 64. It kept
the same seed, 1,000-context targets and 97.5%/95% precision requirements.
V3 kept the V2 cap and thresholds and explicitly excluded the five disclosed
failure families. The original separation audit records 56 checked bindings.

The existing [noun-case contrast generator](../../tools/typing_experiments/noun_case_contrast_corpus.py)
also regenerated all 1,140 authored training rows in an isolated, hash-locked
morphology environment. The
payload SHA-256 matched its original training-selection receipt. This is
one exact ancestral input to the noun-case selection chain. It contains 24
distinct literal `noun-case:` family labels. The historical v6 flag uses
exact strings, so dictionary lemmas derived from those contrast forms cannot
be substituted for its native labels.

The metadata files are in the
[tracked input archive](../../tools/typing_experiments/historical_provenance_sources/v6-inputs).
The exact authored payload is retained locally under
`build/retained-historical-v6/noun-case-authored/`. The original 56-entry
binding map, natural noun-case row files, and final v6 JSONL remain open.

The exact authored source now contributes 25 canonical family keys and
576 target-context keys to the durable holdout ledger. Other entries already
covered all 25 family keys, while all 576 context keys are new to the ledger.
The registration preserves both contrast targets for every authored prefix,
including the retention variants. It adds no historical article or sentence
identities to this authored source. The
[registration check](../../tools/typing_experiments/register_noun_case_authored.py)
regenerates all 1,140 rows with the pinned dictionary, verifies the original
payload SHA-256 and compares both registry entries. The scientific job now runs
that check. The historical reconstruction still uses the original native
family labels described above.

The registry update retains all 225 earlier entries and their on-disk packing.
The original v6 target checker continues to require its historical registry
digest after verifying the known newer entries. An initial integration check
rejected the valid additions. The revised checker specifically verifies both
new entry digests before projecting them out of the historical view. A modified
entry or a missing half of the pair is rejected.

## 2026-11-23 exact grammar contrast inputs

The original authors' generator reproduces 630 rows in the
[initial corpus](2026-10-26-grammar-contrast-diagnostic.json) and 978 rows in
the [edit-profile corpus](2026-10-26-grammar-edit-profile-training-evidence.json).
Both payloads match the SHA-256 digests recorded in October and are retained
locally under `build/retained-historical-v6/grammar-contrasts-authored/`.
Both have 35 original family labels under `infinitive:`, `object:`, and
`predicate:`. The edit-profile corpus is an exclusion input to the historical
noun-case v3 selection.

With the pinned morphology dictionary, both payloads produce the same 38
canonical family keys and 420 target-context keys. The holdout ledger already
covered all 38 family keys and eight context keys. The two new entries add
412 context exclusions and bind both exact corpus digests. The
[scientific CI check](../../tools/typing_experiments/register_grammar_contrasts.py)
regenerates the payloads and compares the resulting entries. The v6 target
checker verifies both entry digests before projecting the pair out of its
historical ledger view.

## 2026-11-23 broad and instrumental noun-case inputs

The original [offline evidence](2026-10-26-noun-case-offline-evidence.json)
contains two aggregate result objects. Serializing them with the original
format reproduces both recorded `result.json` hashes. The recovered
[broad-v2 result](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/noun-broad-v2-result.json)
covers 12,000 rows, including 6,000 controls. The recovered
[instrumental result](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/noun-instrumental-result.json)
covers 68 rows, including 51 controls. Both record zero eligible revisions
and no precision estimate.

The original plan-write commands also recover the literal
[broad-v2 plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/noun-broad-v2-plan.json)
and [instrumental plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/noun-instrumental-plan.json).
Their source, model and policy hashes agree with the archived receipts and
noun-case-v3 plan. Broad-v2 targeted 3,000 contexts with a cap of four per
packed morphology family. The instrumental plan allowed 512 contexts and at
most 32 per family. Its original selection output reports 22 eligible
sentences and 17 selected contexts across five families. An independent
historical SHA-256 for either plan and the manifests and row payloads for
these two inputs remain open.

## 2026-11-24 focused Tatoeba plans and availability

The [grammar-focused selection plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/grammar-focused-plan.json)
matches the original plan SHA-256 in the
[infinitive revision policy](2026-10-26-infinitive-revision-offline-evidence.json).
It combines the original logged declaration, source and model digests from
historical receipts, and the retained scope and form files. The original
[availability output](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/grammar-focused-availability.json)
records 18,251 eligible sentences and 500 selected contexts in each
partition, from 155 calibration and 148 holdout families. The independent
infinitive receipt confirms the selected counts. This grammar corpus supplied
the parent exclusions for noun-case-v3.

The later [right-context-focused-v2 availability](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/right-context-focused-v2-availability.json)
records 1,324 eligible sentences, then only 83 calibration and 14 holdout
contexts. The original preparer stopped because both partitions fell short
of the planned 400 contexts. The first Wikipedia plan binds the recovered
focused plan. Both captured availability documents come from the original
command output. Their standalone original file hashes and the grammar row
files still require reconstruction against the historical bindings.

The November 21 detailed Russian export has 1,239,867 rows and its compressed
SHA-256 differs from the October source. Dropping the 8,092 rows created on
or after October 25 at midnight leaves 1,231,775 rows, 561 fewer than the
1,232,336 recorded by both original selectors. This filter uses a calendar
cutoff for the comparison. Exact snapshot membership requires separate
verification.

Of the remaining rows, 23,184 have a modification timestamp at or after the
cutoff. A streaming scan of 53,439,049 public contribution events found a
pre-cutoff Russian text entry for every one of those IDs. In 23,145 cases the
text matches the current detailed export after normalizing TSV escapes. The
other 39 differ. The audit retained counts only. The original generators
also serialize the owner and source modification date, so restoring text
alone leaves the original payload digests unverified.
[Tatoeba export definition](https://github.com/Tatoeba/tatoeba2/blob/master/docs/database/scripts/weekly_exports.sql)

The NUR Tatoeba package records hashes for the October 17 and October 31,
2026 detailed exports. Its version history jumps between those dates. Both
listed Russian export digests differ from the pinned Rune digest. A lookup
for the exact filename and digest in the public Nix cache returned HTTP 404.
The NUR maintainer's advertised Cachix endpoint returned HTTP 403 for the
requested digest and for both neighboring controls, leaving that cache's
coverage unverified. The Internet Archive Availability API returned no
capture for the exact per-language export URL or the compressed global
detailed-export URL when requesting the closest capture to October 25.
[NUR package update](https://git.sikmir.ru/nur-packages/commit/e58e9085a60d7632b2c291cf04d7184f19b0431e.html)
[Advertised Cachix endpoint](https://git.sikmir.ru/nur-packages/file/README.md.html)
[Nix store path specification](https://nix.dev/manual/nix/2.34/protocols/store-path)
[Availability API](https://archive.org/help/wayback_api.php)

### Detailed-export preparers and family representation

Five source files were reconstructed from their creation and subsequent
patch commands. The follow-on, Supervised 95 and Grammar Context preparers
match SHA-256 values printed from their original manifests. The Grammar
Contrast and Grammar Conservative evaluation preparers have their
recorded source changes and integrity digests. Their independently
attested source digests remain open.

Each captured selector takes the value of `family` from the packed
Joint morphology lookup. This supplies decimal IDs rather than dictionary
lemma strings for those selectors. The final v6 plan gives the Grammar
Profile and Grammar Revision Broad rows the same hashes as Grammar
Conservative. The
[source recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/tatoeba-detailed-preparer-recovery.json)
binds five captured sources to nine direct corpus paths and four identical
alias bindings. The original detailed-export row payloads remain open.

## 2026-11-24 original Tatoeba exclusion manifests

| Recovered manifest | Source of verification | Exclusion bindings |
| --- | --- | ---: |
| [Supervised v2](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/supervised-v2-manifest.json) | Complete original command output and the [Tatoeba import receipt](2026-10-27-tatoeba-history-evidence.json) | 33 |
| [Grammar-focused](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/grammar-focused-manifest.json) | Original selection code and the [infinitive revision receipt](2026-10-26-infinitive-revision-offline-evidence.json) | 47 |
| [Noun-case v3](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/noun-focus-v3-manifest.json) | Original selection code and the [noun-case training receipt](2026-10-26-noun-case-training-evidence.json) | 56 |

All three manifests match their original file SHA-256 values. The
grammar-focused manifest carries forward all 33 supervised exclusions
and verifies 32 excluded packed-morphology families using the exact
authored profile corpus. The original generator sorts paths as path
components. Sorting their serialized strings produced a different
manifest digest. The noun-case v3 manifest carries forward all 47 grammar
bindings and matches the independently recorded SHA-256 of its 56-entry
binding map.

These are the original manifests and exclusion maps. This recovery has no
new natural row payloads. The focused-v2 plan's additional broad-v2 and
instrumental row bindings and the final v6 JSONL remain open.

### Byte-exact CC0 split and training counts

The [CC0 restoration command](../../tools/typing_experiments/restore_historical_tatoeba_cc0.py)
rebuilds the original Russian sentence split and train-only bigram counts from
the pinned October 24 archive. It verifies the lock, archive and decoded
source before replaying the original NFC normalization, normalized-sentence
deduplication, seeded split and token-pair counting.

Both output digests match the original lock. The split has 18,497 train,
2,335 calibration and 2,245 holdout rows, and matches the earlier exclusion
binding in the v6 parent plan. The counts match the original v5/v6 model
lineage. The command retains these bytes in a new ignored build directory.
The separate historical detailed Russian export remains open.

### Exact CC0 context-feature conversation corpus

The [captured original builder](../../tools/typing_experiments/historical_provenance_sources/context_feature_conversation_preparer.py)
was replayed against the restored CC0 split and the pinned frequency list,
packed Russian morphology and Joint corruption helpers. It reproduced both
row files and the original manifest. The [receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/tatoeba-cc0-context-feature-recovery.json)
binds their bytes against the original Tatoeba receipt and both row files
against the v6 parent plan.

The two parts contain **4,444 rows** across 546 calibration and 565
holdout source sentences. The historical `family` fields are packed decimal
morphology IDs. They do not intersect the dictionary lemma strings used for
v6 family exposure. The restored JSONL files remain local. No model ran.

### Exact supervised conversation v2 corpus

The [original v2 builder](../../tools/typing_experiments/historical_provenance_sources/conversation_supervised_v2_preparer.py)
was recovered from its creation and subsequent patch commands. Its source
SHA-256 and the existing split guard match the original manifest. The
replay read the exact CC0 split and reproduced the original scopes of
9,962 excluded sentences and 35,346 excluded target contexts from 33 input
bindings. The raw bytes of six Wikipedia inputs were unavailable, so the
replay used their existing digest-bound article and context indexes.
The 120-row authored input was only reconstructed in memory for this step.

The replay removed the original 199 cross-partition prediction contexts.
The train, calibration and holdout files contain 22,527, 3,204 and 3,172
rows, respectively. All three JSONL files and the manifest match their
original SHA-256 values. The [receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/tatoeba-supervised-v2-recovery.json)
binds those digests and the original generation guards. All declared
families are packed morphology IDs. The JSONL data remain local. No model ran.

### Exact early Wikipedia Context Feature rows

The original article, target-context and source-window registry keys
located the selected terms in the pinned 0020 Wikipedia shard. The replay
applied the original packed morphology, family partition, prefix and
variant rules. In calibration, 601 compatible source candidates resolved
to 600 distinct families. Taking the lowest original selection hash per
family produced the original row order and hash. All 1,000 holdout
families had one compatible candidate.

The [recovery receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/early-wikipedia-context-feature-recovery.json)
binds both original JSONL files to the 2026-10-27 legacy context receipt
and the final v6 parent plan. Their 3,563 and 5,906 rows carry only packed
morphology IDs in `family`. The
[captured preparer](../../tools/typing_experiments/historical_provenance_sources/context_feature_wikipedia_preparer.py)
includes both recorded historical edits. An independent source hash remains
open. Row data are retained locally.

The [reconstructed original manifest](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/early-wikipedia-context-feature-manifest.json)
matches its historical SHA-256. It binds 28 original paths to verified row
bytes from the archived Refinement fixture, seven spelling holdouts, the
Joint and Rare Ranking replay, and the two recovered Word Context
corpora. The historical candidate paths shared the same bytes as the
concatenation of the archived train, dev and test row files.

## 2026-11-24 v6 holdout article availability

The holdout TSV was reopened and matched its original decoded SHA-256.
The holdout source index spans all 7,750 rows in 1,630 contexts and matches
the complete set of 1,614 registered Russian Wikipedia article IDs. Its
SHA-256 is
`d56fb9d7fa167f599e8414dac7190a057a2a7667ad3cad07694dbe3c850e03eb`.
The current [Russian Wikipedia API](https://ru.wikipedia.org/w/api.php)
accounted for every ID. All 1,602 returned pages were in the main namespace.

| Current result | Articles | Historical contexts | Historical TSV rows |
| --- | ---: | ---: | ---: |
| Missing by original article ID | 12 | 12 | 58 |
| Original ID is now a redirect | 4 | 4 | 19 |
| Current article transcludes the queried copyright-violation template | 0 | 0 | 0 |

Missing IDs: `6724762`, `7121163`, `7452977`, `8245986`, `8345062`,
`8441629`, `8717920`, `9744441`, `10024630`, `10138404`,
`10323497`, `10355886`. Redirect IDs: `8249990`, `8455978`,
`9028215`, `9241368`.

The [holdout snapshot map](../../tools/typing_experiments/available-v6-article-origin-v1/holdout-attribution/articles.jsonl)
now supplies the original title and URL for every article. The reconstruction
checked the size and SHA-256 of each of the ten locked Parquet shards before
reading the ID, title and URL columns. It verified each hash again after
the scan and accounted for 926,220 source records. The
[receipt](../../tools/typing_experiments/available-v6-article-origin-v1/holdout-attribution/receipt.json)
binds the map to the source index and the exact decoded TSV digest.
For all records, the original title matches the decoded URL path. The
current title differs for 45 available articles, affecting 46 contexts
and 217 TSV rows. Looking up the snapshot titles of the 12 missing IDs
found two current pages and ten still-missing titles. All four redirect
titles resolve to current destination pages. These lookups establish
current destinations. Historical revisions and passage-level attribution
still require verification.

The API also accounted for the associated discussion titles of all 1,602
available IDs. Of these discussion pages, 679 were missing. The translated
article template appeared on 266 discussions, covering 267 historical
contexts and 1,261 TSV rows. No current discussion transcluded the queried
copyright-violation or VRTS template. Historical discussion revisions,
translation sources and article-specific conditions remain open.

## 2026-11-24 historical holdout translation notices

For the 266 holdout articles with a current translation notice, the review
queried the newest available associated discussion revision at or before
`2023-11-01T23:59:59Z`. Wikimedia returned historical wikitext for 262
discussions. The projection recovered 251 notices on 243 articles, covering
244 original contexts and 1,155 exact holdout TSV rows. It records page and
revision identifiers, timestamps, language codes and article titles.
[Holdout translation-source receipt](../../tools/typing_experiments/available-v6-article-origin-v1/holdout-attribution/translation-sources.json)

The notices named 41 distinct numeric revisions across source and receiving
sites. Of 30 source references, 23 matched the named article, two resolved to
the same article through title resolution, and five pointed to a different
article. Of 12 receiving references, ten matched the receiving article and
two were unavailable. The receipt preserves those outcomes. Another 24
source-version fields and eight receiving-version fields could not be
projected to numeric revision identifiers.

The initial candidate set comes from current notices, so it can omit notices
removed before the current scan. The discussion revision identifies the
notice, while the original excerpt's exact revision and passage-level origin
remain unverified. Publication rights remain open.

### Exact early Wikipedia Word Context corpora

Replay from the pinned Wikipedia shards `0018.parquet` and `0019.parquet`
recovered all 14,508 rows. Word Context has 3,648 rows in each partition.
Word Context Extra has 3,636 calibration rows and 3,576 holdout rows. All
four original JSONL SHA-256 values match the legacy context-history receipt
and the successor v6 plan. Both original manifest SHA-256 values also match
the legacy receipt. Each partition has 500 distinct historical family keys.
The four article sets and four family-key sets are pairwise disjoint.

The two preparers were recovered from the original source creation and
modification commands. Their archived digests are recorded separately from
the verified output digests. The preparers use packed morphology IDs or
explicit `form:` keys when there is no unambiguous lemma. The latter account
for 346 family keys in Word Context and 364 in Word Context Extra. The row
files are retained in the ignored local recovery directory. This was a
historical recovery with zero model calls.

### Historical Word Context training-count sources

The October 25 command capture gives the original Wikipedia training-count
procedure, its indexed prefix-tail exclusion patch and the binary packer.
The archived source digests are recorded alongside independent output
digests from the v5/v6 training lineage and the earlier Word Context
acceptance record. The historical log counted 416,186 included articles,
38,933,219 adjacent tokens and 1,999,683 pairs before applying the
500,000-row packing cap. The full replay reproduced all three totals
using nine hash-verified Wikipedia shards and 23 verified earlier row
inputs. The 500,000-row `model-counts.jsonl` and the 4,558,118-byte
`ru-word-context.bin` each match their independently recorded original
SHA-256. The [replay receipt](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/word-context-v3-replay.json)
records the two matches and the full intermediate count digest. That
intermediate digest identifies the replay output. The original evaluation
rejected the packed Word Context model. Replay used zero model calls.

## 2026-11-24 byte-exact final available-clean v6

A replay of the original parent selector read all ten pinned Wikipedia
shards. It accounted for 926,220 scanned articles, 844,368 eligible articles
and the historical 19,954-article exclusion index. The parent's availability
bytes match the original. The SHA-256 of its 3,293 selected contexts matches
`recordsSha256` in the [recovered original clean plan](../../tools/typing_experiments/historical_provenance_sources/v6-inputs/available-clean-v6-plan.json).
That plan also independently confirms the original clean preparer digest.

The replay helper wrote both parent files before its optional TSV preview
failed on an incompatible tuple shape. The maintained restoration command
then exited zero, independently matched all five historical hashes, and
emitted both JSONL files, both TSV files and the clean plan. Calibration
contains 7,905 rows across 1,661 contexts and holdout contains 7,750 rows
across 1,630 contexts. The two original holdout exclusions removed ten
rows. A second invocation against the relocated parent passed all five
digest checks again.

The [recovery receipt](2026-11-24-q6-final-v6-recovery.json) records both
sets of input and output bindings. The complete texts remain in the
ignored local recovery directory. The historical full-cohort and calibration
qualification failures remain in force. The replay made zero model calls.
Rights and underlying article-revision attribution remain open.

### Exact v6 exclusion ledger entries

A fresh restoration from the retained parent matched all five original
output hashes again. Projecting every restored JSONL row through
`holdout_ledger.keys_for` gave exact set equality with the two original
partition entries on all four axes. Each comparison found zero missing
and zero extra keys.

| Partition | Rows | Articles | Families | Sentences | Contexts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration | 7,905 | 1,651 | 588 | 1,661 | 4,583 |
| Holdout | 7,750 | 1,614 | 523 | 1,630 | 4,481 |

The recovery receipt binds the tested ledger hash. The ledger validator
passed with 229 entries and reported incomplete global freshness
coverage. All 51 tests matching `test_available_v6*.py` passed. The
temporary restoration output was removed.

### Control exclusions for the three recovered corpora

The [control-ledger registration](../../tools/typing_experiments/register_recovered_corpus_controls.py)
verified all seven original JSONL digests before projecting 49,002 rows.
It checked each corpus against the current control ledger, including the
rejected conversation v1 entries, and added nine entries with the missing
keys. Every previous entry was preserved.

| Historical corpus | Rows | Context keys added | Surface keys added | Source keys added |
| --- | ---: | ---: | ---: | ---: |
| Supervised Conversation v2 | 28,903 | 1,813 | 1,249 | 290 |
| Context Feature | 4,444 | 4,431 | 2,448 | 1,111 |
| Available Clean v6 | 15,655 | 12,352 | 3,946 | 2,866 |

A second pass checked that no key was still missing. The nine-entry
canonical SHA-256 is
`a06dd031d14fe8de1f3c58afabb430e9825a438cfa4ba7d9de6f42b14c1e8e81`.
A source-only test checks the entries without needing the recovered
corpus files. The legacy protected-control test verifies the nine original
language/version entries by identity, alongside the new corpus exclusions.
The registry retains its incomplete global coverage status.

### Exact v6 rows affected by article overlap

The [row audit](../../tools/typing_experiments/audit_available_v6_article_rows.py)
verified the historical SHA-256 of both restored partitions and checked that
their article keys exactly equal the corresponding ledger entries. It counted
every affected row, including repeated variants of the same source context.
The broader comparison uses the 239-entry ledger and excludes the two v6
partitions and their direct parent.

| Scope | Calibration articles / contexts / rows | Holdout articles / contexts / rows |
| --- | ---: | ---: |
| Spelling history | 122 / 125 / 596 | 131 / 134 / 646 |
| Neighbor history | 26 / 27 / 133 | 25 / 25 / 120 |
| Spelling or neighbor history | 140 / 144 / 690 | 144 / 147 / 710 |
| All other registered sources | 304 / 308 / 1,469 | 289 / 293 / 1,402 |

Two runs produced byte-identical [numeric receipts](2026-11-24-q6-v6-article-row-overlap.json)
with per-group totals and the input, audit-source, and ledger digests. The
audit made zero model calls. The broader overlap measures current registered
exposure, including later disclosures. Fresh qualification and article-revision
attribution remain open.

### First historical revision-content witnesses

The published Wikipedia snapshot exports a page ID, URL, title and cleaned
text. The [pinned Wikimedia cleaner](https://huggingface.co/datasets/wikimedia/wikipedia/blob/b35d406bd9e81f08c68e7bf95d130d2f506dfe77/wikipedia.py)
reads text from the dump revision and omits its revision ID from the
exported records. The official dump and the Academic Computer Club mirror
returned HTTP 404 for the old `ruwiki/20231101/dumpstatus.json` path. The
Internet Archive identifier query also found no `ruwiki-20231101` item.
[Dataset schema and cleaning notes](https://huggingface.co/datasets/wikimedia/wikipedia#dataset-structure)

The [pilot receipt](2026-11-24-q6-v6-revision-content-pilot.json) binds the
original Parquet bytes for shard `0011`, the recovered page map and the
published cleaner. It selected 16 calibration and 16 holdout articles by
a deterministic hash order. The [MediaWiki revisions API](https://www.mediawiki.org/wiki/API:Revisions)
returned eight readable revisions per article at or before
`2023-11-03T00:00:00Z`. Replaying the Russian cleaning path with
`mwparserfromhell` 0.6.5 produced byte-exact full-article matches for all
32 articles. Of the 256 compared revisions, 76 reproduced the snapshot.

| Partition | Articles with one match in the query window | Articles with multiple matches |
| --- | ---: | ---: |
| Calibration | 9 | 7 |
| Holdout | 7 | 9 |

The receipt keeps all matching revision IDs and timestamps, with scope limited
to the returned window. In 31 cases the API also reported earlier revisions.
The matching revision IDs supply content witnesses for attribution. The
original XML dump revision IDs and passage-level licensing remain open. The
Parquet copy, API response bodies, and temporary environment were removed.

### Full revision-content check for shard 0011

The [first-shard receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0011/receipt.json)
extends the same check to all 355 mapped v6 pages in `0011.parquet`.
It reused the 32 pilot results after checking their snapshot text digests
against the shard. The other 323 pages were queried serially, with a
maximum of eight revisions per page. Across 2,816 readable revisions,
947 produced a full cleaned-text match. Every page has a matching
revision at or before `2023-11-01T23:59:59Z`. The API advertised older
continuation data for 338 pages.

| Partition | Articles | Exact v6 rows | Contexts | One match in queried window | Multiple matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration | 193 | 919 | 193 | 70 | 123 |
| Holdout | 162 | 773 | 163 | 56 | 106 |

The [witness map](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0011/articles.jsonl)
retains public page and revision IDs, timestamps and snapshot digests.
The original XML dump revision IDs, the other nine shards and article-specific
distribution review remain open. The temporary shard, parser environment
and response bodies were removed.

### Complete revision-content check for shard 0012

The [second-shard receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0012/receipt.json)
binds all 292 indexed pages from `0012.parquet`. Of 2,314 readable revisions,
794 reproduced the complete cleaned snapshot text, with at least one match
by the dump date for every page. Within the eight-revision query window,
87 pages had one match and 205 had multiple matches. These pages account for
673 calibration rows (142 contexts) and 721 holdout rows (153 contexts) in
the previously byte-verified v6 JSONL files.

Across shards 0011 and 0012, the public witnesses cover 647 pages and 3,086
v6 rows. The original dump revision identity and passage-level licensing
remain open. The [shard recovery command](../../tools/typing_experiments/recover_v6_revision_witnesses.py)
checks the pinned public article index, source bytes and cleaner before
writing matching revision metadata and digests.

### Revision-content check for shard 0013

The [0013 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0013/receipt.json)
accounts for all 327 indexed pages. Exact-text witnesses at or before
the dump date cover 324 pages. The MediaWiki API reported three original
page IDs missing. All three are in the calibration partition and account for
three contexts and 15 rows. The holdout side has witnesses for all 158 pages
and 756 rows. Across the shard, the check compared 2,533 readable revisions,
found 850 matches and retained multiple matches for 202 pages.

The [offline verifier](../../tools/typing_experiments/check_v6_revision_witnesses.py)
checked each shard's digests, page and partition identities, and revision IDs
against the pinned index. Across the first three shards, it accounted for
974 pages, including 971 with exact-text witnesses covering 4,639 historical
rows. The missing pages, exact dump identities, and distribution rights remain
open.

#### Archived leads for the three missing 0013 pages

The [archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0013/archive-exceptions.json)
binds the three original page IDs to publicly available Wayback captures.
All three captured HTML responses contain the original numeric page ID.
The August and October 2021 captures display revisions `79987682` and
`102002002`. The December 2024 capture returned no displayed revision.

For the two displayed revisions, the check verified the replay HTML digests
again and selected the ordinary `correct` row from each exact v6 context
group. The visible article text contained the normalized right context of
both rows. Neither capture matched the complete recorded source window or
its left context. These are passage leads for two contexts and ten v6 rows.
The three pages remain outside the full-text witness count.
[Wayback availability API](https://archive.org/help/wayback_api.php)

### Revision-content check for shard 0014

The [0014 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0014/receipt.json)
accounts for all 345 indexed pages. Of 2,693 readable revisions, 882 matched
the full cleaned Parquet text. A matching revision by the dump date was
available for 344 pages, covering 881 calibration and 771 holdout rows.
The remaining holdout page was missing by its original ID and accounts for
four rows in one context.

The offline verifier matched both original corpus digests and projected the
first four shard results onto their rows. It counted 1,315 pages with a
full-text witness by the dump date, covering 3,270 calibration and 3,021
holdout rows. Four missing pages account for 19 rows. The other six shards,
original dump identities, and distribution review remain open.

The [0014 archive exception receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0014/archive-exceptions.json)
binds the missing holdout page to the December 14, 2023 Wayback capture
displaying revision `122857447`. The capture contains the original page ID
and the complete normalized source window from the `correct` variant.
This supplies an attribution lead for the one context and four rows. The
full Parquet article comparison and the original dump revision ID remain open.

#### Translation notices on pages with full-text witnesses

The [overlap receipt](2026-11-24-q6-v6-translation-witnesses-0011-0014.json)
binds the first four witness maps, both translation-notice receipts and both
historical JSONL files. Its article sets reproduce the same context and row
counts when projected through the tracked source indexes.

| Partition | Pages with both a notice and a by-date witness | Contexts | Historical rows |
| --- | ---: | ---: | ---: |
| Calibration | 73 | 74 | 354 |
| Holdout | 81 | 81 | 382 |

The 736 rows have evidence for the receiving article text and a historical
translation notice. Passage-level attribution and distribution terms still
require review. The notice screen began with notices visible at the time of
collection, so the overlap measures the recorded notices only.

### Revision-content check for shard 0015

The [0015 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0015/receipt.json)
accounts for all 335 indexed pages. It compared 2,578 readable revisions and
recorded 804 full-text matches. By-date witnesses cover 332 pages and 1,612
rows. The API returned three original page IDs missing. They account for one
calibration context, two holdout contexts, and 15 total rows.

Across five shards, the exact corpus projection found full-text witnesses for
1,647 pages and 7,903 rows. Seven unavailable IDs account for 34 rows. The
checker lists the individual exceptions by public page ID and partition.
The remaining shards, original dump identities, and distribution review
remain open.

The [0015 archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0015/archive-exceptions.json)
confirms the full normalized holdout source window for revision
`133007996`, covering five rows. The other holdout capture has the
original page ID but no matching window. The calibration page yielded
no indexed capture under the article title, mobile title or numeric
page URL.
[Wayback availability API](https://archive.org/help/wayback_api.php)

### Revision-content check for shard 0016

The [0016 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0016/receipt.json)
accounts for all 366 indexed pages. The check compared 2,801 readable
revisions and recorded 917 full-text matches. By-date witnesses cover
364 pages, 876 calibration rows and 869 holdout rows. Two original page
IDs were missing, affecting two calibration contexts and ten rows.

The offline check binds both restored corpus partitions to their original
digests. Across six shards, 2,011 of 2,020 indexed pages have by-date
witnesses, covering 4,967 calibration and 4,681 holdout rows. Nine missing
page IDs account for 44 rows. Four shards, original dump revision
identities and distribution review remain open.

The [0016 archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0016/archive-exceptions.json)
binds both missing page IDs to Wayback captures. The August 4, 2023
capture displays revision `124277971`, and the May 21, 2025 capture
displays revision `140612442`. Both contain the complete normalized
source window from the calibration `correct` variant, accounting
for the two contexts and ten rows. These windows establish passage
matches separately from the full cleaned article check. The original
dump revision IDs and distribution rights remain open.
[Wayback availability API](https://archive.org/help/wayback_api.php)

Run `check_v6_revision_witnesses.py --corpus <exact-v6-corpus>` to
recompute each retained shard's calibration and holdout counts. The
verifier checks both corpus digests in every retained receipt, even
when the exact corpus files are unavailable. With the corpus supplied,
it also rejects a changed row, context or article count.

### Revision-content check for shard 0017

The [0017 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0017/receipt.json)
accounts for all 354 indexed pages. The check compared 2,623 readable
revisions and recorded 815 full-text matches. By-date witnesses cover
349 pages, 776 calibration rows and 877 holdout rows. Four original
IDs were missing, affecting 20 rows. One calibration page yielded
eight readable revisions without a full-text match and accounts
for five rows.

Across seven shards, 2,360 of 2,374 indexed pages have by-date witnesses.
They cover 5,743 calibration and 5,558 holdout rows. Thirteen missing
page IDs account for 64 rows, and the remaining unmatched page for
five rows. Three shards, original dump revision identities and
distribution rights remain open.

The [extended 0017 history check](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0017/extended-history.json)
started at the end of the dump day and compared 32 readable revisions
of the one unmatched page. Revision `132298731` from August 11, 2023
matches the pinned full cleaned text SHA-256. An independent request
by revision ID confirmed the page, timestamp and digest. The exact
calibration corpus binds this result to one context and five rows.
Including this separate check, seven shards now have by-date full-text
witnesses for 2,361 pages and 11,306 rows.

The offline verifier pins the extended receipt and checks that it
binds the unmatched page, snapshot digest and restored partition.
`checked` retains the original bounded-query counters.
`byDateWitnessArticles` and the exact corpus projection include
verified extended history. Archived passage-only checks retain their
own receipts.

The [0017 archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0017/archive-exceptions.json)
confirms the original page IDs for all four missing pages. Three
captures display revision IDs and permit a visible-text comparison
within the article body. The capture displaying revision `120576649`
contains the complete normalized holdout source window for five rows.
Two other captures match the right context only, covering two contexts
and ten rows. The fourth capture lists a current revision ID in its
metadata but displays no revision. No full cleaned article witness is
inferred from these passage checks.
[Wayback availability API](https://archive.org/help/wayback_api.php)

### Revision-content check for shard 0018

The [0018 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0018/receipt.json)
accounts for 343 indexed pages. The check compared 2,499 readable
revisions and retained 881 matching revisions. By-date witnesses cover
340 pages, 816 calibration rows and 812 holdout rows. Three missing
pages account for nine calibration rows and five holdout rows.

The offline check now finds by-date full-text witnesses for 2,701 of
2,717 indexed pages across eight shards, including the extended 0017
history. That covers 6,564 calibration and 6,370 holdout rows. Sixteen
missing pages account for 78 rows. The last two shards account for
2,643 rows awaiting the full-text check.

The [0018 archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0018/archive-exceptions.json)
confirms both missing calibration source windows, covering nine rows.
The holdout capture displays a different page ID. The March 11, 2024
move log associates that ID with the original page but supplies no
source-window evidence for its five rows. All three pages remain
outside the full cleaned article count.
[Wayback availability API](https://archive.org/help/wayback_api.php)

The offline verifier's `archivePassages` section lists the pinned
archive outcomes separately from full cleaned article witnesses. With
the exact v6 corpus supplied, it recomputes the article's context and
row counts and verifies each receipt's corpus and capture bindings.
Across the first eight shards, the archive checks account for all
16 pages missing from the live API. Seven pages have complete source
windows for 33 rows. Four pages have right-context-only matches for
20 rows. The other five pages account for 25 rows.

### Revision-content check for shard 0019

The [0019 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0019/receipt.json)
accounts for all 342 indexed pages. The check compared 2,460 readable
revisions and retained 812 matching revisions. By-date witnesses cover
338 pages, 788 calibration rows and 851 holdout rows. Four unavailable
pages account for 14 calibration rows and five holdout rows.

Across nine shards, 3,039 of 3,059 pages have by-date full-text witnesses,
including the separately verified early revision from 0017. They cover
7,352 calibration and 7,221 holdout rows. Twenty unavailable pages
account for 97 rows. The last shard covers the remaining 985 rows.

The [0019 archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0019/archive-exceptions.json)
confirms complete calibration source windows for nine rows from two
missing pages. A holdout capture matches the left context only
for five rows. The availability query returned no indexed capture for
the fourth page, also accounting for five rows. Across nine shards,
the archive checks now confirm complete source windows for 42 rows
from nine missing pages.
[Wayback availability API](https://archive.org/help/wayback_api.php)

### Revision-content check for shard 0020

The [0020 receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0020/receipt.json)
accounts for all 206 indexed pages. The check compared 1,346 readable
revisions and retained 410 matching revisions. By-date witnesses cover
200 pages, 485 calibration rows and 471 holdout rows. Six unavailable
pages account for 29 rows.

The offline audit with `--require-all --corpus` verifies all ten
pinned shards and both original corpus digests. The 3,239 pages with
by-date full-text witnesses cover 7,837 calibration and 7,692 holdout
rows, for 15,529 of 15,655 historical rows. The remaining 26 live-API
exceptions cover 126 rows. This checks cleaned revision content and
preserves the scope of the original dump identity and distribution
review as open.

The [0020 archive receipt](../../tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0020/archive-exceptions.json)
confirms one complete holdout source window covering five rows. One
other capture contains the original page ID but displays no revision.
The other four title queries returned no indexed capture. Across ten
shards, ten missing pages have complete archived source windows
covering 47 rows. The rest of the live-API exceptions account for 79
rows without either full-text or complete archived source-window evidence.
[Wayback availability API](https://archive.org/help/wayback_api.php)

The [complete translation overlap receipt](2026-11-24-q6-v6-translation-witnesses-0011-0020.json)
binds the ten standard witness maps, the extended history, the
archive receipts, both translation notice maps and both exact
corpus partitions. Every page in the recorded historical notice
maps has a receiving-article full-text witness by the dump date.
This covers 217 calibration pages and 1,035 rows, and 243 holdout
pages and 1,155 rows. The earlier notice collection determined
which notices were observed. The originating passage and terms
of distribution still require review.

### Recovered ancestry exclusions

The [historical importer](../../tools/typing_experiments/import_recovered_v6_history.py)
checks the original v6 parent and clean plan bindings before reading
the recovered payloads. It also verifies the Diagnostic Rare Ranking
manifest against the parent plan and the recovery receipt. The importer
writes a separate ledger file and refuses changed input bytes.

| Historical input | Rows | Articles | Families | Sentence keys | Context keys |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fresh Matched v5 | 45 | 45 | 43 | 45 | 45 |
| Reliable Side v5 | 1,690 | 1,690 | 883 | 1,690 | 1,690 |
| Sentence Corpus v6 | 2,068 | 2,068 | 755 | 2,068 | 2,068 |
| Sentence Pairs v2-v6 | 3,293 | 3,267 | 1,111 | 3,293 | 3,289 |
| Diagnostic Rare Ranking calibration | 4,760 | 486 | Pending | Pending | 1,000 |
| Diagnostic Rare Ranking holdout | 4,788 | 478 | Pending | Pending | 1,000 |

The new entries add 4,334 article, 49 family, 3,798 sentence and
5,796 context keys beyond the prior registry union. The resulting ledger
has 235 entries. Its SHA-256 is
`24e0aa9f5ae3a8cb25a0f91e8cfdfb9b13550400f47bbb41236bfb37591b8212`.
All 229 prior entries and the global coverage status are preserved.
The four selection inputs use their original context hashes for the
historical sentence axis. Rare Ranking still requires separate
packed-family and sentence provenance work. The original qualification
failures remain in force.

Fresh Matched, Reliable Side, Sentence Corpus and both Rare Ranking
partitions have zero article intersection with the final corpus.
The direct parent, Sentence Pairs, contains all 3,265 final article
identities. The historical overlap check compares the final corpus
with entries outside this parent. The target check validates the six
additions before reconstructing its older ledger hash.

### Diagnostic Rare Ranking source windows and family exclusions

Both exact Rare Ranking partitions trace to the pinned Wikipedia shard
`0020.parquet`. The packed morphology file reproduced the numeric
family assignment for each of the 1,000 distinct source words. All
1,000 article, word and prefix combinations identified a single
matching historical selector window. A separate projection through
the pinned Pymorphy dictionary found analyses for all 9,548 rows.

| Partition | Source windows | Dictionary families | Unresolved rows |
| --- | ---: | ---: | ---: |
| Calibration | 500 | 502 | 0 |
| Holdout | 500 | 503 | 0 |

The [importer](../../tools/typing_experiments/import_recovered_rare_ranking.py)
binds both projections to the original diagnostic entries. It adds
four entries with 1,000 new historical sentence-window keys and 45 new
dictionary family keys. The numeric ID checks and the dictionary
projection preserve their respective family definitions.

Two runs regenerated the same [recovery receipt](2026-11-24-q6-rare-ranking-exclusions.json)
and ledger bytes. The ledger now has 239 entries and SHA-256
`db1093ede1b0fcfebf9112bec83a135eaf92d694ee89d344d3d65545702cac77`.
The importer made zero model calls. Global freshness and independent
qualification remain open.
