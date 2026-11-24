# Q7: neighbor-recovery wall deadline and replay stability

The current-product replay uses `PackedCandidateLexicon`, whose neighbor
recovery reads `System.nanoTime()` and stops after 100 ms. The serialized
recovery evidence includes completion, inspected states, terminals and
alternatives, and the Q7 two-pass comparator compares those fields exactly.
Host scheduling pauses can therefore change compared output even with identical
inputs and source. This is a possible explanation for the previously reported
intermittent Linux x86_64-emulated mismatch; the original missing diff means it
is not a proven cause of that failure.

A new JVM integration test uses the real packed fixture and
`CandidateGenerator.generateRecovery`, supplying deterministic clocks to the
same `NeighborRecoverySearch`: one remains within the deadline, one expires at
the first checkpoint. For the same input and baseline, the completed search
returns its candidate while the timed search reports `STATES_EXHAUSTED` with no
candidate; baseline local evidence remains equal. This proves the path from the
deadline to generation output under injected conditions. It does not measure
runtime likelihood, establish an actual device deadline, or prove which field
changed in the historical mismatch. No deadline, admission policy, production
code, replay threshold or frozen baseline was changed.

The complete `NeighborRecoverySearchTest` class passed in a disposable clean
clone: 5 tests, zero failures, errors or skips. Gradle ran offline with the
pinned native submodule checkout. An initial clone populated the submodule as a
source archive without its own Git metadata and failed the qualification-source
check; the submodule was then replaced inside that disposable clone by a local
shared Git clone at the pinned commit, and the test succeeded. The test clone
and generated build outputs were removed. Q7 still requires actual hosted CI and
an attributable reproduction of the earlier intermittent failure.

## Bounded mismatch diagnosis

The replay failure summary now counts changed neighbor-recovery evidence and
sub-cap `STATES_EXHAUSTED` observations separately for each pass. The latter is
a possible deadline signature, not a verdict on the historical failure. The
summary includes no words, source IDs, candidate values or input paths; the
existing full private comparison artifact is unchanged. A test binds the
numeric cap to the current production source. The comparison remains exact
between passes, and the existing baseline tolerance and product code are not
changed.

Ten driver tests and eleven projection tests passed locally. The actual current
2,160-row replay ran twice with the original strict determinism gate and matched
its baseline: zero differing rows, zero tolerated score differences. It exited
zero and did not reproduce the old Linux failure. This run used macOS arm64,
not hosted CI or Linux x86_64. Its task-owned private observations and logs were
removed after inspecting the receipt. Hosted acceptance remains open.
