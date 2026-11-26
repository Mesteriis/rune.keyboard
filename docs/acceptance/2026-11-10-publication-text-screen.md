# Preliminary publication screen of changed text

At clean source `7da494926141`, compared with local `origin/main`
`2c1ff9751e74`, a read-only search inspected 1,205 added or modified files
that existed in the checkout, were at most 1,000,000 bytes, were not in a short
binary-extension exclusion list and did not contain a NUL in the first 8 KiB.
The search examined the entire selected files, not just added lines. It looked
for common PEM private-key headers, `/Users/<name>/` paths and the known Fold
ADB serial. It printed matching filenames, not matched payloads.

No selected file contained the searched key headers or serial. One file,
`tools/test_verify_packaged_native.py`, contained `/Users/` paths: inspection
confirmed they are synthetic negative-test inputs with a fictional `private`
user, used to verify that packaged native paths are refused. No file was
changed as a result of this screen.

This narrow search is not a secret scan, binary inspection, history audit or
release approval. It excludes files over 1 MB, specified binary extensions,
files with an early NUL, deleted files, untracked files, other path shapes,
other identifiers and credentials without the searched key headers. The large
registries, APK/native payloads, full change set and publication readiness still
require their own proportionate checks; hosted CI and independent acceptance
remain open.

## Large-file follow-up

The same three patterns were checked in 17 changed files larger than 1 MB
(145,918,255 bytes total) whose first 8 KiB contained no NUL. Files were read
in 1 MiB chunks with overlap, and no pattern matched. One additional large
file was excluded by that NUL check: the retained compressed English Tatoeba
source. A streaming BZip2 read examined its 4,735,999 decompressed bytes with
the same patterns and found no match; no extracted copy was written. Its
compressed SHA-256 `a144a0c52f8be13bee7cc30eb109eb5836803f22128a8ef8376c1ca5c6c5cf8a`
matches the repository source lock. This repeat used the unchanged source tree
at `07f50a2d` except for this documentation addition. The narrow pattern and
history, deletion and untracked-file limitations above remain.

## Remaining selected binary files

The same changed-file inventory contained two binary or binary-extension files
at or below 1 MB. Streaming the retained Russian Tatoeba BZip2 source produced
3,015,831 bytes; the same three patterns had no match, and the compressed
SHA-256 `982264e0857d2574ada9d1c07897e816ab9c4a8fb139f05320b5836f53d4d7ed`
matched its source lock. No extracted copy was written. Visual inspection of
the changed distribution PNG showed the Rune home screen with an empty typing
field and generic status icons; its PNG chunks contained no text or EXIF chunks.
This is a visual and basic metadata check, not proof of all possible image
metadata or of source rights. Other scope limitations above still apply.

## Full unpublished-history secret-scan repeat

At clean source `479dd429` the live `origin/main` was still `2c1ff975`;
`main` was 615 commits ahead. Gitleaks 8.30.1 scanned the Git range
`origin/main..HEAD` using default rules, a 10 MB per-target limit, no archive
traversal and redacted reporting. It exited 1 with 21,800 `generic-api-key`
findings across 49 paths and 55 commits. Counts are findings, not unique values
or confirmed secrets; the earlier 74-finding result was at an older source.

A local structural screen loaded each reported commit/path with `git show`
and used the reported line and column bounds. In 21,721 findings the reported
range overlapped a 64-character lowercase hexadecimal JSON value in a named
field: 9,876 `sentenceKey`, 6,570 `targetKey`, 3,256 `articleKey`, 2,014
`surfaceKey`, and five other explicitly named digest fields. These fields are
associated with public-source exclusion and evidence data, but shape and field
name alone do not prove that every value is non-secret or releasable. The
other 79 findings did not meet this structural criterion; 76 of their lines
contain a 64-character hexadecimal sequence and three do not. They remain
unresolved and require direct review. No actual finding values or report were
retained in this receipt; the temporary report was removed.

This is not publication approval, a license audit, an archive/binary inspection
or proof that unflagged content is safe. Objects beyond the target size limit,
archives, private content that does not match the scanner and all unmatched
secrets remain outside its coverage. The latest published hosted CI run for
`2c1ff975` remains failed; this local scan did not trigger hosted CI.

## Follow-up on the 79 remaining findings

The same fixed range `origin/main..479dd429` was rescanned with the same
Gitleaks settings and again produced 21,800 findings and exit 1. For the 79
outside the initial named-field screen, the reported range overlapped a
64-character hexadecimal value in 76 cases; three did not. Of the 76, 72 were
in JSON, two in Python and two in Markdown.

A read-only cross-check recursively located the 72 JSON values in their
historical objects and treated their parent keys as candidate repository paths.
For 56 findings, the SHA-256 of that tracked file at the same commit exactly
matched the value. Sixteen could not be connected to a tracked file by this
method. The two Python, two Markdown and three non-hex findings were not
resolved by the file-hash cross-check. Thus 23 of the original 79 remain
unresolved by this check; the 56 matches establish the relationship to tracked
bytes, not the safety or licensing of those bytes. The 21,721 named-field
findings retain the separate structural-only limitation above.

The redacted temporary scan report was removed after analysis. Archive
contents, large targets, other disclosure risks and hosted CI remain open; this
is not permission to publish. No values from findings were printed or retained.

## Targeted provenance checks for remaining findings

A targeted Gitleaks rescan of the relevant historical files was performed in a
mode-0700 temporary directory. Its protected report allowed exact value
comparisons locally; no values were printed or copied into this receipt. Of the
23 findings previously unresolved, 18 received further provenance checks:

- Fifteen occurrences were one SHA-256 value matching a Python file in the
  `pymorphy3==2.0.6` wheel. The downloaded wheel itself matched the hash pinned
  in `tools/morphology/requirements.lock`. The similarly pinned dictionary-only
  wheel did not contain that file; the successful match was in the main package.
- One value matched the SHA-256 of the tracked `english_family_keys.py` source
  in the current checkout.
- Two constants named `KEYS_SHA` are checked against serialized family-key
  lists by their respective importers. Both current `--check` commands passed,
  checking 7,903 and 2,503 family keys respectively.

At that point five values remained: four hexadecimal values in historical
Markdown and one 20-character identifier in the review plan. The original
classification of all four as APK hashes was incorrect; the follow-up below
corrects it. The old artifact bytes were not recovered or checked at this step,
and the identifier's origin was not established. The targeted scan
also repeated two findings already linked to tracked files in the preceding
section, so its 23 reported findings are not the same set as the earlier 23.
Two additional Markdown findings were checked separately to cover that gap.
An initial local analysis script failed due to a type error; the corrected
script completed. The report and downloaded wheels were removed.

These checks concern value provenance only. They do not verify the safety or
licensing of all referenced content, the 21,721 structurally screened findings,
archives, large targets, or hosted CI, and do not authorize publication.

## Correction and identifier follow-up

The 20-character identifier is a navigation-receipt slug in the plan. A
read-only check of the Git tree at the finding's commit found exactly one
corresponding dated article under `docs/acceptance`; it is not an authentication
credential. No identifier value was retained in the audit output.

The four historical hexadecimal values were reclassified from their actual
source context: the two in the confirmed-words receipt are API 26 and API 37
test-log SHA-256 values; the two in the U18 receipt are debug and test APK
SHA-256 values. The previous paragraph's initial description of all four as
APK hashes was wrong. A filename inventory in the `build/` directories of the
canonical checkout and the other Rune worktree found no corresponding named
logs or APKs; owner Fold backup directories were excluded. This filename search
does not establish that differently named artifacts or external backups do not
exist. None of these four original artifacts has been hash-verified here.

The redacted identifier-scan report was deleted. The Git history secret scan
still exited 1, and this result is not publication approval: the large
structural-only group, archive content, source licensing and hosted CI remain
separate open issues.

## Registry findings checked against retained provenance gates

At clean source `c621aca5`, the three available-v6 provenance checkers and the
Wiktionary and UniMorph historical exclusion `--check` commands all exited 0.
They verified, respectively, 3,265 article mappings, 3,307 context anchors,
6,584 target matches, 15,833 Wiktionary surfaces, and 644 UniMorph surfaces.
The v6 checks validate retained file/receipt and helper identities, article
keys against article IDs, sentence keys against retained context hashes, target
membership and source/partition links. The historical exclusion checks validate
their fixture identities, parent links and registry bindings. They do not
reconstruct all original text or prove independent qualification.

For each of the five large files accounting for 21,716 of the prior scan's
21,721 named-field findings, `git rev-list origin/main..479dd429 -- <path>`
reported one change commit and the same single blob as at `479dd429`. Thus the
checked files are the same versions introduced in that scanned range. The
finding totals count repeated field occurrences, not distinct hashes. This
connects those occurrences to checked public-data exclusion and recovery
fixtures; it does not independently prove that every underlying source has
publishable licensing, establish complete historical provenance, or verify the
five other named-field findings. No raw scan values were exposed or retained.
The earlier Gitleaks result remains a nonzero scan and should not be presented
as a clean secret scan.

## Archive history, source labels and streaming secret scan

At clean source `59468c82`, a filename inventory of the unpublished Git history
found two archive paths, the retained English and Russian Tatoeba CC0 `.bz2`
exports. Each path had one changing commit and one distinct retained Git blob
in the range. The current compressed files matched their committed source-lock
SHA-256 values; streaming decompression produced 4,735,999 English and
3,015,831 Russian bytes. The Russian decoded hash also matched its lock; the
English lock does not declare a decoded hash.

Each decompressed stream was independently piped directly to Gitleaks 8.30.1
with default rules and redacted output. Both scanners exited 0 with zero
findings; scanner reports were removed and no extracted copy was written. This
is narrower than a guarantee of no private text or credentials. The inventory
uses filename extensions and does not detect disguised or embedded archives.

The archive notices and locks label these specific sources CC0-1.0. Tatoeba's
[downloads page](https://tatoeba.org/ca/downloads) distinguishes its general
CC BY dataset from the CC0 subset, and its [CC0 contribution guidance](https://en.wiki.tatoeba.org/articles/show/cc0-contributions)
says CC0 is available for eligible original sentences. The locks preserve the
original CC0-export URLs and byte hashes, but this check did not independently
reconstruct the historical server response or verify each contributor's rights.
Other source licenses, the large registry contents, unflagged private material
and hosted CI remain open. This is not publication approval.

## Bounded scan of oversized registries

At clean source `faae84cb`, the two current tracked registries over the earlier
10 MB limit were screened without feeding the entire files to one scanner:
`holdout-ledger.json` (93,353,394 bytes) in 90 one-MiB blocks and
`control-ledger.json` (22,875,328 bytes) in 22 blocks, with 4,096-byte overlap.
Before each block was sent to Gitleaks 8.30.1 stdin with default rules, every
complete quoted lowercase 64-hex string was replaced with same-length spaces;
307,204 and 301,357 replacements respectively include overlap duplicates. All
block scans exited 0 and reported zero findings. Each file's SHA-256 was
identical before and after the scan. The temporary reports were removed.

This checks the remaining text only: masked hex values were not scanned and a
credential shaped like one would be missed. Block boundaries and finite overlap
can also miss matches that require more than 4,096 bytes of context; repeated
matches in overlap would not be independent findings. The prior provenance gates
cover specific public-data fixtures, not every value in these registries. This
is not a clean whole-history scan, a personal-data or license audit, or
publication approval; earlier nonzero Gitleaks results remain disclosed.

## Structural inventory of masked registry values

At clean source `b9ea9011`, both current registry files were parsed as JSON and
all exact lowercase 64-hex string values were counted by their structural path,
without printing values. The lexical registry contains 306,086 such values:
302,375 under key/surface collections or packed-key checksum fields, 3,657 in
binding maps and 54 in named metadata checksum fields. The control registry
contains 300,244: 299,710 under key/surface collections, 532 in binding maps
and two in named metadata checksum fields. Neither file contains a 64-hex JSON
property name; no values appeared outside these structural categories. Packed
base64 payloads are not included in these string counts. File SHA-256 values
were unchanged across inspection.

The current `holdout_ledger.load_ledger` and `control_ledger.load` validators
also exited 0, accepting 225 and 69 entries respectively, including their
packed-key checks where applicable. This is an inventory and schema/integrity
check, not independent provenance for each value: a credential placed in an
accepted binding field could still have the same form. The earlier block scan
explicitly masked these values, so no blanket clean-scan claim follows. The
prior public-fixture provenance checks and remaining publication limitations
still apply. Temporary numeric summaries were deleted.

## Registry binding provenance against current and historical files

At clean source `0068ca12`, the exact SHA-256 bindings in the current registry
binding maps were compared only with tracked files inside the checkout; no Fold
backups or untracked `build/` contents were opened. In the lexical registry,
1,825 references matched current tracked files, 224 differed, and 1,608 pointed
to paths under `build/` which are not tracked. In the control registry, the
corresponding counts were 485, 11 and 36. These are reference occurrences, not
unique files; the registry bytes were stable throughout.

For all 235 references that differed from their current tracked files, the
corresponding paths had 30 distinct expected hashes across 21 paths. A read-only
search of `git rev-list --all -- <path>` and 109 distinct blob versions found
an exact SHA-256 match for every reference. This proves the referenced bytes
exist in the local Git history, not that they are safe to publish or that their
licenses are sufficient. The 1,644 `build/` references were deliberately not
opened or checked; the temporary numeric summaries were removed. Packed key
payloads and other metadata fields were outside this comparison. Prior scanner,
license, source-lineage and hosted-CI limitations remain open.

## Recovery of build-path binding identities

At clean source `517baebd`, the 1,644 registry references to `build/` covered
277 distinct paths and 251 distinct expected SHA-256 values. All 277 paths were
missing or failed the regular-file, no-symlink, inside-build checks. Paths
containing `fold-owner` were excluded; no Fold backup was opened. This is a
check of those exact paths in the canonical checkout, not every backup or
alternate location.

A SHA-256 inventory of current tracked regular files then matched 20 of the
251 expected values, covering 161 references, at other tracked paths. The
matched references correspond to `.py` (79), `.json` (51) and `.bz2` (31)
files. It read 3,047 tracked regular files and skipped one non-regular or
unavailable entry. The other 1,483 references were not matched by this current
tracked-file inventory. Exact byte identity does not itself establish the
original use, complete lineage, data rights or safety of an artifact; no
historical corpus was reconstructed. The temporary numeric summaries were
removed and the registry files were not changed.

## Later historical qualification archives

At source `11022428`, the archive checker verified the catalog, original
manifest hashes and all seven member hashes in each of the newly tracked v3
and v4 qualification archives. Each archive contains eight regular files.
A separate in-memory scan sent each decompressed member to Gitleaks 8.30.1
with default rules. All 14 row files returned exit 0 with no findings. Each
manifest returned exit 1 with one `generic-api-key` finding; in both cases the
exact flagged 64-character value matches the SHA-256 of that archive's
`protected-tokens.jsonl`. The member hashes were computed independently. Both
archive hashes were unchanged before and after this inspection. The unredacted
finding values were compared only in memory and were not recorded.

The manifests declare no personal messages, but this scan and declaration do
not establish independent authorship, complete licensing, absence of all
private data or publication readiness. No archive member was written to disk.
The nonzero manifest scans remain nonzero; these checks do not change the
previous history scan or demonstrate hosted CI.

## Delta through the local scientific verification

At `3208a70f`, the local comparison against `origin/main` found 2,765 unique
unpublished blobs. Of these, 74 exceeded 10,000,000 bytes, 56 exceeded 50 MiB,
and none exceeded 100 MiB. The largest was 94,497,017 bytes. The range
whitespace check passed. The F-Droid policy verified all 33 inventory entries,
and its 14 targeted tests passed.

Gitleaks scanned `479dd429..3208a70f` with a 10 MB target limit and archive
traversal disabled. It exited 1 with six generic API-key findings in the
control registry. Each value matched the SHA-256 computed directly from the
same committed v2 protected-token file at the finding's commit. Reports were
removed after comparison. Earlier history and out-of-scope files retain their
previous verification limits.

For the v3 and v4 archives, all six source-shard hashes and both manifests'
license lists and article-selection parameters matched their historical source
locks. A [source notice](../../tools/typing_experiments/historical-qualification-v3-v4/NOTICE.md)
now accompanies the archives. The source labels and generator inspection show
why those matching shard hashes alone cannot identify the articles behind
individual spelling and punctuation rows. Article attribution and review of
the broader unpublished history remain open before public distribution.

## Attribution and registry delta through 3001b212

Gitleaks scanned `3208a70f..3001b212` with default rules, redacted output,
a 10 MB target limit and archive traversal disabled. The scanner exited 0
with zero reported findings. This incremental scan covers the additions after
the preceding range, including the article attribution files and new
article exclusion entries, within the scanner's limits. The report was
removed. Earlier scan results and the remaining publication review still apply.

## Current history and recovered v6 inputs

At `d22466f1`, the live `origin/main` ref was still `2c1ff975`, matching
the local tracking ref. The 659 unpublished commits contained 2,872 unique
reachable blobs. The largest was 94,497,017 bytes. Of these, 77 exceeded
10,000,000 bytes, 56 exceeded 50 MiB, and none exceeded 100 MiB.
`git diff --check origin/main..HEAD` passed.

Gitleaks 8.30.1 with default rules, a 10 MB target limit, no archive traversal
and redacted reports exited 1 for the full range. It reported 23,466
`generic-api-key` findings across 50 paths. The incremental range
`3001b212..d22466f1` contained 51 blobs and none exceeded the size limit.
Its scan exited 1 with 1,660 occurrences, all present in the full result by
exact commit, path, line, column and rule. The reported locations all
intersect the verified `sentenceKey` fields of the v6 calibration source
index. The earlier findings retain their individual review status.

The 77 large JSON blobs above the history scanner's limit were read in full
using an independent streaming marker check. They comprised 67 lexical and
10 control ledger versions, 4,723,459,392 bytes. The marker set covered PEM
private-key headers, the local home path, email-address shapes and GitHub,
AWS and Slack token shapes. No blob matched those markers. This separate
screen is limited to the stated patterns.

Two compressed files were added in the incremental range. Their decoded
SHA-256 values matched the original calibration manifest and the retained
rival map, respectively. Gitleaks stdin scans of the 3,266,373-byte TSV and
of its decoded prefix and typed columns both exited 0 with zero findings.
The decoded rival map scan exited 1 with 4,967 locations. All intersect
registry hash fields: 2,481 `sentenceKey`, 2,466 `targetKey` and 20
`contextHash`. Both archive hashes remained identical before and after.
Decoded corpus rows were handled in memory. The earlier history limits,
personal-data review and distribution rights remain open.

## Delta through the Android full-report gate

The 18 commits in `d22466f1..40e45595` added 85 unique reachable blobs.
The largest was 371,928 bytes, below the 10 MB Gitleaks target limit.
`git diff --check` passed. A separate byte scan of all 85 blobs found no
NUL bytes and no matches for the local home path, private-key headers, or
the tested GitHub, AWS and Slack token patterns.

Gitleaks 8.30.1 with default rules and redacted output exited 1 with 1,627
`generic-api-key` locations. Checking the exact Git blob for each finding's
commit at the reported lines and columns mapped 1,626 locations to the historical v6
holdout source index's `sentenceKey` fields and one to the
`pymorphy3/tokenizers.py` hash in the natural-context recovery receipt.
The holdout index passed its article, context and family coverage test
against the existing registry. The package file independently matched
the receipt using the pinned Pymorphy environment.

These results cover the incremental commits and the stated checks.
Earlier history findings and limits, source distribution rights and
publication approval remain open. The redacted report and the temporary
verification environment were removed.

## Delta through the API 26 supplementary routes

The ten commits in `40e45595..90cd5fad` made 43 unique blobs reachable.
Gitleaks 8.30.1 scanned the Git patches with the default rules, redaction
and a 10 MB target limit. It exited 0 with no findings. A separate byte
scan of all 41 smaller blobs found no NUL bytes, local home path, private
key headers, or matches for the tested GitHub, AWS and Slack token
patterns. The largest of those blobs was 112,187 bytes. The range passed
`git diff --check`.

The two oversized blobs are successive versions of `holdout-ledger.json`.
A byte comparison against each parent verified that both changes preserve
the entire previous ledger and insert two entries inside the entries array.
The first pair binds 25 family and 576 context keys. The second pair binds
38 family and 420 context keys. An unmasked Gitleaks stdin scan of the
four entries exited 0 with no findings. Both registration checks ran in a
fresh offline environment with the hash-pinned morphology requirements.
They regenerated the original authored corpora and reproduced all four
entries. The older ledger bytes retain the scope and limitations of the
earlier audit. Historical findings and distribution rights remain open.

## Delta through the API 37 QA editor change

The eight commits in `90cd5fad..905d1a23` made 27 unique blobs reachable.
Every blob was below the 10 MB target limit. The largest was the
420,540-byte holdout article map. `git diff --check` passed. A separate
byte scan of all blobs found zero matches for NUL bytes, the local home
path, private-key headers and the tested GitHub, AWS and Slack token
patterns.

Gitleaks 8.30.1, with default rules and redaction, exited 1 with two
`generic-api-key` locations. Checking the exact Git blobs resolved both
locations to the `pymorphy3/tokenizers.py` SHA-256 field in the recovered
grammar-focused and noun-case-v3 manifests. The hash of that file from
an offline, hash-pinned install of Pymorphy 2.0.6 matched both locations.
The recovered manifests and article map also passed their provenance
checks. Earlier history findings, article-specific attribution and
distribution rights remain open.

## Delta through Joint and Rare Ranking recovery

The 15 commits in `905d1a23..3831990e` made 59 unique blobs reachable.
The largest was 118,514 bytes. The range passed `git diff --check`. A
byte scan of all 59 blobs found no NUL bytes, local home path, private
key headers, or matches for the tested GitHub, AWS and Slack token patterns.

Gitleaks 8.30.1 ran with default rules, redaction and a 10 MB target limit.
It exited 1 with one `generic-api-key` location in the Joint and Rare Ranking
recovery receipt. The source line in the reported Git blob binds the SHA-256
of the Reliable Side v5 article exclusion index. The retained index matched
the digest and contained 16,152 unique keys. The temporary scan report was
removed. Earlier history findings and distribution rights remain open.

## Delta through Reliable Side v5 and the night-learning runs

The five commits in `78bfd3bd..6c7967ad` made 19 unique blobs reachable.
The largest was 120,613 bytes. The range passed `git diff --check`.
A byte scan of all 19 blobs found no NUL bytes, local home path, private
key headers, or matches for the tested GitHub, AWS and Slack token patterns.

Gitleaks 8.30.1 ran with default rules, redaction and a 10 MB target limit.
It exited 1 with one `generic-api-key` location. The reported Git line
contains the SHA-256 of the sentence-corpus-v6 article exclusion index.
The retained index matched the digest and contained 17,886 unique keys.
The temporary scan report was removed. Earlier history findings and
distribution rights remain open.

## Delta through the supervised v2 and clean-v6 report recovery

The six commits in `c95862c7..15d3c788` made 21 unique blobs reachable.
The largest was 122,359 bytes. `git diff --check` passed. A byte scan of
all blobs found zero NUL bytes, local home paths, private-key headers,
or matches for the tested GitHub, AWS and Slack token patterns.

Gitleaks 8.30.1 with default rules, redaction and a 10 MB target limit
exited 1 with one `generic-api-key` location. It matched the SHA-256
of the sentence-pairs v2-v6 article index. The retained index matched
that digest and contained 19,954 unique keys. The temporary report was
removed. Earlier history findings and distribution rights remain open.

## Delta through the original Word Context and Context Feature manifests

The eight commits in `15d3c788..a0c2a067` made 34 unique blobs reachable.
The largest was 123,541 bytes. `git diff --check` passed. The byte scan
found no NUL bytes, private-key headers or matches for the tested GitHub,
AWS and Slack token patterns. Its single home-path match was the literal
placeholder in the first section of this receipt.

Gitleaks 8.30.1 with default rules, redaction and a 10 MB target limit
exited 0 with zero findings. The temporary redacted report was removed.
This result covers the eight-commit delta. Earlier history and distribution
rights remain open.

## Hosted CI dependencies on two retained v6 text files

A local sparse checkout at `2aa1c510` excluded the compressed v6 calibration
TSV and the logged calibration observation. It retained the rival-association
archive. Both excluded files are absent from the local `origin/main` tree.
Their first unpublished commits are `f2a730e3` and `acf029fa`, respectively.
A sparse checkout leaves their Git objects reachable from the original
history.

| Check | Result with both text files absent |
| --- | --- |
| Q6 recovery module | Exit 1, four missing-file errors among 48 tests |
| F-Droid data policy | Exit 1, stale inventory entry |
| Packaged numeric-asset notice | Exit 1, inventory validation failed |
| Hosted Python module inventory | Exit 0 |

Three recovery tests depend on the calibration TSV through its byte digest,
source-index validation or attribution receipt. A fourth reads the original
logged observation. The F-Droid inventory explicitly binds the TSV and the
numeric-asset notice gate reuses that exact inventory. The rival-association
archive contains 2,492 records with identities, partitions, source offsets and
variant labels. Its schema contains no excerpt or word fields.

On the intact checkout through `0fc01ca0`, the 49-test recovery module, the
35-entry F-Droid policy, the numeric-asset notice and the Python module inventory
all passed. The temporary checkout was removed. This was a local negative
probe for the affected hosted routes. It identifies which checks a publication
candidate without either original text file must address before a hosted run.

### Isolated v6 archive checks

The first profile split at `52a23ffb` moved the four direct archive checks.
An exhaustive run without the two text files then found a fifth check in the
context-anchor module. It reported one missing-file error among 1,079 tests
in 210 modules. Source inspection identified three scientific modules that
used the same logged observation. The follow-up at `98c10c78` moved those
three modules and the fifth check into `historical-artifacts`, retaining the
assertions. The hosted profiles still check the frozen attribution metadata
and verify the remaining input files. The local profile passed 21 tests in
four modules with both originals and pinned PyArrow.

At `98c10c78`, a separate Python 3.12.14 checkout omitted the same two
files. The scientific workflow commands installed their pinned dependencies,
ran the morphology and authored registries, and verified and restored the
other original fixtures. The scientific runner passed 107 tests and skipped
one in 27 modules, with zero errors, failures or timeouts. Its receipt SHA-256
is `45e8cc2df40329357722c9b9ac65a34be2503d9f4d222595da8d8a7e5a6ede51`.

A temporary copy of the F-Droid inventory with just the absent calibration
TSV entry removed verified all 34 remaining entries and passed the
numeric-asset notice gate. The original policy continued to refuse an
absent inventoried file. The policy probe did not change the repository
inventory or transfer Git objects.

A second Python 3.12.14 checkout of `98c10c78` initialized the pinned
llama.cpp submodule and omitted both text files. The full stdlib runner
passed all 1,078 tests in 210 modules, with zero errors, failures, skips
or timeouts. Its receipt SHA-256 is
`bc35710e565fb41da129d445c1d58e40aa1de3cf0b5608c5d9a5f8e1f9ac338a`.
The temporary checkouts and the scientific environment were removed.
Both local profile runs covered test execution with the files absent from
the working tree. External hosted execution, Git object reachability in a
publication candidate and distribution rights remain open.

### Local candidate bundle and clean import

Published `main` still pointed at `2c1ff9751e74` when queried. A
temporary index constructed candidate `4458c29144c1` with that commit as
its sole parent. Its source tree starts from `6c181a0b`, removes the
calibration TSV and logged observation, and removes the corresponding
TSV entry from the F-Droid policy. The source-to-candidate diff lists
exactly those three paths.

Git object enumeration covered all 10,506 objects reachable from the
candidate, including 1,549 objects beyond its parent. The two excluded
historical blob IDs were absent. A new receiver without Git alternates
fetched only the published base, then verified and imported a
97,050,342-byte incremental bundle. Neither excluded blob was readable
before or after import. The bundle SHA-256 was
`1419e08886abf000889181ad7d41ddb34fd7f3a8a9ad5284e8131f35768bc82a`.

The imported tree passed Python inventory, F-Droid data policy,
numeric-asset notice, packaged provenance and local documentation checks.
It also passed 46 v6 metadata tests and three public-anchor tests with
the pinned submodule checked out. Bundle and checkouts were removed.
The candidate remains available under the local Git ref
`refs/rune-review/ci-candidate`. The check covers the two named payloads
and the affected routes. Broader source rights and hosted execution
remain open.

Gitleaks 8.30.1 scanned the candidate's one-commit range with the default
rules, 100 percent redaction, a 10 MB target limit and archive traversal
disabled. It exited 1 with 25,076 `generic-api-key` findings. Of those,
25,002 overlapped a 64-character value in one of four registry fields:
13,162 `sentenceKey`, 6,570 `targetKey`, 3,256 `articleKey` and 2,014
`surfaceKey`. This is a structural classification. The other 74 findings
across 48 paths still need review in this exact candidate. The candidate
delta has 1,361 unique blobs, including two over 10 MB and five archive
paths. The redacted report was removed.

### Candidate finding provenance and excluded scanner inputs

A second full scan of `4458c291` reproduced the 25,076 findings and the
25,002 overlaps with named registry fields. All 74 other locations were
classified from the exact candidate source:

| Locations | Evidence |
| ---: | --- |
| 44 | Reported hexadecimal values matched SHA-256 of tracked candidate blobs. |
| 18 | The tokenizer digest matched the member of the hash-pinned Pymorphy 3 2.0.6 wheel. |
| 3 | Digests matched the retained article-exclusion indexes for Reliable Side v5, Sentence Corpus v6 and the Sentence Pairs v2 v6 parent. |
| 2 | The A4 frequency-source checker recomputed both digests from the registered lexical and control article-key lists. |
| 2 | Both Neighbor history checks recomputed the original family-key digests for 7,903 and 2,503 keys. |
| 1 | The exact reported value resolved to a tracked navigation receipt slug. |
| 4 | Original `shasum -a 256` tool outputs on October 28 and 29 pair the exact values with two APKs and two Android test logs. The original artifact bytes were unavailable for rehashing in this pass. |

The two oversized blobs match the canonical checkout. The lexical and
control registries passed their schema and integrity validators with 229
and 91 entries. Gitleaks found zero matches in 23 and eight four-MiB
blocks respectively, with 4,096-byte overlap and complete quoted
64-character hex values masked. The scan covers the unmasked bytes.
Registry coverage remains incomplete.

All five new archive blobs were checked in memory. Both Tatoeba CC0
archives matched their locks and had zero scanner findings after
decompression. The v3/v4 manifest and payload hashes verified, and each
manifest's one finding matched the enclosed protected-token payload.
The v6 rival archive verified against the registered target associations.
Its decoded scanner run found 4,967 generic findings, and the field
classification repeat found 4,968. All reported locations in the repeat
overlapped checked sentence, target or context digests.

The candidate Git scan still exits 1. Classification of the 25,002
registry-field locations in that scan is structural, and the separate
large-file pass masked quoted digest values. These checks address value
provenance and scanner coverage. Distribution rights and hosted
execution remain open. The temporary scanner reports and wheel downloads
were removed.

### Historical v3/v4 archives in the CI candidate

Candidate `4458c291` still contains both historical archives. Their catalog,
archives and attribution maps matched the local verified bytes. The keys in
the twelve language/component maps matched the original archived row IDs
exactly. Every one of the 22,800 spelling and punctuation rows has at least
one source candidate. Of those, 99 have multiple candidate articles.
Across both versions, the maps reference 5,948 English, 5,744 Spanish and
5,118 Russian article IDs. The authored protected-token component is outside
these counts.

The current-public-page check requested MediaWiki page metadata and selected
notice templates by article ID. The service returned HTTP 429 after retries
and no language completed. This attempt produced no verified article-level
availability or notice totals. Discussion pages and historical article
revisions also remain open. Article matching and title/URL coverage are
separate from the article-specific attribution and licensing review.
[MediaWiki page and template queries](https://www.mediawiki.org/wiki/API:Templates)
[Wikimedia licensing terms](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)

An isolated checkout of the candidate omitted both archives. All three
workflow commands for the early unknown surfaces, historical qualification
controls and historical spelling articles exited 1 on missing inputs.
Six Python modules also failed when the original archives were absent:

- `test_import_early_ru_history`
- `test_import_control_components`
- `test_check_historical_qualification_archives`
- `test_register_early_unknown_control_surfaces`
- `test_register_historical_qualification_controls`
- `test_public_corpus_preparation_v1`

With the verified archives present, the three registry checks exited zero
and audited 654 surfaces, 12 control entries and six lexical entries with
15,652 article keys. The temporary checkout and the empty API output
directory were removed. The candidate still needs a supported fixture route
for these checks if distribution excludes the archive bytes.

### Byte-exact fixture reconstruction from the pinned source shards

The source commits of the v3/v4 tar members are outside the published
base's ancestry. Both historical manifests also bind training data, with
different train, validation and manifest digests in the two versions.

The fixture reconstruction used the hash-verified historical generators,
source locks, vocabulary files, and archived selection fingerprints.
Article-ID maps narrowed each scan to the source candidates for the
already selected rows. Across the six pinned Parquet shards, every
expected spelling and punctuation item was recovered from upstream text.
The original frozen emitters then reproduced all twelve language rows
files byte for byte. The authored protected-token generators reproduced
both 1,800-row protected components independently.

The two original manifests, the reconstructed components, and fixed
sorted tar metadata reproduced both compressed archive SHA-256 values in
the catalog. This was recovery of the original fixture from frozen
selections. End-to-end reselection using the original training inputs
was outside this run. It made zero model calls. All ten archive validation
tests passed, including the new exact protected-component check.

The temporary downloads and redundant reconstructed payloads were removed
after verification. A hosted fixture route still needs checked
selection-only metadata and a CI step that reconstructs the archives
before the dependent tests. Article-specific publication rights remain
open.

### Fixture replay wired into the hosted workflow

The stdlib matrix and unit-test jobs now run the pinned public-source
reconstruction before their archive-dependent checks. The checked-in
index contains the original manifests, source-map digests and selection
fingerprints. The replay verifies each public shard before and after
reading, checks every emitted payload, and installs only the original
catalog-bound archives. Present archives pass the same byte checks.
The workflow does not upload these regenerated fixtures.

A disposable checkout initially omitted both v3/v4 archives and both
unresolved v6 text files. The permanent command fetched six pinned
shards and rebuilt both archives byte for byte. In that checkout all
three dependent registry commands, 64 tests in the six affected
modules, the 34-entry candidate F-Droid inventory and the numeric
asset notice check passed. The two v6 text files stayed absent. On the
intact checkout, the updated archive test module passed all 11 tests,
including the replay-index bindings. Both workflow shell blocks parse.
Temporary source, downloads and outputs were removed. These were local
checks. Hosted job execution and distribution rights are still open.

Candidate `0ecfca8c951d2`, based on `e6a3b0a1`, includes the fixture
replay route. A fresh bundle import verified all four excluded blob IDs
were unavailable in the receiver: the two v6 texts and both v3/v4
archives. The sole parent is still the live published base
`2c1ff9751e74`. The candidate policy keeps both v3/v4 inventory entries
for the exact files generated before validation. The bundle was
95,450,446 bytes, with SHA-256
`96ceb597a5989cc52e65b6fba7bb555fd5b02edc3614a2cd3efb6da8125dc7fc`.
The local candidate ref was updated after verification, then the
bundle and both temporary repositories were removed.

The Gitleaks scan of the fixture-route commit exited 1 with two generic
findings in the new replay index. Both matched SHA-256 of the original
protected-token files, one per archive. No raw finding value was retained.

### Local candidate with the recovered v6 exclusions

Local ref `refs/rune-review/ci-candidate-v6` points to `2c8a2af925ba`.
Its sole parent is `2c1ff9751e74`, independently confirmed as the live
published main-branch tip. The 15 changed paths since `0ecfca8c951d`
are documentation and typing-experiment files. The Android application,
native runtime and workflow trees match the earlier candidate.

A fresh bundle import and Git connectivity check passed. All four
excluded blob IDs were unavailable before and after import. The bundle
contained 96,498,639 bytes and had SHA-256
`4364926bdfa8b79579d4085d96fa60ad4ee21bdf48eb1d7e3b2ee1028ef50d37`.
The temporary Git repositories and bundle were removed.

Gitleaks scanned the 15-path delta with 100 percent redaction and the
10 MB limit. It exited 1 with one generic finding in the Rare Ranking
receipt. A separate installation from the hash-locked Pymorphy 2.0.6
wheel reproduced the digest of `pymorphy3/tokenizers.py` at that
location. The temporary wheel environment and scanner reports were
removed. This scan covers the delta subject to the scanner limit.
Hosted validation and source distribution rights remain open.

## Review delta through the v6 revision-content pilot

The range `a0c2a067..a858fb5f` contains 45 commits, 41 changed paths and
135 newly reachable blobs. `git diff --check` passed. A separate byte scan
over all 135 blobs found no NUL bytes, local home paths, private-key headers,
or matches for the tested GitHub, AWS and Slack token patterns.

Gitleaks 8.30.1 with 100% redaction, a 10 MB target limit and no archive
traversal reported three generic findings. The exact values were SHA-256
digests. One independently matched `pymorphy3/tokenizers.py` installed from
the pinned wheel. Two matched the `protected-tokens.jsonl` members read from
the original v3/v4 archives.

Two ledger blobs, 94,698,968 and 94,938,354 bytes, exceeded the scanner
limit. Comparing each with its predecessor found six and four new entries,
with no change to any prior entry. Separate Gitleaks stdin scans of those
new entries exited zero with zero findings. The redacted reports and wheel
environment were removed. Earlier scans' limits and the source distribution
review remain open.

### Current local CI candidate through the revision pilot

Local ref `refs/rune-review/ci-candidate-v6` was advanced to `4cb8066907b8`
after validation. It represents source `a858fb5fe62c` and has the live
published `2c1ff9751e74` as its sole parent. The sole source-tree differences
are the four consistently withheld files and the corresponding calibration
TSV policy entry. The candidate differs from `2c8a2af925ba` at 16 paths.

A repository without alternates fetched the published parent and imported the
candidate bundle. Git connectivity passed. The four withheld blobs were absent
before import, afterward, and after fetching the historical controller revision
that the new CI step requires. The role replay reproduced 9,094 groups and their
original SHA-256 in that imported tree. The Python inventory, four focused role
tests, numeric asset notice, and packaged provenance checks passed. The notice
and provenance checks used two local v3/v4 fixture files checked against the
candidate's explicit size and SHA-256 policy, plus the pinned source submodule.
The fixture files introduced no corresponding Git objects.

The bundle was 96,530,020 bytes, with SHA-256
`5bdbde2528135b3404f407abd5e02864345a471aa941495498fc7a6616ab507c`.
The file scan of the 16 changed candidate paths reported a generic finding on
the unchanged U18 review row. Its complete line matched the prior candidate
byte for byte. The bundle, receiver and temporary verifier outputs were removed.
Hosted execution and distribution review remain open.

### Delta through the revision witness verifier

The six commits in `a858fb5f..426efd4c` made 18 unique blobs reachable.
The largest was 133,514 bytes. `git diff --check` passed, and Gitleaks
8.30.1 with full redaction and a 10 MB target limit exited zero with
zero findings. This covers the first two shard witness maps, the recovery
command and the offline verifier. The temporary scanner report was removed.
The local CI candidate remains at its separately verified snapshot.

### Local CI candidate with the English pronoun boundary fix

Local ref `refs/rune-review/ci-candidate-v6` now points to
`94819126a417435afec503acc8d49e873f401972`. Its sole parent is the
published main tip `2c1ff9751e74`. The candidate applies the controller
and regression-test files from `36989ab5` to `4cb80669`.
A redacted Gitleaks scan of these two source files found zero findings.

An isolated repository fetched the published parent, imported the
candidate bundle and passed Git connectivity. The four previously
withheld paths and their Git objects were absent after import and
after fetching the historical controller revision used by CI. The bundle
was 96,523,858 bytes, SHA-256
`bf5c9838abd56b1b7df586936af3ccd56ab100d703bab178728d01f882d0f83d`.

The Python inventory check and all 1,415 app and 19 runtime JVM tests
passed with zero failures or skips. The local CI replay matched both
frozen projections (2,160 and 12,000 rows) with zero tolerated score
differences. The exact unsigned APK passed the [local release checks
and F-Droid scanner](2026-10-29-q1-fdroid-binary-scan.md#release-scan-after-the-english-pronoun-boundary-fix).
The bundle and verification checkout were removed. The latest hosted
run for published main still shows failures in the Android boundary jobs
and frozen replay. This candidate has local evidence.
[Hosted run for published main](https://github.com/Mesteriis/rune.keyboard/actions/runs/40680972358)

### 2026-11-24 candidate with current Android review fixes

Local ref `refs/rune-review/ci-candidate-v6` advanced from `94819126` to
`123d0a5246b4e173a787102ede60b24c8cdc786d`. The sole parent remains
the verified GitHub main tip `2c1ff9751e74`. The four changed files
bring in the A1 instrumented apostrophe case and required runner entry,
and the U6 settings focus fix and instrumented assertion. The app,
native runtime and workflow trees match the review checkout at
`d53ce8bf`. The previous candidate's publication exclusions are unchanged.

A fresh repository with no object alternates fetched the published
parent, imported the bundle, fetched the workflow's historical controller
revision and passed Git connectivity. All four excluded blob IDs were
absent before import, after import and after the historical fetch. The
bundle was 96,526,648 bytes, SHA-256
`82df3df2575152db55dcc53bc1d2bd67cb3e920ebde2b3b78da75e1637f546b2`.
The full patch passed `git diff --check`. A fully redacted Gitleaks
scan of the four exact new blobs found zero findings.

The Python inventory and 38 focused runner tests passed from the
imported checkout (27 Android boundary runner, six shell, five replay).
The offline Gradle resolver verified five pinned JARs. The same replay
command used by CI independently ran both profiles twice, matching
14,160 frozen rows with zero differing rows and zero tolerated score
differences.

| Rows | Baseline and candidate projection SHA-256 |
| --- | --- |
| 2,160 | `e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea` |
| 12,000 | `b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512` |

The temporary repositories, bundle, scan inputs and build outputs were
removed. The latest GitHub run on the published parent still records
the earlier `PINNED_KOTLIN_CACHE` failure and both Android boundary
failures. The new candidate is local. [Fresh JVM and targeted Android tests](2026-10-28-q7-ci-baseline.md#2026-11-24-jvm-and-android-checks-on-candidate-123d0a52) and the [unsigned release package checks](2026-10-29-q1-fdroid-binary-scan.md#release-scan-of-the-refreshed-hosted-ci-candidate) passed on this revision. Full Android boundary runs on this revision, hosted execution and release acceptance remain open.
[GitHub Actions run 40680972358](https://github.com/Mesteriis/rune.keyboard/actions/runs/40680972358)

### Candidate with A2 retention and editor-settling fixes

Local ref `refs/rune-review/ci-candidate-v6` advanced to
`75d06f6f3de543baea505a33e79614ea5867a1c5`. Its published parent remains
`2c1ff9751e74`. Nine source and test files carry A2's source-only request
replay, the bounded-window retention fix and the non-normal editor UI
test fix. The production and instrumented code matches those files in
`c8dca88d`.

The 96,528,507-byte bundle has SHA-256
`d5a87aa298721a0fbb49a46978ec362376fc6781db5c79675e8656c8fae61de0`.
An isolated repository with no alternates fetched the published parent,
imported the bundle and fetched the separate historical controller
revision. Git connectivity passed and all four excluded blobs stayed
absent. Redacted Gitleaks found zero findings in the nine changed files.

Forty focused Python tests passed in the imported repository. The CI
replay toolchain resolved five pinned JARs, and both frozen profiles
matched all 14,160 rows with zero tolerated differences. The A2 request
checker ran without model artifacts and matched all 1,877 calibration
and 2,004 holdout requests. The bundle and temporary repositories were
removed. Hosted execution and the full Android matrix remain open.

### Candidate with expanded-suggestion accessibility and the U14 CI gate

Local ref `refs/rune-review/ci-candidate-v6` advanced to
`687361c8ac48eee16217c23b7510c18129817f6f` on the unchanged published parent
`2c1ff9751e74`. Nine production, instrumentation and CI paths match
`ffb1304e`. An initial full-file scan of the wider docs and code scope found
one generic-key signature on a byte-identical U18 line present in both
predecessors. This refresh carries the nine code and test paths. Their
redacted Gitleaks scan found zero findings.

The temporary bundle was 96,534,818 bytes with SHA-256
`ca959a681a75a2f86d014952f7637702c35d381e50f2920bd63f67a48edd1a74`.
A fresh repository fetched the published parent and separately fetched the
historical controller revision. Connectivity checks passed after bundle
import, with no alternates and all four excluded blobs absent. The import
passed 54 Android CI runner tests and five replay-helper tests, resolved five
pinned replay JARs, and matched all 14,160 frozen rows. Temporary repositories
and the bundle were removed. Hosted execution remains open.
