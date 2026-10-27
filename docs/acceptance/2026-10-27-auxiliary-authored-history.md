# Q6: auxiliary authored corpora, combined inputs and residual group reuse

Reproduced five sorted JSONL payloads exactly against their historical hashes:

| Corpus | Prepared rows | Selected groups | Dictionary families | Context keys |
| --- | ---: | ---: | ---: | ---: |
| Instrumental v1 | 1,102 | 40 | 11 | 138 |
| Instrumental v2 | 2,862 | 180 | 19 | 346 |
| Left sequence v1 | 2,268 | 2,268 | 26 | 570 |
| Left sequence v1-v2 | 2,268 | 2,268 | 26 | 570 |
| Oblique v1 | 2,016 | 1,800 | 8 | 156 |

The five exposures total 10,516 rows with 7,146 unique IDs. The left-sequence
versions reuse exactly the same corpus with different feature-source metadata;
instrumental v1 is included in v2. These counts are not independent examples.
Dictionary paradigms and exact archived generators reproduce every payload and
skipped case. Eight generator/preparation files are now archived by hash.
Preparation scripts are retained without executing their top-level writes.

Every selected group's embedded row equals a reproduced corpus row, and the
selection receipts bind the actual manifests and group files. Prepared rows
that native retrieval did not select remain conservatively quarantined. No
missing candidate is injected and no new score or model fit is computed.

Verified combined v11 inputs as the exact ordered concatenation of applied-v2,
left-sequence-v1-v2 and instrumental-v2 groups (34,472). Combined v12 adds the
1,800 selected oblique groups, yielding 36,272. Parent selection hashes, output
group hashes/counts, group order and unique row IDs all match. Residual v10/v11
reuse their respective applied/combined parents; residual v12/v13/v14 reuse the
combined v12 group bytes exactly. Their plan hashes/counts match actual files.
This proves input lineage and reuse; it does not prove training execution,
feature parity, model identity or independent quality.

The five corpora yield 40 canonical dictionary-family keys already covered by
the default supervised/prepared exclusions, and 1,069 previously unblocked
context keys. Added ten family/context entries, retaining the complete prior
103-entry registry and incomplete global coverage. Ambiguous dictionary
readings remain conservative exclusions; corrupted unknown inputs get no
predicted canonical lemmas.

The original left-sequence-v1 manifest cites feature hash
82aeb37a82f7ac32aafd2f5f08eab36469ad2605b169943359db9a069726788e,
which was not found in the checked copies/Git version. Its generator does not
import that feature module, so corpus reproduction succeeds while full
historical source coverage remains false. This gap is additional to the older
v4 role-feature gap recorded previously. No replacement hash is presented as
the original missing implementation.

All 189 tests pass in a fresh isolated source-only directory without build
corpora, models or morphology packages. Both registry schemas validate with
incomplete coverage. New regressions cover exact concatenation/order even with
valid hashes, stale parent receipts, duplicate group rows, residual reuse plans,
restricted source-path resolution and all eight archives. The durable snapshot
and real preparation CLI reject a reused instrumental context with another
typo, exit code 2 and no output. CI includes the new audit tests; no remote CI
run is claimed. The full dictionary-backed audit exits 0 without model calls.

Q6 remains open for the outstanding source/origin/family gaps, fresh independent
qualification and the remaining provenance inventory. This step changes no
runtime behavior, source certificate, model, APK or device state.
