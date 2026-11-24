# Q6 base collector registry gates

The direct v6 spelling holdout and original joint-correction preparers now use
the same permanent-registry gate as v7–v12 and the joint follow-up. Default
execution refuses incomplete coverage before reading requested source inputs
or importing the optional Parquet runtime. Before output, all selected rows
must pass the shared new-family gate and ledger snapshots must remain unchanged.

Historical collection requires `--historical-reproduction`. Both manifests and
CLI summaries identify disclosed, non-independent regression scope; manifests
bind the guard sources and declare `newUnseenHoldout=False`. The original exact
v6 and joint sources were already retained in the frozen archive; both digests
are rechecked. No original source receipt is rewritten. Joint output creation
now follows row construction and registry validation, rather than preceding it.

Actual verification covers all nine current collector CLI entry points: each
refuses current incomplete coverage, reads no intentionally absent source and
creates no output. Seven focused tests pass on Python 3.12 and 3.14. Four
spelling row builders match their archived originals on four deterministic rows
each; original and current joint builders also produce identical complete rows
for a two-family finite fixture. Full historical natural corpus generation was
not rerun.

The full stdlib profile passes all 113 modules / 599 tests, with zero failures,
errors or skips. The scientific profile also passes 19 modules / 72 tests,
with zero failures/errors and one explicit MLX-environment skip. See the
[source/evidence receipt](2026-10-28-q6-base-collector-gates-evidence.json).
The historical refinement, word-ranking, additional-epoch and retrieval
preparers still need their own scope audit. Complete historical provenance and
fresh independent qualification remain outstanding; this slice does not close
Q6 or change the APK.

## Source-bound v6 follow-up

The maintained v6 builder had the same source-identity gap as v7–v12: it
discarded the source article and had no dictionary-derived families in rows
sent to the joint preflight. Its nonhistorical path now uses the shared
source-occurrence, whole-token, dictionary and disjoint-family checks, binds
the source, exclusions and helper inputs, and rechecks them before output.
Both paths still refuse the present incomplete registry before collection.

The shared input reader also now refuses a repeated exclusion path. Its
previous duplicate check compared a `Path` to string dictionary keys, so it
could count the same file twice. This refusal applies in both modes; ordinary
historical runs with distinct exclusions retain their selection behavior.

Synthetic integration exercised v6 and v7 through the actual joint preflight,
including article/family overlap and changed-source refusal. A separate probe
used actual Parquet decoding and the pinned Pymorphy dictionary for both
builders; four rows reached fixture registries without identity errors and
were blocked on incomplete coverage. The probes substitute the initial guard
and do not constitute independent corpus admission. The v6 and v7 historical
builders each matched their previous implementation on 700 synthetic rows;
their respective SHA-256 values were
`043c6f4ffa89e97095d53ee6d9875b34cb478b18aa6ced45de23e51dd2ad541a` and
`6c857015a4bc0d9a23ca05f0e04480223cf1d3a7576cd977ad91a4cd776fe7c2`.
This is not a full historical-corpus replay. Temporary fixtures, environments
and source archives were removed; no model, APK or policy was changed. In a
staged archive without `build/`, the 26 shared-builder tests, three v6 tests
and five historical-wrapper tests passed. The 29 joint-preflight tests and
both isolated historical text and retrieval checks also passed locally.
