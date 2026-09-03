# Exact global top-seven integration

The production generator can now use `CandidateLexicon.selectTop` after the
existing protection, normalization and all routed exact-membership checks.
Packed readers and the lazy ready bridge implement it through `PackedTopSeven`.
Other readers return null and use exhaustive scan. `scan` retains its original
full-enumeration contract. No model, confidence policy, corpus label or expected
word participates in selection.

This integrates the previously reviewed global-order prototype. Source/control
digests are recorded in `prototype-origins.json`. The production adaptation
shares the existing generator's preflight and comparator, removes prototype
observers, obtains immutable handles through the ready bridge and reads route
priors from the route rather than repeating constants. The historical review
does not claim an independent review of this integration.

## Certificate

The comparator is weighted edit cost, descending language prior, frequency rank,
scalar folded display, language ordinal, scalar terminal. Case preservation
and original-display suppression precede admission; dedup precedes fallback quota.

For each unresolved trie region, retain the maximum inherited UNIT row minimum
and validated terminal-length gap, U. Prune only when U exceeds the unit radius.
The weighted quarter-cost lower bound is
`max(inherited W, weighted row minimum, 3*U, 4*lengthGap)`.
The recurrence is unrestricted Damerau-Levenshtein, with complete last-occurrence
history and unbanded matrices. In particular, a transposition spanning r source
and c target positions costs `4r + 4c - 11` with r,c >= 2. A skipped prefix cut
t <= r-1 positions into the edge is reachable by deletions costing 4t, no greater
than that edge. Thus the minimum prefix row remains a lower bound even when an
optimal transposition jumps the cut. UNIT has the analogous inequality
`t <= r-1 <= r+c-3`. Every weighted edge is at least three times its UNIT cost;
insert/delete requirements give the length-gap bound. Ancestor bounds remain
valid for every descendant, so their maximum is safe.

One global heap covers both routes. A popped region stays unresolved until its
entire child list has been expanded; no certificate is evaluated mid-expansion.
Replayed prefixes use previously charged arena records, not uncharged trie reads.
The pending heap contains verified exact comparator keys. Its minimum may stream
only when strictly before every unresolved lower bound. Frequency/lexical bounds
remain conservative bottom values, so equality in weighted cost and prior never
certifies. A streamed display is marked seen even when skipped by the fallback
quota. The requested number (1–7) of accepted globally ordered representations proves its exact prefix;
otherwise frontier exhaustion and drained pending prove the shorter list.

`TopCandidateProof` distinguishes those outcomes from no proof. Budget exhaustion
retains only verified partial suggestions and its unconditional AutoReplace veto.
Cancellation wins over exhaustion and drops all payload. Scratch clears in
`finally`, including the temporary mapping references. Mapped dictionaries remain
public immutable assets owned by the existing loader.

The caps remain 8192 states shared with exact lookup and 64 verifications shared
between languages. Fixed search arrays reserve 272,508 primitive bytes; two
terminal verification engines add 10,016 bytes. The existing generator and
readers retain their own previous arrays. This is approximately 283 KB additional
primitive scratch per actively used selection engine in the initial integration;
prefix reuse adds 4,352 bytes, for a current total of 286,876 bytes. It is allocated lazily and is
not a measured RSS/allocation figure. No per-state objects or new index sidecars.

## Reusing prefix recurrence rows

The frontier order, bounds, state/verifications counters and result certificates
are unchanged. `PrefixDistance` retains the last scalar path and a 33-by-32 table
of last-occurrence histories for that path. Moving to a new region retains only
its common scalar prefix with the previous path, and only for the same adjacency
language and query. The suffix is recomputed using the original unrestricted
recurrence. At language changes the reusable depth is zero. At query changes
`begin` resets both matrices, path and histories. Cancellation/finally clears
them with the other typing scratch; no cache survives a selection.

Rows through the common prefix depend only on that prefix, query and language;
their recurrence values and histories are therefore identical to replay from
root. A new row overwrites all columns it can subsequently reference. Its
transposition references use only strictly earlier occurrence rows and earlier
query columns. Deeper discarded rows cannot contribute to a new recurrence.
Sibling expansion restores the already saved parent history and overwrites its
child row. This preserves full unrestricted history, including repeated symbols
and transpositions crossing the common-prefix boundary; it is not a banded or
optimal-string-alignment approximation.

Regression controls compare branch/language/query/sibling reuse against full
replay, retain independent graph/oracle coverage, and cancel at every observed
checkpoint. The public 6000-row calibration export must remain byte-identical
to the previous generator output. This optimization changes CPU work, not
candidate coverage or confidence policy.

## Evidence and reproduction

`app/src/test/resources/smarttyping/top-seven/` contains the unchanged independent
finite controls: 3209 distance pairs / 8218 prefix cuts and 94 full policy cases.
Their generator uses independent edit graphs plus a source-only policy reference.
Regenerate into a fresh directory, then compare each TSV SHA against MANIFEST:

```sh
python3 tools/lexicon/smart-typing-0.3/top-seven/prepare_controls.py \
  --output build/smart-typing-0.3/top-seven-regenerated-controls
```

JVM tests run these controls against production, add both-route quotas, exact
8192/64/65 limits, strict ties, every cancellation checkpoint and reuse. Existing
independent generator graph tests now test both exhaustive and packed selectors.

The calibration export documented in `tools/eval/smart-typing-0.3/pipeline/`
compiles the new production implementation. Reuse that exact compiled artifact
for a full-neighborhood comparison against the immutable historical oracle:

```sh
python3 tools/lexicon/smart-typing-0.3/top-seven/qualify_current.py \
  --compiled-export build/smart-typing-0.3/pipeline-calibration-top7-01 \
  --output build/smart-typing-0.3/top-seven-current-oracle-01 \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
```

The archive loader checks all pinned historical text identities. Current source,
binary and asset hashes must match the selected compiled export. Exactly 773
UTF-8-compatible noncancelled cases execute; the explicit cancellation and
unpaired-surrogate controls are listed as excluded and remain separately tested
in JVM. Every complete result must equal the full oracle's ranked set; incomplete
results must be verified subsets and retain their veto. This is a fresh current
implementation run, not a relabeling of the historical prototype's 775 results.

Android comparison uses the first 20 public development queries per language
with no outcome-based selection. The fixture identity is in
`android-fixture-origins.json`. Each strategy runs two unmeasured passes and five
measured passes, alternating execution order: 300 CPU/wall observations per
strategy. Only numeric IDs/counters/timings are emitted. The exhaustive strategy
uses the same assets, policy and generator with `selectTop` disabled. Cold load
is separately covered by the existing APK asset test. Emulator timings do not
qualify physical Fold battery or final latency budgets.

No AutoReplace, model quality or release gate is enabled by an exact set certificate.

## Candidate-width calibration experiments

The product currently requests seven alternatives. The user contract allows up
to seven, so this is a configurable design choice to evaluate before ranking
calibration. `CandidateGenerator` now accepts an immutable `maximumAlternatives`
constructor argument (1–7, default7). `candidate_budget.py` exercises that actual
production API for exact top1/top3/top7 alternatives (total set widths2/4/8 including original).
No source overlays are used. It does not change search/verification limits, protected
tokens, original preservation, comparator or language fallback policy.
The width is selected before the request; a budget-exhausted request is never
reinterpreted as a successful smaller request.

```sh
python3 tools/lexicon/smart-typing-0.3/top-seven/candidate_budget.py \
  --candidates 4 --output build/smart-typing-0.3/candidate-budget-four-fresh \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
python3 tools/lexicon/smart-typing-0.3/top-seven/qualify_current.py \
  --maximum-alternatives 3 \
  --compiled-export build/smart-typing-0.3/candidate-budget-four-fresh/export \
  --output build/smart-typing-0.3/candidate-budget-four-oracle-fresh \
  --index-dir build/smart-typing-0.3/lexicon-index-prototype/assets \
  --rank-dir build/smart-typing-0.3/packed-lexicon-reader-prototype/rank-assets \
  --java java --gradle-cache "$HOME/.gradle/caches/modules-2/files-2.1"
```

Use fresh directories and corresponding explicit widths for the2/8 controls.
The oracle is always the preserved full-neighborhood oracle; the declared
requested prefix is compared exactly. Verifier metadata must match the request,
and every incomplete request must retain its veto. Width8 is also compared
byte-for-byte with the production calibration export as a default-width compatibility control.
The earlier overlay experiment is reproducible at commit `03cea45`; its frozen
outputs remain unchanged. New provenance records the numeric harness argument.
Evidence and limitations: `results/2026-09-03-candidate-widths/` and
`docs/acceptance/2026-09-03-smart-typing-0.3-candidate-widths.md`.
