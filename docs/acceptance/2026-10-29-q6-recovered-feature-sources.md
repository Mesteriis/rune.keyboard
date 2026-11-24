# Q6 recovered historical feature sources

Two source versions previously recorded as unavailable have been restored to
`tools/typing_experiments/frozen_sources/`. Their bytes match the original
receipt hashes: role features `2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0`
and left-sequence features `82aeb37a82f7ac32aafd2f5f08eab36469ad2605b169943359db9a069726788e`.

The role source was extracted as data from the locally recorded file-creation
command. The left-sequence source was reconstructed in a temporary directory
from the recorded initial patch and subsequent patches; its pinned bytes were
present after the second applied revision. Neither historical source was
executed during recovery. Existing historical receipts remain unchanged and
still describe what was unavailable when those audits ran.

The new verifier checks both bytes against the original receipt entries and
checks Python syntax without importing either file. Its regression test rejects
source and receipt mutations. The verifier and test are wired to CI; hosted CI
has not run this change. Recovery does not establish historical model execution,
feature or model parity, complete transitive provenance, or independent data
qualification. No model was trained and no device was changed.

A separate local check read the two surviving historical corpus manifests from
`build/`, verified each manifest's SHA-256 against the existing audit receipt,
and compared its `sourceHashes` entry to the restored source. The v4 manifest
contains 8,688 rows and binds the restored role source; the left-sequence-v1
manifest contains 2,268 rows and binds the restored left-sequence source. This
establishes the source identities recorded by those manifests, not that either
feature source was executed or that a trained model used it. The permanent CI
verifier uses the tracked receipts and does not depend on these ignored files.

All 11 direct source-hash records in those two original manifests now have
byte-identical tracked counterparts: four for role-v4 and seven for
left-sequence-v1. A small tracked projection records only source basenames,
hashes and tracked paths, plus the receipt-bound original manifest hashes;
the two absolute machine paths in the original manifests are not published.
Its CI verifier checks all 11 file hashes and both receipt bindings without
`build/`, and its mutation test rejects source and parent-receipt changes. This
is a direct manifest projection: the projection was checked against the original
local manifests when created, and the portable check does not reread them. It
does not establish transitive dependency closure or historical execution.

The late and auxiliary authored-history auditors now resolve the two historical
feature digests through the same archive manifest used by their other sources.
Future audit receipts bind the archived files and require their exact bytes.
Either missing or changed archive file causes an audit failure. The earlier
point-in-time receipts remain the evidence of what the original audit saw.
