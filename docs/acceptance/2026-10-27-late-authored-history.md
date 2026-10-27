# Q6: late authored transformations, homographs and historical chain gaps

Reproduced the sorted JSONL payloads for role corpus v4 (8,688 rows), noun/predicate
extension v5 (9,572), copied v6 (9,572) and continuation corpus v7 (31,916).
Each regenerated payload matches its pinned historical SHA-256, count and,
where declared, skipped cases. v5 appends exactly to v4; v7 derives only from
v6 parent IDs or retains unchanged parent rows. v6 is exact v5 corpus reuse.
The 59,748 row exposures contain 33,596 unique row IDs, not independent samples.

Archived six hash-matching files: three generator modules and three original
preparation scripts. The preparation scripts are preserved as evidence and are
not executed: their top-level writes and replay setup are unnecessary for this
audit. Verified generation dependencies are checked before generator import.
The audit rebuilds dictionary paradigms using the same dictionary-only analyzer
and invokes the verified generator functions, without scoring or fitting.

Selection receipts bind the actual corpus manifests. Group files match their
selection and training-plan hashes/counts (8,286 / 9,094 / 9,094 / 30,512), and
every selected group's embedded row exactly matches its reproduced corpus row.
This is a consistency check of surviving evidence, not proof of fit execution,
binary reproduction, source qualification or independent model quality.

Candidate forms have 48 dictionary families in v4 and 59 in v5-v7. All analyses
are retained, including adverbs homographic with neuter short adjectives.
Nineteen families were missing from the default supervised/prepared-family
blocklist: бедно, богато, больно, важно, вежливо, верно, весело, глупо, здорово,
красиво, нужно, опасно, полезно, скромно, слабо, счастливо, умно, честно, щедро.
They are conservative training exclusions, not declarations of intended labels.
Unknown corruptions are not given invented lemmas. The reproduced versions add
1,101 previously unblocked left-context/target keys; their full union is 1,208.
As before, this projection conservatively ignores right suffixes. The new
prepared-training-quarantine/context-only entries retain v6's duplicate lineage.
All previous 91 registry entries and incomplete global coverage remain intact.

One historical source gap remains explicit. v4's manifest claims role feature
hash 2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0.
It differs from the tracked/current 181fff1a... version and was not found among
the checked Git/file copies. It is not used by the role corpus generator, so
payload reproduction succeeds without substituting a feature implementation.
The receipt records this as an unavailable historical claim and sets full
historical source coverage false. Current helper hashes used for regeneration
are recorded separately from that unverified old claim. Feature/model parity
for that missing historical version is not asserted.

All 174 tests pass in a fresh source-only directory without original build
corpora, models or morphology packages. Both ledger schemas validate and remain
incomplete. New regressions cover parent derivation and row identity, duplicate
IDs, archive tampering without executing archived preparation, selection/group
content checks and ambiguous adverb/adjective families. Snapshot tests preserve
v5/v6 reuse; the real preparation CLI rejects полезно under the default profile,
with exit code 2 and no output directory. CI includes the new audit tests; no
remote CI run is claimed. The dictionary-backed provenance audit exits 0.

Q6 remains open for later applied/residual transformations, unsupported historic
word families, the missing feature version and the separate 120-example file
whose origin is still unproven. No runtime policy, model, APK or device change.
