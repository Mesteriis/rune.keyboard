# Q9: frozen runtime asset identity and policy threshold checks

Added FrozenAssetIdentityTest to the app JVM suite. One table covers all 17
runtime data/policy files in smarttyping/experiments: every bin/ctx/gram and
the four policy JSON files. It checks byte length and streaming SHA-256 against
the existing Frozen*/Qualification pins, including the previously uncovered
neighbor model and contextual model/wiki/conversation/grammar inputs. Rescue
policy has no runtime size constant; its test-only size pin is the measured
1,314 bytes, alongside the existing runtime policy SHA. No runtime pin changes.

Inventory equality rejects an orphan binary/policy or a missing file. Metadata
JSON and NOTICE are outside the runtime table. The four policy files must each
have exactly one modelSha256, minimumScore and minimumMargin matching their
runtime qualification constants. Three flat scalar fields are inspected without
a new JSON dependency; complete policy bytes are independently SHA-bound.
Duplicate fields cannot mask threshold drift. Six current fingerprints must
also pass their existing independent admission pins, preserving the deliberate
literal checks in allows(). Legacy compact/joint/recovery policy identities and
the qualification suffix literals are unchanged.

Mutation regressions verify failure messages name the affected asset. They flip
one byte in a temporary neighbor-model copy, inject changed expected hash/size
pins, change expected model/score/margin pins for every policy, mutate the JSON
fields independently of the file-hash check, add duplicate fields, and add/remove
inventory members. Expected-pin injection exercises the same verifier inputs
that compiled constant changes supply; tracked runtime constants are not edited.
The negative checks assert actual rejection and fail if verification succeeds.

The initial targeted command passed eight identity/mutation tests. After adding
fingerprint consistency coverage, the full :app:testDebugUnitTest command passed
1,153 tests in 123 suites, including all nine new tests: zero failures, errors
or skips. The existing CI testDebugUnitTest --rerun-tasks job discovers this
standard JVM test class automatically. No remote CI execution is claimed.

Q9's requested source/JVM acceptance is verified. This does not establish APK
packaging, runtime readiness on a device, model quality or product replay parity;
those retain their own review gates. No production code, assets, thresholds,
dependency or device state changed. Exact commands, outcomes, source/asset
hashes and the mutation scope are recorded in the adjacent evidence JSON.
