# Q6/Q7: original public historical datasets restored for CI

Three existing modules now run in the scientific CI job without changing their
assertions: `test_epoch_evaluation.py`, `test_extra_epochs.py`, and
`test_neural_refinement.py`. The job verifies and restores the original public
data before executing the eight scientific modules. The remaining three
historical-artifact modules remain explicitly outside CI execution; Q7 is open.

## Data and provenance

The nested historical workspace archive retained the refinement manifest at
`20b32e840b890aab726fabea30c6409fce058d0c9ba3dd64d603aaaa24475ce7`
and additional-epoch manifest at
`1d2a8f51d0fe2462b8610cb813d2b4330a41e3e6360a6f993acb00fee6de6361`.
Both current preparation scripts still equal their original bound source hashes.
They were run against the hash-pinned public Wikipedia parquet and vocabulary:
both manifests and every advertised payload reproduced byte for byte, 15 files
in total. No model was trained or selected.

`tools/ci/historical-data-v1` preserves all these bytes in a 1,849,627-byte
archive (9,896,304 bytes of payload). The generator also reads the same pinned
parquet to attribute all 1,388 consumed articles by title and contributor-history
link. Original source terms, normalization and synthetic spelling changes are
disclosed in the package NOTICE. A second complete archive generation matched
all four package files byte for byte on the tested host.

The installer verifies fixed original manifest hashes, every payload, source
lock, generator identities, attribution and permanent exclusions before writing.
It never uses tar extraction paths directly; staged payloads have a fixed member
set and size bound. Existing dataset directories and symlink parents are refused.
Other build outputs are preserved.

The previous durable ledger covered the 1,158 refinement articles, but omitted
all 230 additional-epoch articles. The new historical-exclusion entry adds all
230 and the 1,500 target contexts. Every prior entry is preserved, global
coverage remains false, and canonical-family/full-source-sentence recovery is
still explicitly missing. These old revealed rows are regression inputs.

## Actual validation

- Local macOS ARM64, Python 3.12.14, task-owned clean tracked source plus the
  candidate files bound in the evidence JSON; no owner-local experiment modules.
- Actual fresh-checkout installation: 15 files, all original bytes retained.
- Stdlib profile: 92 modules, 518 tests passed, no skips.
- Scientific profile: eight modules, 34 tests; 33 passed and the existing
  unsupported-environment MLX gradient test was skipped.
- All 24 CI infrastructure tests and 23 public-ledger tests passed. Fixture
  coverage includes corrupt payload/manifest refusal, archive symlink refusal,
  existing-data preservation and missing-exclusion refusal.
- Remaining historical profile: three modules, ten tests, six missing-artifact
  errors, exit 1. Models, candidate exports and absolute-path receipt relocation
  still need their original provenance preserved before CI integration.
- Exact F-Droid data-policy check and `git diff --check` passed. This is not a new
  full source scan or independent F-Droid build.
- Clean test checkout restored after verification; original owner payloads and
  untracked paths preserved. No phone commands, push or hosted workflow dispatch.

Earlier unsuccessful attempts and their raw logs are retained and disclosed in
the evidence JSON. Commands and remaining gaps are in
[python-tools-tests](../python-tools-tests.md). Raw local evidence remains under
`build/review-q7-tools-20261028/`.
