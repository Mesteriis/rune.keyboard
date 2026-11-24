# Public-history large-blob preflight

At `a2c7ecb5`, the live `origin/main` ref matched its local tracking ref; the
local branch had 542 unpublished commits. `git diff --check origin/main...HEAD`
passed. No push or hosted workflow was performed.

A read-only `git rev-list --objects origin/main..HEAD` walk and `git cat-file`
size inspection found 2,477 unique reachable blob objects. Seventy exceeded the
10,000,000-byte threshold, all versions of the lexical or control ledgers;
55 exceeded 50 MiB, and none exceeded 100 MiB. The largest was a historical
lexical ledger blob of 94,497,017 bytes. These are object counts, not counts of
unique logical files or evidence that a remote will accept a push. The result
also does not validate repository size, hosting quota or every historical path.

The prior history Gitleaks run used a 10 MB target limit and did not scan these
large blobs. A separate streaming screen read all 70 complete blobs (4,468,547,443
bytes total), without retaining their contents or matched values, for four
specific markers: private-key PEM headers, the local user-home path, the Fold
serial and email-address-shaped strings. None of those markers appeared. This is
not a general secret scanner, personal-data review or licensing audit and does
not cover compressed archive contents. It does not make the existing unpublished
history safe to publish.

The current net diff contains 28 JSONL/TSV/CSV files; each had a nearby NOTICE
or LICENSE under a bounded parent-directory search. Presence of a notice does
not establish rights in its actual contents or in earlier commits. The previous
history secret-scan classification and unresolved corpus provenance continue to
apply. Publication and hosted CI remain pending full content/rights review and
the appropriate authorization.

## Repeat after v6 source-anchor recovery

At `7676bc24`, Gitleaks 8.30.1 scanned `origin/main..HEAD` using its default
rules and a 10 MB target limit, without archive traversal. It exited 1 with
21,790 generic API-key findings across 45 paths. This is not a clean scan and
the full set is not classified. The report was stored only in a private
temporary directory and removed after aggregate inspection.

A separately repeated scan of the three source-anchor commits found 19,702
findings whose locations map to named registry hash fields in the retained
JSONL: 3,256 `articleKey`, 3,302 `sentenceKey` in the anchor file, 6,574
`sentenceKey` and 6,570 `targetKey` in the target mapping. These field names
and source derivation explain those specific generic-rule matches; they do not
classify the remaining full-history findings, establish absence of secrets or
cover large blobs and archives. The respective reports were also removed.
No publication or hosted CI run was performed.

## Earlier-history range recheck

A separate scan of `origin/main..03e26fd4` with the same tool and limits
returned exit 1 with 2,088 generic API-key findings across 42 paths. Of these,
2,014 occur in the two earlier source-bound historical text projection files;
all 2,088 finding commits are ancestors of `03ad7b82`. The earlier
[preflight at `03ad7b82`](2026-11-09-q7-current-python-inventory.md#public-history-preflight)
recorded a detailed classification of 2,089 findings in its range, including
2,014 `surfaceKey` findings and 74 hexadecimal findings. The present check
compares commit ancestry and aggregate counts, not individual fingerprints;
it does not prove the two sets of 74 are identical. The remaining findings and
all material outside the scanner's limits still require appropriate review.
The temporary reports were removed.

## Exact-location reconciliation of current findings

At source `a294a522`, Gitleaks 8.30.1 was rerun over
`origin/main..HEAD` with its default rules, a 10 MB target limit, no archive
traversal and redacted reports. Its actual exit was 1: 21,790 findings from
`generic-api-key` across 45 paths. A second scan of
`origin/main..03ad7b82` exited 1 with 2,088 occurrences. A multiset comparison
using commit, path, line, column and rule matched all 2,088 old occurrences to
current findings. This corrects the earlier aggregate-only comparison, but it
cannot prove that the removed report from the earlier 2,089-finding run
contained the same individual findings.

The 19,702 remaining current occurrences were checked against the exact
committed source lines and finding columns. All intersect the following
64-character hexadecimal JSON fields: 3,256 `articleKey`, 3,302 `sentenceKey`
in anchors, 6,574 `sentenceKey` and 6,570 `targetKey` in target matches.
There were no unmatched locations in these three paths. These are retained
registry identity fields, not a general exemption for hexadecimal strings.
At the same source, all 12 retained v6 article, context and target receipt tests
passed. These checks establish source-location classification and artifact
bindings, not a clean secret scan, recovery of corpus rows or authorization to
publish. The other 2,088 occurrences still require exact reconciliation with
the earlier detailed classification, whose raw report was not retained. Large
blobs, archives, personal text, rights and complete publication review remain
outside this result. Both redacted reports and scan logs were removed.

## Newer unpublished commits

Gitleaks 8.30.1 scanned `a294a522..663047d3` with default rules, a 10 MB
target limit, archive traversal disabled and report redaction. It exited 1,
with ten `generic-api-key` occurrences across four paths. Each finding's exact
committed line and reported column range overlaps a 64-character hexadecimal
JSON value. Seven values equal SHA-256 digests independently computed over the
corresponding tracked file at the finding's own commit. The remaining three
are named as digests in their source: two A4 exclusion-manifest keys and the
Pymorphy tokenizer entry in the scientific receipt. Those three were not
independently recomputed in this repeat; their field names alone are not proof
that they are harmless. The redacted report and temporary scan log were removed.

This incremental result does not supersede the earlier 21,790-finding scan,
resolve its exact reconciliation gap or cover files above the limit, archives,
personal text, licensing, untracked data or commits after the upper bound. The
scan is not a clean security or publication approval, and no push was made.

### Follow-up on the three remaining values

The current source-bound `import_a4_frequency_source.py --check` completed with
exit 0, validating the frozen manifest and independently recomputing both
92,622-key registry digests from their retained ledger entries. This verifies
the two A4 values as hashes of those registered keys; it does not re-read the
original source shard or establish independent qualification.

For the tokenizer value, a new temporary Python 3.12.14 environment installed
`tools/morphology/requirements.lock` offline with `uv pip --require-hashes`.
The installed `pymorphy3/tokenizers.py` SHA-256 matched the one corresponding
receipt value. The install and comparison exited 0; the environment and install
log were removed. These checks resolve the three named occurrences as matching
their respective data or locked dependency bytes, without changing the scanner's
exit code or the earlier and out-of-scope limitations.

## Repeated older-range source-location review

Gitleaks 8.30.1 repeated `origin/main..03ad7b82` with the same default rules,
10 MB limit, no archive traversal and redacted output. It exited 1 with 2,088
`generic-api-key` occurrences. Against the exact committed source lines and
reported column ranges, 2,014 overlap `surfaceKey` hexadecimal fields in the
two historical source projections. Fifty further values match SHA-256 digests
computed directly from their corresponding tracked files at the finding's own
commit, including two values embedded on a minified JSON line. Fourteen match
`pymorphy3/tokenizers.py` in a fresh offline Python 3.12.14 environment installed
from the locked requirements using `uv pip --require-hashes`.

Ten occurrences remain outside those three checks: nine hexadecimal values and
one non-hexadecimal match. The earlier detailed receipt describes their types,
but its raw report was not retained, so this repeat does not equate individual
findings with that earlier classification or treat the remaining ten as safe.
Matching a digest or a source-identity field does not establish that the data
it describes is suitable for publication. The temporary redacted report, logs
and environment were removed. All previously stated scan limits and publication
boundaries continue to apply.

### Follow-up on the ten remaining older findings

The older range was scanned again with the same Gitleaks version and options;
its exit remained 1. Five of the ten outstanding occurrences were checked more
deeply. Three receipt values matched SHA-256 computed from their corresponding
tracked source or key file in the finding's commit: the neighbor-prefix
tokenizer, English EWT family-key helper and retrieval source-key file. The
other two are `KEYS_SHA` constants in the neighbor-family importers. Their
values at the finding commits match the current constants, and both current
`--check` commands exited 0 after recomputing the retained family-key lists
(2,503 and 7,903 keys respectively).

One non-hexadecimal finding's reported range overlaps U18 navigation-receipt
identifiers in the plan. The remaining four hexadecimal occurrences are labelled
as API 26 and API 37 raw-log SHA-256 values in two acceptance documents. The
specified ignored log directories were absent when checked, so their bytes were
not independently rehashed in this follow-up. The prior receipt describes them
as log digests, but this repeat does not prove their original contents. The
redacted report and temporary log were removed. The prior 2,014 `surfaceKey`
classification and limitations of scanner coverage, source rights, private data
and publication remain unchanged.
