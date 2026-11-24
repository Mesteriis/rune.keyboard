# Q6: historical neighbor segment verification isolation

The historical neighbor source-segment entry binds the exact bytes of the old
`independent_corpus_guard.py`. Its original `--check` correctly refuses even a
nonsemantic change to those bytes. That live-file requirement prevented safe
migration of the current guard, despite the historical bytes already being
retained and verified in the text-boundary history archive.

The existing isolated history runner now also executes the unchanged neighbor
segment verifier against its archived guard. CI runs that check through the
runner rather than directly against the live helper. The runner verifies the
archived hash before execution, projects the later EWT source-only control entry
only after the live registration check, and leaves the live checkout and both
ledgers untouched. A failure in the neighbor verifier propagates. This is a
historical source-binding check; it neither re-reads the original shards nor
certifies independent qualification.

In a clean source archive without `build/`, an extra newline in the live guard
made the direct verifier fail with `NEIGHBOR_SEGMENT_DRIFT`. The isolated runner
then used the exact archived helper. Its own tests include corruption refusal,
source projection and propagation of a failing neighbor verifier. This removes
one specific migration dependency; other historical bindings and full Q6
freshness remain open.
The isolated runner completed: both three-test historical boundary suites,
their 179- and 470-row checks, named regressions and 279,056 neighbor segment
keys passed. Five runner unit tests passed, including neighbor failure
propagation. The ordinary neighbor check also passed before the migration probe.
Hosted CI was not run.
