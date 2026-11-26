# Q5: descriptive chat-report cluster integrity

The v2 chat reporter accepts `clusterId` independently of the Tatoeba article
identity in each input row. A synthetic two-control example with the same
article but two different cluster IDs was counted as two clusters by v2. That
can inflate the cluster denominator if metadata is inconsistent; it does not
show that the earlier report had that error.

The new v3 report retains v2's text-based Undo check and rejects mismatches
between `clusterId`, the Tatoeba article and source repository. It requires
one control per article and consistent sentence hash, prefix and target within
the article group. This is internal consistency checking, not authentication
of article contents or proof of independent authors. The historical v1 and v2
reporters remain available to reproduce their bound receipts. V3 continues to
describe exposed unproofread source controls, not a false-change estimate or
model qualification.

The original disclosed rows were regenerated in memory using the retained
public source and the historical ledger. All 34,330 rows matched the original
SHA-256 `c25d9afed4b75f78490f2e360c3eb0a0e06aaf97e3291d79f0bdd29aec0ee62f`
and passed cluster validation: 9,543 article groups, each with one control.
Four v3 and five v2 tests passed, including a reproduced v2 counterexample,
cluster splits, duplicated controls, changed source metadata, inconsistent
Undo and CLI refusal without output. A new product replay and v3 report over
the historical observations were not run; their previous results are not
relabelled as v3 evidence. Independent natural-chat qualification remains open.
The four v3 tests also passed in a staged source archive without `build/`;
the archive was removed.

## Bound source reproduction follow-up

The v3 command now also requires the pinned compressed Tatoeba source, its
source lock and the ledger used to create the rows. It checks the lock and
source bytes, validates the supplied ledger, regenerates the entire corpus and
requires byte-identical rows. All input and generator-helper bytes are checked
for drift and their hashes are recorded in the report. Consistent alteration of
both article and cluster ID, which passes the internal group consistency check,
is rejected by source reproduction. Changed source and source-lock bytes are
also rejected. The direct in-memory `report()` function remains a descriptive
aggregation and does not itself prove source reproduction.

Five v3 tests pass, including real source regeneration, consistent identity
forgery, and source/lock mutation. A complete CLI probe regenerated the original
34,330 rows using the historical ledger and processed 34,330 constructed
unchanged observations, reporting 9,543 control clusters. These observations
are synthetic validation fixtures, not a product replay or quality result. The
temporary fixture files were removed. The supplied ledger can still have
incomplete coverage; a matching source and ledger do not establish independent
labels, authors, or model qualification.
All five updated tests also passed from a staged source archive without
`build/`; the temporary archive was removed.

## Current-controller replay with v3 report

At clean source `797fb8587e82208298c5845930da2aa3a038257e`, the original
Tatoeba source and historical ledger regenerated the 34,330 disclosed rows
with the original `c25d9afed4b75f78490f2e360c3eb0a0e06aaf97e3291d79f0bdd29aec0ee62f`
rows digest. The current-product JVM controller replay completed with exit 0
and source/tool/resource binding checks; the observations SHA-256 was
`46bca0d8304e7956b09d04cf1d19692a6e9538e4ce152bc1d580db27cb5276c2`.
The v3 report reproduced and bound the exact input rows from the source and
ledger. Its output SHA-256 was
`d2bdb01163388947c1d8d28811230a78671f949b37154f2da9c186e4d9ddca09`.

The controller changed 33 of 9,543 unproofread source controls, matching the
previous curated-protection result. The descriptive Wilson interval for this
change rate is 0.246%–0.485%; it is not a verified false-change interval.
Across 34,330 rows, 16,811 boundary changes were observed, with zero
text-based Undo failures, prefix changes or input transformations. Among the
24,787 synthetic typo-labelled rows, 16,143 changes matched the synthetic
target; these labels do not establish real user intent or natural typing
accuracy. The test uses a single-token controller replay, not Android IME
timing or multiword revisions. One replay and report were executed, not a
determinism repeat. Temporary corpus, observations, compiled harness, logs,
ledger and report were removed. No Fold or hosted CI was used.
