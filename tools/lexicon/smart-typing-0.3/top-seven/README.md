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
quota. Seven accepted globally ordered representations prove the exact top-seven;
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
primitive scratch per actively used selection engine, allocated lazily; it is
not a measured RSS/allocation figure. No per-state objects or new index sidecars.

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
